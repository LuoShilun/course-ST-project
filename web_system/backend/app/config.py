from __future__ import annotations

import os
from pathlib import Path
from datetime import timedelta


class Config:
    BASE_DIR = Path(__file__).resolve().parents[1]
    WEB_ROOT = BASE_DIR.parent
    REPO_ROOT = WEB_ROOT.parent

    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "5000"))

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", "24")))

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://root:123456@127.0.0.1:3306/underwater_system?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "0") == "1"

    CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]

    UPLOAD_DIR = (BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")).resolve()

    QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
    QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
    QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

    QWEATHER_API_KEY = os.getenv("QWEATHER_API_KEY", "")
    QWEATHER_BASE_URL = os.getenv("QWEATHER_BASE_URL", "https://devapi.qweather.com/v7/weather/3d")

    MODEL_DEFAULT_STUDENT_CKPT = os.getenv(
        "MODEL_DEFAULT_STUDENT_CKPT",
        "../../experiments/runs/distill_20260329_141841/checkpoints/best_val.pth",
    )
    MODEL_ENABLE_INFERENCE = os.getenv("MODEL_ENABLE_INFERENCE", "0") == "1"
    MODEL_DEVICE = os.getenv("MODEL_DEVICE", "auto")
    MODEL_CYCLEGAN_CKPT = os.getenv("MODEL_CYCLEGAN_CKPT", "app/models/ami_cyclegan.pth")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


def get_config() -> type[Config]:
    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig
