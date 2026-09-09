from __future__ import annotations

import time
from mimetypes import guess_type
from pathlib import Path

from flask import Blueprint, Response, current_app, request, send_file
from sqlalchemy.exc import ProgrammingError
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError

from app.extensions import db
from app.models import DetectionRecord, Robot, UserRobotLink, VideoTask
from app.services.detection_service import DetectionService
from app.services.task_service import TaskService
from app.utils.auth import get_current_user, roles_required
from app.utils.response import api_error, api_success

bp = Blueprint("detection", __name__, url_prefix="/api/detection")
bp_v1_compat = Blueprint("detection_v1_compat", __name__, url_prefix="/api/v1/detection")


def _get_detection_service() -> DetectionService:
    service = current_app.extensions.get("detection_service")
    if service is None:
        service = DetectionService(current_app)
        current_app.extensions["detection_service"] = service
    return service


def _check_robot_access(user_id: int, robot_id: int | None, is_admin: bool) -> bool:
    if robot_id is None or is_admin:
        return True
    return UserRobotLink.query.filter_by(user_id=user_id, robot_id=robot_id).first() is not None


def _resolve_robot_for_detection(user, robot_id_raw: str | None) -> int | None:
    if user.role == "admin":
        return int(robot_id_raw) if robot_id_raw else None

    links = UserRobotLink.query.filter_by(user_id=user.id).all()
    if len(links) == 0:
        bound_robot_ids = {row.robot_id for row in UserRobotLink.query.with_entities(UserRobotLink.robot_id).all()}
        candidate = Robot.query.filter(~Robot.id.in_(bound_robot_ids)).order_by(Robot.created_at.asc()).first()
        if candidate is None:
            return None
        db.session.add(UserRobotLink(user_id=user.id, robot_id=candidate.id))
        db.session.commit()
        return int(candidate.id)
    if len(links) > 1:
        # Auto-fix legacy data by keeping the earliest link.
        links.sort(key=lambda x: ((x.created_at.timestamp() if x.created_at else 0.0), x.id or 0))
        keep = links[0]
        for item in links[1:]:
            db.session.delete(item)
        db.session.commit()
        return int(keep.robot_id)
    return int(links[0].robot_id)


def _parse_score_thresh(raw: str | None, default: float = 0.25) -> float:
    try:
        val = float(raw) if raw is not None else default
    except (TypeError, ValueError):
        val = default
    return max(0.05, min(0.99, val))


def _parse_realtime_fps(raw: str | None, default: float = 8.0) -> float:
    try:
        val = float(raw) if raw is not None else default
    except (TypeError, ValueError):
        val = default
    return max(1.0, min(30.0, val))


@bp.get("/models")
@roles_required("admin", "user")
def list_models():
    from app.models.entities import SystemConfig

    service = _get_detection_service()
    models = service.list_models()
    loadable_model_keys = [item["key"] for item in models if item.get("key") != "mock-default" and item.get("loadable", False)]
    try:
        default_config = SystemConfig.query.get("default_model_key")
    except ProgrammingError:
        # Gracefully fallback when legacy DB is missing system_configs table.
        db.session.rollback()
        default_config = None
    configured_default = str(default_config.value).strip() if default_config and default_config.value else ""
    if configured_default in loadable_model_keys:
        default_model_key = configured_default
    elif loadable_model_keys:
        default_model_key = loadable_model_keys[0]
    else:
        default_model_key = "mock-default"
    
    return api_success(
        {
            "models": models,
            "default_model_key": default_model_key,
            "inference_enabled": bool(current_app.config.get("MODEL_ENABLE_INFERENCE", False)),
        }
    )


@bp_v1_compat.get("/models")
@roles_required("admin", "user")
def list_models_v1_compat():
    # Backward compatibility for old frontend cache that still calls /api/v1.
    return list_models()


