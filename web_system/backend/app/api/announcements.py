from __future__ import annotations

from datetime import datetime

from flask import Blueprint, request

from app.extensions import db
from app.models import Announcement
from app.utils.auth import roles_required
from app.utils.response import api_error, api_success

bp = Blueprint("announcements", __name__, url_prefix="/api/announcements")


@bp.get("")
def list_announcements():
    now = datetime.utcnow()
    q = Announcement.query
    q = q.filter((Announcement.start_at.is_(None)) | (Announcement.start_at <= now))
    q = q.filter((Announcement.end_at.is_(None)) | (Announcement.end_at >= now))
    rows = q.order_by(Announcement.pinned.desc(), Announcement.created_at.desc()).all()
    return api_success([r.to_dict() for r in rows])


@bp.post("")
@roles_required("admin")
def create_announcement():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    content = str(data.get("content", "")).strip()
    if not title or not content:
        return api_error("标题和内容不能为空", code=4001)

    row = Announcement(
        title=title,
        content=content,
        pinned=bool(data.get("pinned", False)),
    )
    db.session.add(row)
    db.session.commit()
    return api_success(row.to_dict(), message="创建成功")


@bp.put("/<int:announcement_id>")
@roles_required("admin")
def update_announcement(announcement_id: int):
    row = Announcement.query.get(announcement_id)
    if row is None:
        return api_error("公告不存在", code=4041, http_status=404)

    data = request.get_json(silent=True) or {}
    if "title" in data:
        row.title = str(data.get("title") or row.title)
    if "content" in data:
        row.content = str(data.get("content") or row.content)
    if "pinned" in data:
        row.pinned = bool(data.get("pinned"))

    db.session.commit()
    return api_success(row.to_dict(), message="更新成功")


@bp.delete("/<int:announcement_id>")
@roles_required("admin")
def delete_announcement(announcement_id: int):
    row = Announcement.query.get(announcement_id)
    if row is None:
        return api_error("公告不存在", code=4041, http_status=404)

    db.session.delete(row)
    db.session.commit()
    return api_success(message="删除成功")
