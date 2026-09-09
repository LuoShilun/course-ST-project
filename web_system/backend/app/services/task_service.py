from __future__ import annotations

from pathlib import Path
import threading

from flask import current_app

from app.extensions import db, video_executor
from app.models import DetectionRecord, VideoTask
from app.services.detection_service import DetectionService


class TaskService:
    _dispatch_lock = threading.Lock()
    _inflight_task_ids: set[str] = set()

    @staticmethod
    def _mark_inflight(task_id: str) -> bool:
        with TaskService._dispatch_lock:
            if task_id in TaskService._inflight_task_ids:
                return False
            TaskService._inflight_task_ids.add(task_id)
            return True

    @staticmethod
    def _clear_inflight(task_id: str) -> None:
        with TaskService._dispatch_lock:
            TaskService._inflight_task_ids.discard(task_id)

    @staticmethod
    def _mark_task_failed(app, task_id: str, error_message: str) -> None:
        with app.app_context():
            task = VideoTask.query.get(task_id)
            if task is None:
                return
            task.status = "failed"
            task.error_message = str(error_message)
            db.session.commit()

    @staticmethod
    def _attach_future_guard(app, task_id: str, future) -> None:
        def _done_callback(fut):
            try:
                exc = fut.exception()
            except Exception as callback_exc:
                TaskService._mark_task_failed(app, task_id, f"后台任务回调异常: {callback_exc}")
                return

            if exc is not None:
                TaskService._mark_task_failed(app, task_id, f"后台任务调度失败: {exc}")

        future.add_done_callback(_done_callback)

    @staticmethod
    def _start_video_task_thread(app, task_id: str) -> bool:
        if not TaskService._mark_inflight(task_id):
            return False

        def _runner() -> None:
            try:
                TaskService._run_video_task(app, task_id)
            except Exception as exc:
                TaskService._mark_task_failed(app, task_id, f"后台任务线程异常: {exc}")
            finally:
                TaskService._clear_inflight(task_id)

        try:
            threading.Thread(target=_runner, daemon=True, name=f"video-task-{str(task_id)[:8]}").start()
            return True
        except Exception:
            TaskService._clear_inflight(task_id)
            raise

    @staticmethod
    def recover_video_task(app, task_id: str) -> bool:
        with app.app_context():
            task = VideoTask.query.get(task_id)
            if task is None:
                return False
            if task.status in {"finished", "failed"}:
                return False

            if task.status == "queued":
                task.status = "running"
                task.progress = max(1, int(task.progress or 0))
                db.session.commit()

        started = TaskService._start_video_task_thread(app, str(task_id))
        return bool(started)

    @staticmethod
    def _get_detection_service(app) -> DetectionService:
        service = app.extensions.get("detection_service")
        if service is None:
            service = DetectionService(app)
            app.extensions["detection_service"] = service
        return service

    @staticmethod
    def submit_video_task(
        user_id: int,
        robot_id: int | None,
        video_path: Path,
        model_key: str | None = None,
        score_thresh: float = 0.25,
        use_cyclegan: bool = False,
        use_tracking: bool = False,
        simulate_realtime: bool = True,
        realtime_fps: float = 8.0,
    ) -> VideoTask:
        task = VideoTask(
            user_id=user_id,
            robot_id=robot_id,
            video_path=str(video_path),
            status="queued",
            progress=0,
            result_json={
                "model_key": model_key or "",
                "score_thresh": score_thresh,
                "use_cyclegan": use_cyclegan,
                "use_tracking": use_tracking,
                "simulate_realtime": simulate_realtime,
                "realtime_fps": realtime_fps,
            },
        )
        db.session.add(task)
        db.session.commit()

        app = current_app._get_current_object()

        # Mark as running immediately to avoid long-lived queued status when workers are starved.
        task.status = "running"
        task.progress = 1
        db.session.commit()

        try:
            TaskService.recover_video_task(app, str(task.id))
        except Exception as exc:
            TaskService._mark_task_failed(app, task.id, f"视频任务线程启动失败: {exc}")
        return task

    @staticmethod
    def _run_video_task(app, task_id: str) -> None:
        with app.app_context():
            task = None
            try:
                task = VideoTask.query.get(task_id)
                if task is None:
                    return

                task.status = "running"
                task.progress = max(5, int(task.progress or 0))
                db.session.commit()

                res_json = task.result_json or {}
                model_key = str(res_json.get("model_key", "") or "")
                score_thresh = float(res_json.get("score_thresh", 0.25) or 0.25)
                use_cyclegan = bool(res_json.get("use_cyclegan", False))
                use_tracking = bool(res_json.get("use_tracking", False))
                simulate_realtime = bool(res_json.get("simulate_realtime", True))
                realtime_fps = float(res_json.get("realtime_fps", 8.0) or 8.0)

                service = TaskService._get_detection_service(app)
                output_dir = Path(app.config["UPLOAD_DIR"]) / "videos" / "annotated"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_video_path = output_dir / f"{task.id}_{Path(task.video_path).stem}_annotated.mp4"

                def _on_progress(p: int) -> None:
                    if p > (task.progress or 0):
                        task.progress = min(99, int(p))
                        db.session.commit()

                summary = service.detect_video_summary(
                    video_path=Path(task.video_path),
                    score_thresh=score_thresh,
                    model_key=model_key or None,
                    use_cyclegan=use_cyclegan,
                    use_tracking=use_tracking,
                    simulate_realtime=simulate_realtime,
                    realtime_fps=realtime_fps,
                    save_annotated=True,
                    output_video_path=output_video_path,
                    progress_callback=_on_progress,
                )

                dominant = str(summary.get("dominant_type") or "none")
                avg_conf = float(summary.get("avg_confidence", 0.0) or 0.0)

                task.result_json = summary
                task.status = "finished"
                task.progress = 100

                db.session.add(
                    DetectionRecord(
                        user_id=task.user_id,
                        robot_id=task.robot_id,
                        source_type="video",
                        media_path=task.video_path,
                        detected_type=dominant,
                        is_trash=service._is_trash_class(dominant),
                        confidence=max(0.0, min(1.0, avg_conf)),
                        details_json=task.result_json,
                    )
                )
                db.session.commit()
            except Exception as exc:
                if task is None:
                    task = VideoTask.query.get(task_id)
                if task is not None:
                    task.status = "failed"
                    task.error_message = str(exc)
                    db.session.commit()
