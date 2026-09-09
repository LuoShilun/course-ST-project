from __future__ import annotations

from datetime import datetime
import math

from flask import Blueprint, request

from app.extensions import db
from app.models import DetectionRecord, UserRobotLink
from app.utils.auth import get_current_user, roles_required
from app.utils.response import api_error, api_success

bp = Blueprint("records", __name__, url_prefix="/api/records")


def _can_access_robot(user_id: int, robot_id: int) -> bool:
    return UserRobotLink.query.filter_by(user_id=user_id, robot_id=robot_id).first() is not None


def _validate_record_fields(data: dict, *, creating: bool = False) -> dict:
    """Validate all shared fields before applying any changes to an ORM row."""
    fields = {}
    if creating or "detected_type" in data:
        value = data.get("detected_type")
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 50:
            raise ValueError("detected_type 必须为 1 到 50 个字符的非空字符串")
        fields["detected_type"] = value.strip()
    if creating or "confidence" in data:
        value = data.get("confidence", 0.0)
        try:
            confidence = float(value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("confidence 必须为 0 到 1 之间的有限数值") from None
        if isinstance(value, bool) or not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence 必须为 0 到 1 之间的有限数值")
        fields["confidence"] = confidence
    if creating or "is_trash" in data:
        value = data.get("is_trash", True)
        if not isinstance(value, bool):
            raise ValueError("is_trash 必须为 JSON 布尔值 true 或 false")
        fields["is_trash"] = value
    return fields


@bp.get("")
@roles_required("admin", "user")
def list_records():
    user = get_current_user()
    assert user is not None

    try:
        page = max(int(request.args.get("page", 1)), 1)
        page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)
        robot_id_raw = request.args.get("robot_id")
        robot_id = int(robot_id_raw) if robot_id_raw else None
    except (TypeError, ValueError, OverflowError):
        return api_error("page、page_size 和 robot_id 必须为整数", code=4002)

    q = DetectionRecord.query
    if user.role != "admin":
        q = q.filter(DetectionRecord.user_id == user.id)

    source_type = str(request.args.get("source_type", "")).strip()
    if source_type:
        q = q.filter(DetectionRecord.source_type == source_type)

    if robot_id is not None:
        q = q.filter(DetectionRecord.robot_id == robot_id)

    is_trash = request.args.get("is_trash")
    if is_trash in {"0", "1"}:
        q = q.filter(DetectionRecord.is_trash.is_(is_trash == "1"))

    q = q.order_by(DetectionRecord.detected_at.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    return api_success(
        {
            "items": [r.to_dict() for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@bp.post("")
@roles_required("admin", "user")
def create_record():
    user = get_current_user()
    assert user is not None

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return api_error("请求体必须为 JSON 对象", code=4001)
    robot_id = data.get("robot_id")
    if robot_id is not None:
        robot_id = int(robot_id)
        if user.role != "admin" and not _can_access_robot(user.id, robot_id):
            return api_error("无权访问该机器人", code=4031, http_status=403)

    try:
        fields = _validate_record_fields(data, creating=True)
    except ValueError as exc:
        return api_error(str(exc), code=4001)

    detected_at_str = str(data.get("detected_at", "")).strip()
    try:
        detected_at = datetime.fromisoformat(detected_at_str) if detected_at_str else datetime.utcnow()
    except ValueError:
        return api_error("detected_at 必须为有效的 ISO 8601 日期时间", code=4003)

    row = DetectionRecord(
        user_id=user.id if user.role != "admin" else int(data.get("user_id", user.id)),
        robot_id=robot_id,
        source_type=str(data.get("source_type", "image")),
        media_path=str(data.get("media_path", "")) or None,
        **fields,
        details_json=data.get("details", {}),
        detected_at=detected_at,
    )
    db.session.add(row)
    db.session.commit()

    return api_success(row.to_dict(), message="创建成功")


@bp.put("/<int:record_id>")
@roles_required("admin", "user")
def update_record(record_id: int):
    user = get_current_user()
    assert user is not None

    row = DetectionRecord.query.get(record_id)
    if row is None:
        return api_error("记录不存在", code=4041, http_status=404)
    if user.role != "admin" and row.user_id != user.id:
        return api_error("无权访问该记录", code=4031, http_status=403)

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return api_error("请求体必须为 JSON 对象", code=4001)
    try:
        fields = _validate_record_fields(data)
    except ValueError as exc:
        return api_error(str(exc), code=4001)
    for key, value in fields.items():
        setattr(row, key, value)
    for key in ["source_type", "media_path"]:
        if key in data:
            setattr(row, key, str(data.get(key)))
    if "details" in data:
        row.details_json = data.get("details")

    db.session.commit()
    return api_success(row.to_dict(), message="更新成功")


@bp.delete("/<int:record_id>")
@roles_required("admin", "user")
def delete_record(record_id: int):
    user = get_current_user()
    assert user is not None

    row = DetectionRecord.query.get(record_id)
    if row is None:
        return api_error("记录不存在", code=4041, http_status=404)
    if user.role != "admin" and row.user_id != user.id:
        return api_error("无权访问该记录", code=4031, http_status=403)

    db.session.delete(row)
    db.session.commit()
    return api_success(message="删除成功")