@bp.post("/models/upload")
@roles_required("admin")
def upload_model():
    if "file" not in request.files:
        return api_error("请上传模型文件", code=4001)
    file = request.files["file"]
    if not file.filename:
        return api_error("文件名不能为空", code=4002)

    filename = secure_filename(file.filename)
    if not filename.endswith((".pt", ".pth", ".onnx")):
        return api_error("仅支持 .pt, .pth, .onnx 格式的模型文件", code=4003)

    service = _get_detection_service()
    service.model_dir.mkdir(parents=True, exist_ok=True)
    save_path = service.model_dir / filename
    if save_path.exists():
        return api_error("该模型文件已存在，请修改文件名后再上传", code=4004)

    file.save(save_path)
    return api_success({"message": "模型上传成功", "file_name": filename})


@bp_v1_compat.post("/models/upload")
@roles_required("admin")
def upload_model_v1_compat():
    return upload_model()


@bp.post("/models/default")
@roles_required("admin")
def set_default_model():
    from app.models.entities import SystemConfig
    from app.extensions import db

    payload = request.get_json() or {}
    model_key = str(payload.get("model_key", "")).strip()
    if not model_key:
        return api_error("必须提供 model_key", code=4001)

    service = _get_detection_service()
    available_models = {item["key"]: item for item in service.list_models()}
    if model_key not in available_models:
        return api_error("所选模型不存在", code=4004)
    if model_key != "mock-default" and not available_models[model_key].get("loadable", False):
        return api_error("当前仅支持选择可加载的 .pt / .pth / .onnx 模型作为默认模型", code=4003)
    if model_key == "mock-default" and any(item.get("loadable", False) for item in available_models.values() if item.get("key") != "mock-default"):
        return api_error("当前已有可用检测模型，请先选择实际模型作为默认值", code=4003)

    try:
        config = SystemConfig.query.get("default_model_key")
    except ProgrammingError:
        db.session.rollback()
        return api_error("数据库缺少 system_configs 表，请重启后端自动迁移后重试", code=5002, http_status=500)
    if not config:
        config = SystemConfig(key="default_model_key")
        db.session.add(config)
    config.value = model_key
    db.session.commit()

    return api_success({"message": "默认模型设置成功", "default_model_key": model_key})


@bp_v1_compat.post("/models/default")
@roles_required("admin")
def set_default_model_v1_compat():
    return set_default_model()


@bp.post("/models/delete")
@roles_required("admin")
def delete_model():
    from app.models.entities import SystemConfig
    from app.extensions import db
    
    payload = request.get_json() or {}
    model_key = str(payload.get("model_key", "")).strip()
    if not model_key:
        return api_error("必须提供 model_key", code=4001)

    service = _get_detection_service()
    model_path = service.model_dir / model_key
    if not model_path.exists() or not model_path.is_file():
        return api_error("系统模型不存在或不可删除", code=4004)
        
    try:
        config = SystemConfig.query.get("default_model_key")
    except ProgrammingError:
        db.session.rollback()
        config = None
    if config and config.value == model_key:
        return api_error("不能删除当前正在使用的默认模型", code=4003)

    try:
        model_path.unlink()
    except Exception as e:
        return api_error(f"删除失败: {str(e)}", code=5000)

    return api_success({"message": f"成功删除模型 {model_key}"})


@bp_v1_compat.post("/models/delete")
@roles_required("admin")
def delete_model_v1_compat():
    return delete_model()


