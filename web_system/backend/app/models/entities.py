from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import UniqueConstraint

from app.extensions import db


def utcnow() -> datetime:
    return datetime.utcnow()


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    robot_links = db.relationship("UserRobotLink", back_populates="user", cascade="all, delete-orphan")
    detection_records = db.relationship("DetectionRecord", back_populates="user")
    assistant_sessions = db.relationship("AssistantSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = db.relationship("AuditLog", back_populates="user")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Robot(TimestampMixin, db.Model):
    __tablename__ = "robots"

    id = db.Column(db.Integer, primary_key=True)
    robot_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    capacity_total = db.Column(db.Float, nullable=False, default=100.0)
    capacity_used = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), nullable=False, default="available")
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    is_online = db.Column(db.Boolean, nullable=False, default=False)
    rtsp_url = db.Column(db.String(255), nullable=True)
    last_heartbeat = db.Column(db.DateTime, nullable=True)

    user_links = db.relationship("UserRobotLink", back_populates="robot", cascade="all, delete-orphan")
    detection_records = db.relationship("DetectionRecord", back_populates="robot")
    video_tasks = db.relationship("VideoTask", back_populates="robot")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "robot_code": self.robot_code,
            "name": self.name,
            "capacity_total": self.capacity_total,
            "capacity_used": self.capacity_used,
            "capacity_free": max(self.capacity_total - self.capacity_used, 0.0),
            "status": self.status,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "is_online": self.is_online,
            "rtsp_url": self.rtsp_url,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserRobotLink(TimestampMixin, db.Model):
    __tablename__ = "user_robot_links"
    __table_args__ = (UniqueConstraint("user_id", "robot_id", name="uq_user_robot"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    robot_id = db.Column(db.Integer, db.ForeignKey("robots.id"), nullable=False, index=True)
    alias = db.Column(db.String(100), nullable=True)

    user = db.relationship("User", back_populates="robot_links")
    robot = db.relationship("Robot", back_populates="user_links")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "robot_id": self.robot_id,
            "alias": self.alias,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DetectionRecord(db.Model):
    __tablename__ = "detection_records"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    robot_id = db.Column(db.Integer, db.ForeignKey("robots.id"), nullable=True, index=True)

    source_type = db.Column(db.String(20), nullable=False, default="image")
    media_path = db.Column(db.String(255), nullable=True)
    detected_type = db.Column(db.String(50), nullable=False)
    is_trash = db.Column(db.Boolean, nullable=False, default=True)
    confidence = db.Column(db.Float, nullable=False, default=0.0)
    details_json = db.Column(db.JSON, nullable=True)
    detected_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    user = db.relationship("User", back_populates="detection_records")
    robot = db.relationship("Robot", back_populates="detection_records")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "robot_id": self.robot_id,
            "robot_code": self.robot.robot_code if self.robot else None,
            "source_type": self.source_type,
            "media_path": self.media_path,
            "detected_type": self.detected_type,
            "is_trash": self.is_trash,
            "highlight": self.is_trash,
            "confidence": self.confidence,
            "details": self.details_json or {},
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }


class VideoTask(TimestampMixin, db.Model):
    __tablename__ = "video_tasks"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    robot_id = db.Column(db.Integer, db.ForeignKey("robots.id"), nullable=True, index=True)
    video_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="queued", index=True)
    progress = db.Column(db.Integer, nullable=False, default=0)
    result_json = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    robot = db.relationship("Robot", back_populates="video_tasks")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "robot_id": self.robot_id,
            "robot_code": self.robot.robot_code if self.robot else None,
            "video_path": self.video_path,
            "status": self.status,
            "progress": self.progress,
            "result": self.result_json or {},
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Announcement(TimestampMixin, db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    start_at = db.Column(db.DateTime, nullable=True)
    end_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "pinned": self.pinned,
            "start_at": self.start_at.isoformat() if self.start_at else None,
            "end_at": self.end_at.isoformat() if self.end_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WeatherCache(db.Model):
    __tablename__ = "weather_cache"

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(50), unique=True, nullable=False)
    payload_json = db.Column(db.JSON, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class SystemConfig(db.Model):
    __tablename__ = "system_configs"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(255), nullable=True)


class AssistantSession(TimestampMixin, db.Model):
    __tablename__ = "assistant_sessions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False, default="新建会话")

    user = db.relationship("User", back_populates="assistant_sessions")
    messages = db.relationship("AssistantMessage", back_populates="session", cascade="all, delete-orphan")


class AssistantMessage(db.Model):
    __tablename__ = "assistant_messages"

    id = db.Column(db.BigInteger, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("assistant_sessions.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sources_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    session = db.relationship("AssistantSession", back_populates="messages")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "sources": self.sources_json or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.String(64), nullable=True)
    detail_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    user = db.relationship("User", back_populates="audit_logs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "detail": self.detail_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
