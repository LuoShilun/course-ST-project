from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func

from app.models import DetectionRecord, Robot, User, UserRobotLink


class StatsService:
    @staticmethod
    def _allowed_robot_ids(user: User) -> list[int] | None:
        if user.role == "admin":
            return None
        rows = UserRobotLink.query.filter_by(user_id=user.id).all()
        return [r.robot_id for r in rows]

    @classmethod
    def home(cls, user: User) -> dict:
        allowed_robot_ids = cls._allowed_robot_ids(user)

        user_count = User.query.count() if user.role == "admin" else 1

        q = DetectionRecord.query
        if user.role != "admin":
            q = q.filter(DetectionRecord.user_id == user.id)

        total_records = q.count()
        trash_records = q.filter(DetectionRecord.is_trash.is_(True)).count()

        robot_q = Robot.query
        if allowed_robot_ids is not None:
            robot_q = robot_q.filter(Robot.id.in_(allowed_robot_ids))
        online_robots = robot_q.filter(Robot.is_online.is_(True)).count()

        return {
            "user_count": user_count,
            "total_records": total_records,
            "trash_records": trash_records,
            "online_robots": online_robots,
        }

    @classmethod
    def bigscreen(cls, user: User) -> dict:
        allowed_robot_ids = cls._allowed_robot_ids(user)

        now = datetime.utcnow()
        day_start = datetime(now.year, now.month, now.day)

        q = DetectionRecord.query
        if user.role != "admin":
            q = q.filter(DetectionRecord.user_id == user.id)

        today_q = q.filter(DetectionRecord.detected_at >= day_start)
        today_total = today_q.count()

        class_rows = (
            today_q.with_entities(DetectionRecord.detected_type, func.count(DetectionRecord.id))
            .group_by(DetectionRecord.detected_type)
            .all()
        )
        class_counts = [{"name": name, "value": count} for name, count in class_rows]

        trend = []
        for i in range(9, -1, -1):
            day = day_start - timedelta(days=i)
            day_end = day + timedelta(days=1)
            dq = q.filter(DetectionRecord.detected_at >= day, DetectionRecord.detected_at < day_end)
            total_count = dq.count()
            trash_count = dq.filter(DetectionRecord.is_trash.is_(True)).count()
            trend.append(
                {
                    "date": day.strftime("%Y-%m-%d"),
                    "total": total_count,
                    "trash": trash_count,
                }
            )

        robot_q = Robot.query
        if allowed_robot_ids is not None:
            robot_q = robot_q.filter(Robot.id.in_(allowed_robot_ids))
        robots = robot_q.all()
        radar = []
        for robot in robots:
            utilization = 0.0
            if robot.capacity_total > 0:
                utilization = robot.capacity_used / robot.capacity_total * 100.0
            radar.append(
                {
                    "name": robot.name,
                    "value": round(utilization, 2),
                    "robot_code": robot.robot_code,
                }
            )

        record_rows = q.order_by(DetectionRecord.detected_at.desc()).limit(50).all()
        records = [
            {
                "robot_code": r.robot.robot_code if r.robot else "N/A",
                "detected_at": r.detected_at.isoformat(),
                "detected_type": r.detected_type,
                "is_trash": r.is_trash,
            }
            for r in record_rows
        ]

        return {
            "today_total": today_total,
            "class_counts": class_counts,
            "trend": trend,
            "pie": class_counts,
            "robot_radar": radar,
            "records": records,
        }
