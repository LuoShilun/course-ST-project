from __future__ import annotations

from flask import Blueprint, request

from app.extensions import db
from app.models import User, UserRobotLink
from app.services.auth_service import AuthService
from app.utils.auth import get_current_user, roles_required
from app.utils.response import api_error, api_success

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.get("")
@roles_required("admin")
def list_users():
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)

    q = User.query.order_by(User.created_at.desc())
    total = q.count()
    users = q.offset((page - 1) * page_size).limit(page_size).all()

    data = []
    for u in users:
        item = u.to_dict()
        item["robot_count"] = UserRobotLink.query.filter_by(user_id=u.id).count()
        data.append(item)

    return api_success({"items": data, "total": total, "page": page, "page_size": page_size})


@bp.post("")
@roles_required("admin")
def create_user():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    display_name = str(data.get("display_name", username)).strip() or username
    role = str(data.get("role", "user")).strip() or "user"

    if role not in {"user", "admin"}:
        return api_error("角色不合法", code=4002)

    if not username or not password:
        return api_error("用户名和密码不能为空", code=4001)

    try:
        user = AuthService.create_user(username=username, password=password, display_name=display_name, role=role)
    except ValueError as exc:
        return api_error(str(exc), code=4003)

    return api_success(user.to_dict(), message="创建成功")


@bp.put("/<int:user_id>")
@roles_required("admin")
def update_user(user_id: int):
    user = User.query.get(user_id)
    if user is None:
        return api_error("用户不存在", code=4041, http_status=404)

    data = request.get_json(silent=True) or {}
    if "display_name" in data:
        user.display_name = str(data.get("display_name") or user.display_name)
    if "role" in data:
        role = str(data.get("role") or user.role)
        if role not in {"user", "admin"}:
            return api_error("角色不合法", code=4002)
        user.role = role
    if "is_active" in data:
        user.is_active = bool(data.get("is_active"))

    if "password" in data and str(data.get("password", "")).strip():
        AuthService.set_password(user, str(data["password"]))
    else:
        db.session.commit()

    return api_success(user.to_dict(), message="更新成功")


@bp.delete("/<int:user_id>")
@roles_required("admin")
def delete_user(user_id: int):
    me = get_current_user()
    if me and me.id == user_id:
        return api_error("不能删除当前登录用户", code=4004)

    user = User.query.get(user_id)
    if user is None:
        return api_error("用户不存在", code=4041, http_status=404)

    db.session.delete(user)
    db.session.commit()
    return api_success(message="删除成功")
