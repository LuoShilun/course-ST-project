from __future__ import annotations



import os

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;2000000|timeout;2000000"

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"



from pathlib import Path



from dotenv import load_dotenv

from flask import Flask

from sqlalchemy import inspect, text

from werkzeug.security import generate_password_hash



from app.extensions import cors, db, jwt

from app.models import Announcement, Robot, User, UserRobotLink





def create_app() -> Flask:

    # Keep runtime behavior aligned with backend/.env even when parent process exports old values.

    env_path = Path(__file__).resolve().parents[1] / ".env"

    load_dotenv(dotenv_path=env_path, override=True)



    # Import after loading .env so class-level config values read fresh env vars.

    from app.config import get_config



    app = Flask(__name__)

    app.config.from_object(get_config())



    upload_dir = Path(app.config["UPLOAD_DIR"])

    upload_dir.mkdir(parents=True, exist_ok=True)



    db.init_app(app)

    jwt.init_app(app)

    cors.init_app(app, origins=app.config.get("CORS_ORIGINS", ["*"]), supports_credentials=True)



    with app.app_context():

        _ensure_schema_compat()



    from app.api import register_blueprints



    register_blueprints(app)

    register_cli(app)

    return app





def _ensure_schema_compat() -> None:

    inspector = inspect(db.engine)

    table_names = set(inspector.get_table_names())



    if "system_configs" not in table_names:

        if db.engine.dialect.name == "mysql":

            db.session.execute(

                text(

                    "CREATE TABLE IF NOT EXISTS system_configs ("

                    "`key` VARCHAR(100) NOT NULL, "

                    "`value` VARCHAR(255) NULL, "

                    "PRIMARY KEY (`key`)"

                    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

                )

            )

        else:

            db.session.execute(

                text(

                    "CREATE TABLE IF NOT EXISTS system_configs ("

                    "key VARCHAR(100) NOT NULL PRIMARY KEY, "

                    "value VARCHAR(255)"

                    ")"

                )

            )

        db.session.commit()



    if "robots" not in table_names:

        return

    columns = {col["name"] for col in inspector.get_columns("robots")}

    if "rtsp_url" not in columns:

        db.session.execute(text("ALTER TABLE robots ADD COLUMN rtsp_url VARCHAR(255)"))

        db.session.commit()

    db.session.execute(

        text(

            "UPDATE robots SET rtsp_url = :url "

            "WHERE robot_code = 'ROV-001' AND (rtsp_url IS NULL OR rtsp_url = '')"

        ),

        {"url": "rtsp://localhost:8554/live/cam01"},

    )

    db.session.commit()





def register_cli(app):
    pass
