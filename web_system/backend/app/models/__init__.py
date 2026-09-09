from app.extensions import db
from app.models.entities import (
    Announcement,
    AssistantMessage,
    AssistantSession,
    AuditLog,
    DetectionRecord,
    Robot,
    SystemConfig,
    User,
    UserRobotLink,
    VideoTask,
    WeatherCache,
)

__all__ = [
    "db",
    "User",
    "Robot",
    "UserRobotLink",
    "DetectionRecord",
    "VideoTask",
    "Announcement",
    "WeatherCache",
    "SystemConfig",
    "AssistantSession",
    "AssistantMessage",
    "AuditLog",
]
