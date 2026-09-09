from __future__ import annotations

from typing import Any

from flask import jsonify


def api_success(data: Any = None, message: str = "成功", code: int = 0, http_status: int = 200):
    payload = {
        "code": code,
        "message": message,
        "data": data,
    }
    return jsonify(payload), http_status


def api_error(message: str, code: int = 4000, http_status: int = 400, data: Any = None):
    payload = {
        "code": code,
        "message": message,
        "data": data,
    }
    return jsonify(payload), http_status
