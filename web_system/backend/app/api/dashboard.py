from __future__ import annotations

from flask import Blueprint, current_app, request

from app.models import Announcement
from app.services.stats_service import StatsService
from app.services.weather_service import WeatherService
from app.utils.auth import get_current_user, roles_required
from app.utils.response import api_success

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

COMMON_APPS = [
    {"name": "数据大屏", "path": "/dashboard", "icon": "TrendCharts"},
    {"name": "机器人地图", "path": "/map", "icon": "Location"},
    {"name": "垃圾检测", "path": "/detect", "icon": "Camera"},
    {"name": "智能助手", "path": "/assistant", "icon": "ChatDotRound"},
]

SLOGANS = [
    "早识别，快清理。",
    "让水下生态看得见。",
    "用数据守护海洋环境。",
]


@bp.get("/home")
@roles_required("admin", "user")
def home_data():
    user = get_current_user()
    assert user is not None

    city = str(request.args.get("city", "深圳"))
    weather = WeatherService.get_weather(
        city=city,
        api_key=str(current_app.config.get("QWEATHER_API_KEY", "")),
        base_url=str(current_app.config.get("QWEATHER_BASE_URL", "")),
    )

    announcements = Announcement.query.order_by(Announcement.pinned.desc(), Announcement.created_at.desc()).limit(8).all()

    return api_success(
        {
            "overview": StatsService.home(user),
            "announcements": [a.to_dict() for a in announcements],
            "common_apps": COMMON_APPS,
            "weather": weather,
            "slogans": SLOGANS,
        }
    )


@bp.get("/bigscreen")
@roles_required("admin", "user")
def bigscreen_data():
    user = get_current_user()
    assert user is not None
    return api_success(StatsService.bigscreen(user))