@bp.post("/image")
@roles_required("admin", "user")
def detect_image():
    user = get_current_user()
    assert user is not None

    if "file" not in request.files:
        return api_error("请上传文件", code=4001)
    file = request.files["file"]
    if not file.filename:
        return api_error("文件名不能为空", code=4002)

    # Validate actual image data before saving or invoking inference.
    try:
        with Image.open(file.stream) as uploaded_image:
            uploaded_image.verify()
        file.stream.seek(0)
        with Image.open(file.stream) as uploaded_image:
            uploaded_image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        return api_error("请上传内容完整且有效的图片文件", code=4003)
    finally:
        file.stream.seek(0)

    robot_id_raw = request.form.get("robot_id")
    try:
        robot_id = _resolve_robot_for_detection(user, robot_id_raw)
    except RuntimeError as exc:
        return api_error(str(exc), code=4006)

    if user.role != "admin" and robot_id is None:
        return api_error("当前用户未绑定机器人，请联系管理员先完成绑定", code=4005)

    if not _check_robot_access(user.id, robot_id, user.role == "admin"):
        return api_error("无权访问该机器人", code=4031, http_status=403)

    score_thresh = _parse_score_thresh(request.form.get("score_thresh"), default=0.25)
    model_key = str(request.form.get("model_key", "")).strip() or None
    use_cyclegan = request.form.get("use_cyclegan", "false") == "true"

    upload_root = Path(current_app.config["UPLOAD_DIR"]) / "images"
    upload_root.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file.filename)
    save_path = upload_root / f"{int(time.time() * 1000)}_{filename}"
    file.save(save_path)

    service = _get_detection_service()
    result = service.detect_image(
        image_path=save_path,
        score_thresh=score_thresh,
        model_key=model_key,
        use_cyclegan=use_cyclegan,
    )
    
    # One record represents the entire image; any trash target must flag it.
    detections = result.get("detections", [])
    trash_detections = [item for item in detections if item.get("is_trash", False)]
    representative = max(trash_detections or detections, key=lambda item: float(item.get("score", 0.0)), default=None)
    record = DetectionRecord(
        user_id=user.id,
        robot_id=robot_id,
        source_type="image",
        media_path=str(save_path),
        detected_type=representative["class_name"] if representative else "none",
        is_trash=bool(trash_detections),
        confidence=float(representative["score"] if representative else 0.0),
        details_json={
            "model_key": model_key or "default",
            "use_cyclegan": use_cyclegan,
            "cyclegan_applied": bool(result.get("cyclegan_applied", False)),
            "cyclegan_error": result.get("cyclegan_error"),
            "summary": result.get("summary", {}),
            "detections": result.get("detections", []),
        },
    )
    db.session.add(record)
    db.session.commit()

    return api_success(result, message="图片检测完成")


@bp.post("/video")
@roles_required("admin", "user")
def detect_video():
    user = get_current_user()
    assert user is not None

    if "file" not in request.files:
        return api_error("请上传文件", code=4001)
    file = request.files["file"]
    if not file.filename:
        return api_error("文件名不能为空", code=4002)

    robot_id_raw = request.form.get("robot_id")
    try:
        robot_id = _resolve_robot_for_detection(user, robot_id_raw)
    except RuntimeError as exc:
        return api_error(str(exc), code=4006)

    if user.role != "admin" and robot_id is None:
        return api_error("当前用户未绑定机器人，请联系管理员先完成绑定", code=4005)

    if not _check_robot_access(user.id, robot_id, user.role == "admin"):
        return api_error("无权访问该机器人", code=4031, http_status=403)

    score_thresh = _parse_score_thresh(request.form.get("score_thresh"), default=0.25)
    model_key = str(request.form.get("model_key", "")).strip() or None
    use_cyclegan = request.form.get("use_cyclegan", "false") == "true"
    use_tracking = request.form.get("use_tracking", "false") == "true"
    simulate_realtime = request.form.get("simulate_realtime", "true") == "true"
    realtime_fps = _parse_realtime_fps(request.form.get("realtime_fps"), default=8.0)

    upload_root = Path(current_app.config["UPLOAD_DIR"]) / "videos"
    upload_root.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file.filename)
    save_path = upload_root / f"{int(time.time() * 1000)}_{filename}"
    file.save(save_path)

    task = TaskService.submit_video_task(
        user_id=user.id,
        robot_id=robot_id,
        video_path=save_path,
        model_key=model_key,
        score_thresh=score_thresh,
        use_cyclegan=use_cyclegan,
        use_tracking=use_tracking,
        simulate_realtime=simulate_realtime,
        realtime_fps=realtime_fps,
    )
    return api_success(task.to_dict(), message="视频任务已提交")


