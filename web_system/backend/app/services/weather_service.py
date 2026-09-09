from __future__ import annotations

from datetime import datetime, timedelta

import requests

from app.extensions import db
from app.models import WeatherCache


class WeatherService:
    @staticmethod
    def get_weather(city: str, api_key: str, base_url: str) -> dict:
        now = datetime.utcnow()
        cache = WeatherCache.query.filter_by(city=city).first()
        if cache and cache.expires_at > now:
            return cache.payload_json

        if api_key:
            try:
                payload = WeatherService._fetch_from_qweather(city=city, api_key=api_key, base_url=base_url)
            except Exception:
                payload = WeatherService._mock_weather(city)
        else:
            payload = WeatherService._mock_weather(city)

        if cache is None:
            cache = WeatherCache(city=city, payload_json=payload, expires_at=now + timedelta(minutes=30), updated_at=now)
            db.session.add(cache)
        else:
            cache.payload_json = payload
            cache.expires_at = now + timedelta(minutes=30)
            cache.updated_at = now
        db.session.commit()

        return payload

    @staticmethod
    def _fetch_from_qweather(city: str, api_key: str, base_url: str) -> dict:
        # QWeather free APIs use location id. This project keeps a lightweight city name mock fallback.
        # For production, map city name to location id first with geo API.
        resp = requests.get(base_url, params={"location": city, "key": api_key}, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", [])
        today = daily[0] if daily else {}
        return {
            "city": city,
            "text_day": today.get("textDay", "未知"),
            "temp_max": today.get("tempMax", "-"),
            "temp_min": today.get("tempMin", "-"),
            "wind_dir": today.get("windDirDay", "-"),
            "wind_scale": today.get("windScaleDay", "-"),
            "source": "和风天气",
        }

    @staticmethod
    def _mock_weather(city: str) -> dict:
        return {
            "city": city,
            "text_day": "多云",
            "temp_max": "28",
            "temp_min": "22",
            "wind_dir": "东南风",
            "wind_scale": "3",
            "source": "模拟数据",
        }
