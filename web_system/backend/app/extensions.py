from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
video_executor = ThreadPoolExecutor(max_workers=2)
