# -*- coding: utf-8 -*-
"""web_system环境地址，账号，路径等配置信息"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
REPORTS_DIR = PROJECT_ROOT / "reports"
SCREENSHOT_DIR = REPORTS_DIR / "screenshots"

BASE_URL = os.getenv("HXZJ_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
WEB_URL = os.getenv("HXZJ_WEB_URL", "http://127.0.0.1:5173").rstrip("/")

ACCOUNTS = {
    "admin": {"username": "admin", "password": "admin123", "role": "admin"},
    "user1": {"username": "user1", "password": "user123", "role": "user"},
    "user2": {"username": "user2", "password": "user123", "role": "user"},
}

# 被测系统已绑定的机器人：user1 -> ROV-001(id=1)，user2 -> ROV-002(id=2)
USER_ROBOT = {"user1": 1, "user2": 2, "admin": None}

for _d in (ASSETS_DIR, REPORTS_DIR, SCREENSHOT_DIR):
    _d.mkdir(parents=True, exist_ok=True)