@bp.get("/video/tasks/<string:task_id>")
@roles_required("admin", "user")
def get_video_task(task_id: str):
    user = get_current_user()
    assert user is not None

    task = VideoTask.query.get(task_id)
    if task is None:
        return api_error("任务不存在", code=4041, http_status=404)
    if user.role != "admin" and task.user_id != user.id:
        return api_error("无权访问该任务", code=4031, http_status=403)

    
    should_kick = False
    age_sec = 0.0
    if getattr(task, "created_at", None) is not None:
        try:
            age_sec = max(0.0, time.time() - task.created_at.timestamp())
        except Exception:
            age_sec = 0.0

    if task.status == "queued" and age_sec >= 1.0:
        should_kick = True
    elif task.status == "running" and int(task.progress or 0) <= 1 and age_sec >= 5.0:
        should_kick = True

    if should_kick:
        app_obj = current_app._get_current_object()
        try:
            TaskService.recover_video_task(app_obj, str(task.id))
            task = VideoTask.query.get(task_id)
        except Exception:
            pass

    return api_success(task.to_dict())


@bp.get("/video/tasks/<string:task_id>/preview")
@roles_required("admin", "user")
def preview_video_task(task_id: str):
    user = get_current_user()
    assert user is not None

    task = VideoTask.query.get(task_id)
    if task is None:
        return api_error("任务不存在", code=4041, http_status=404)
    if user.role != "admin" and task.user_id != user.id:
        return api_error("无权访问该任务", code=4031, http_status=403)

    preview_path = None
    # Assign a new dict so SQLAlchemy persists newly generated preview metadata.
    result_json = dict(task.result_json) if isinstance(task.result_json, dict) else {}
    preview_candidate = result_json.get("output_video_preview_path") if isinstance(result_json, dict) else None
    output_video_path = result_json.get("output_video_path") if isinstance(result_json, dict) else None

    if preview_candidate:
        cand = Path(str(preview_candidate))
        if cand.exists() and cand.is_file():
            preview_path = cand

    # Backward-compatible path for historical tasks without preview field:
    # try to transcode annotated video first, then fallback to annotated source.
    if preview_path is None and output_video_path:
        annotated_path = Path(str(output_video_path))
        if annotated_path.exists() and annotated_path.is_file():
            service = _get_detection_service()
            web_path, web_ok = service._build_web_preview_video(annotated_path)
            if web_ok and web_path.exists() and web_path.is_file():
                preview_path = web_path
                if isinstance(result_json, dict):
                    result_json["output_video_preview_path"] = str(web_path)
                    result_json["output_video_web_playable"] = True
                    task.result_json = result_json
                    db.session.commit()
            else:
                preview_path = annotated_path
                if isinstance(result_json, dict):
                    result_json["output_video_preview_path"] = str(annotated_path)
                    result_json["output_video_web_playable"] = False
                    task.result_json = result_json
                    db.session.commit()

    video_path = preview_path or Path(task.video_path)
    if not video_path.exists() or not video_path.is_file():
        return api_error("视频文件不存在", code=4042, http_status=404)

    mimetype = guess_type(video_path.name)[0] or "application/octet-stream"
    resp = send_file(video_path, mimetype=mimetype, as_attachment=False, conditional=False)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@bp.get("/image/records")
@roles_required("admin", "user")
def image_records():
    user = get_current_user()
    assert user is not None

    q = DetectionRecord.query.filter(DetectionRecord.source_type == "image")
    if user.role != "admin":
        q = q.filter(DetectionRecord.user_id == user.id)

    rows = q.order_by(DetectionRecord.detected_at.desc()).limit(200).all()
    return api_success([r.to_dict() for r in rows])


@bp.get("/video/records")
@roles_required("admin", "user")
def video_records():
    user = get_current_user()
    assert user is not None

    q = DetectionRecord.query.filter(DetectionRecord.source_type == "video")
    if user.role != "admin":
        q = q.filter(DetectionRecord.user_id == user.id)

    rows = q.order_by(DetectionRecord.detected_at.desc()).limit(200).all()
    return api_success([r.to_dict() for r in rows])


