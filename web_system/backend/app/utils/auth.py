from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.models import User
from app.utils.response import api_error


def get_current_user() -> User | None:
    identity = get_jwt_identity()
    if identity is None:
        return None
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return User.query.get(user_id)


def roles_required(*roles: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    role_set = {r.strip() for r in roles if r.strip()}

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            verify_jwt_in_request()
            user = get_current_user()
            if user is None:
                return api_error("用户不存在或令牌无效", code=4011, http_status=401)
            if not user.is_active:
                return api_error("用户已被禁用", code=4012, http_status=403)
            if role_set and user.role not in role_set:
                return api_error("权限不足", code=4031, http_status=403)
            return func(*args, **kwargs)

        return wrapper

    return decorator
