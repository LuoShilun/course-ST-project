from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User


class AuthService:
    @staticmethod
    def create_user(username: str, password: str, display_name: str, role: str = "user") -> User:
        if User.query.filter_by(username=username).first() is not None:
            raise ValueError("用户名已存在")

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            display_name=display_name,
            role=role,
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def authenticate(username: str, password: str) -> User | None:
        user = User.query.filter_by(username=username).first()
        if user is None or not user.is_active:
            return None
        if not check_password_hash(user.password_hash, password):
            return None
        return user

    @staticmethod
    def set_password(user: User, new_password: str) -> None:
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
