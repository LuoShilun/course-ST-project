from __future__ import annotations

from flask import Blueprint, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, verify_jwt_in_request

from app.models import User
from app.services.auth_service import AuthService
from app.utils.auth import get_current_user
from app.utils.response import api_error, api_success

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    display_name = str(data.get("display_name", username)).strip() or username
    role = str(data.get("role", "user")).strip() or "user"

    if not username or not password:
        return api_error("用户名和密码不能为空", code=4001)
    if role not in {"user", "admin"}:
        return api_error("角色不合法", code=4002)

    if role == "admin" and User.query.count() > 0:
        verify_jwt_in_request()
        me = get_current_user()
        if me is None or me.role != "admin":
            return api_error("创建管理员账号需要管理员令牌", code=4031, http_status=403)

    try:
        user = AuthService.create_user(
            username=username,
            password=password,
            display_name=display_name,
            role=role,
        )
    except ValueError as exc:
        return api_error(str(exc), code=4003)

    return api_success(user.to_dict(), message="注册成功")


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if not username or not password:
        return api_error("用户名和密码不能为空", code=4001)

    user = AuthService.authenticate(username=username, password=password)
    if user is None:
        return api_error("用户名或密码错误", code=4010, http_status=401)

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return api_success(
        {
            "access_token": token,
            "user": user.to_dict(),
        },
        message="登录成功",
    )


@bp.get("/me")
@jwt_required()
def me():
    user = get_current_user()
    if user is None:
        return api_error("用户不存在", code=4011, http_status=401)
    return api_success(user.to_dict())


@bp.post("/logout")
@jwt_required()
def logout():
    identity = get_jwt_identity()
    return api_success({"user_id": identity}, message="退出登录成功")
