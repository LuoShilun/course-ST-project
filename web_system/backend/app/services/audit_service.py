from __future__ import annotations

from typing import Any

from app.extensions import db
from app.models import AuditLog


class AuditService:
    @staticmethod
    def log(
        user_id: int | None,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        log = AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail_json=detail or {},
        )
        db.session.add(log)
        db.session.commit()