@bp.post("/realtime/start")
@roles_required("admin", "user")
def start_realtime_detection():
    user = get_current_user()
    assert user is not None

    payload = request.get_json(silent=True) or {}
    source = str(payload.get("source", "")).strip()

    robot_id_raw = payload.get("robot_id")
    try:
        robot_id = _resolve_robot_for_detection(user, str(robot_id_raw) if robot_id_raw is not None else None)
    except RuntimeError as exc:
        return api_error(str(exc), code=4006)

    if user.role != "admin" and robot_id is None:
        return api_error("当前用户未绑定机器人，请联系管理员先完成绑定", code=4005)

    if not _check_robot_access(user.id, robot_id, user.role == "admin"):
        return api_error("无权访问该机器人", code=4031, http_status=403)

    if robot_id is not None:
        robot = Robot.query.get(robot_id)
        machine_rtsp = str(robot.rtsp_url or "").strip() if robot is not None else ""
        if user.role != "admin":
            if not machine_rtsp:
                return api_error("当前绑定机器未配置 RTSP 地址，请联系管理员在机器管理中配置", code=4007)
            source = machine_rtsp
        elif machine_rtsp and not source:
            source = machine_rtsp

    if not source:
        return api_error("请提供监控源地址（如 0 / rtsp://... / http://...）", code=4007)

    score_thresh = _parse_score_thresh(str(payload.get("score_thresh")) if payload.get("score_thresh") is not None else None, default=0.25)
    model_key = str(payload.get("model_key", "")).strip() or None
    use_cyclegan = bool(payload.get("use_cyclegan", False))
    use_tracking = bool(payload.get("use_tracking", False))
    realtime_fps = _parse_realtime_fps(str(payload.get("realtime_fps")) if payload.get("realtime_fps") is not None else None, default=8.0)

    service = _get_detection_service()
    try:
        session = service.start_realtime_session(
            user_id=user.id,
            robot_id=robot_id,
            source=source,
            score_thresh=score_thresh,
            model_key=model_key,
            use_cyclegan=use_cyclegan,
            use_tracking=use_tracking,
            realtime_fps=realtime_fps,
        )
    except ValueError as exc:
        return api_error(str(exc), code=4008)

    return api_success(session, message="实时监控会话已启动")


@bp.get("/realtime/sessions/<string:session_id>")
@roles_required("admin", "user")
def realtime_session_status(session_id: str):
    user = get_current_user()
    assert user is not None
    service = _get_detection_service()
    try:
        data = service.get_realtime_session_status(session_id=session_id, user_id=user.id, is_admin=(user.role == "admin"))
    except KeyError:
        return api_error("会话不存在", code=4043, http_status=404)
    except PermissionError:
        return api_error("无权访问该会话", code=4031, http_status=403)
    return api_success(data)


@bp.get("/realtime/sessions/<string:session_id>/frame")
@roles_required("admin", "user")
def realtime_session_frame(session_id: str):
    user = get_current_user()
    assert user is not None
    service = _get_detection_service()
    try:
        payload = service.get_realtime_session_frame(session_id=session_id, user_id=user.id, is_admin=(user.role == "admin"))
    except KeyError:
        return api_error("会话不存在", code=4043, http_status=404)
    except PermissionError:
        return api_error("无权访问该会话", code=4031, http_status=403)

    if payload is None:
        return Response(status=204)

    return Response(payload, mimetype="image/jpeg", headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})


@bp.post("/realtime/sessions/<string:session_id>/stop")
@roles_required("admin", "user")
def stop_realtime_session(session_id: str):
    user = get_current_user()
    assert user is not None
    service = _get_detection_service()
    try:
        data = service.stop_realtime_session(session_id=session_id, user_id=user.id, is_admin=(user.role == "admin"))
    except KeyError:
        return api_error("会话不存在", code=4043, http_status=404)
    except PermissionError:
        return api_error("无权访问该会话", code=4031, http_status=403)
    return api_success(data, message="实时监控会话已停止")
