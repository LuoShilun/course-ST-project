from __future__ import annotations

from flask import Blueprint, current_app, request

from app.services.weather_service import WeatherService
from app.utils.auth import roles_required
from app.utils.response import api_success

bp = Blueprint("weather", __name__, url_prefix="/api/weather")


@bp.get("/current")
@roles_required("admin", "user")
def current_weather():
    city = str(request.args.get("city", "深圳"))
    data = WeatherService.get_weather(
        city=city,
        api_key=str(current_app.config.get("QWEATHER_API_KEY", "")),
        base_url=str(current_app.config.get("QWEATHER_BASE_URL", "")),
    )
    return api_success(data)
