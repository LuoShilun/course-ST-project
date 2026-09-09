from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import sys

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api import detection


class _DummyQuery:
    def __init__(self, task: SimpleNamespace):
        self._task = task

    def get(self, _task_id: str):
        return self._task


class VideoPreviewApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = Flask(__name__)
        self.user = SimpleNamespace(id=1, role="user")

    def test_preview_endpoint_prefers_web_preview_video(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            raw_video = tmp / "raw.mp4"
            annotated_video = tmp / "annotated.mp4"
            web_preview_video = tmp / "annotated_web.mp4"

            raw_video.write_bytes(b"RAW_VIDEO")
            annotated_video.write_bytes(b"ANNOTATED_VIDEO")
            web_preview_video.write_bytes(b"WEB_PREVIEW_VIDEO")

            task = SimpleNamespace(
                id="task-1",
                user_id=1,
                video_path=str(raw_video),
                result_json={
                    "output_video_path": str(annotated_video),
                    "output_video_preview_path": str(web_preview_video),
                    "output_video_web_playable": True,
                },
            )

            with self.app.test_request_context("/api/detection/video/tasks/task-1/preview"):
                with patch.object(detection, "get_current_user", return_value=self.user):
                    with patch.object(detection.VideoTask, "query", _DummyQuery(task)):
                        response = detection.preview_video_task.__wrapped__("task-1")

            try:
                self.assertEqual(response.status_code, 200)
                response.direct_passthrough = False
                self.assertEqual(response.get_data(), b"WEB_PREVIEW_VIDEO")
            finally:
                response.close()

    def test_preview_endpoint_returns_annotated_when_no_web_preview(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            raw_video = tmp / "raw.mp4"
            annotated_video = tmp / "annotated.mp4"

            raw_video.write_bytes(b"RAW_VIDEO")
            annotated_video.write_bytes(b"ANNOTATED_VIDEO")

            task = SimpleNamespace(
                id="task-2",
                user_id=1,
                video_path=str(raw_video),
                result_json={
                    "output_video_path": str(annotated_video),
                    "output_video_web_playable": False,
                },
            )
            fake_service = SimpleNamespace(
                _build_web_preview_video=lambda _p: (annotated_video, False),
            )

            with self.app.test_request_context("/api/detection/video/tasks/task-2/preview"):
                with patch.object(detection, "get_current_user", return_value=self.user):
                    with patch.object(detection.VideoTask, "query", _DummyQuery(task)):
                        with patch.object(detection, "_get_detection_service", return_value=fake_service):
                            with patch.object(detection.db.session, "commit", Mock()):
                                response = detection.preview_video_task.__wrapped__("task-2")

            try:
                self.assertEqual(response.status_code, 200)
                response.direct_passthrough = False
                self.assertEqual(response.get_data(), b"ANNOTATED_VIDEO")
            finally:
                response.close()

    def test_preview_endpoint_transcodes_on_demand_for_legacy_task(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            raw_video = tmp / "raw.mp4"
            annotated_video = tmp / "annotated.mp4"
            web_preview_video = tmp / "annotated_web.mp4"

            raw_video.write_bytes(b"RAW_VIDEO")
            annotated_video.write_bytes(b"ANNOTATED_VIDEO")
            web_preview_video.write_bytes(b"WEB_PREVIEW_VIDEO")

            task = SimpleNamespace(
                id="task-3",
                user_id=1,
                video_path=str(raw_video),
                result_json={
                    "output_video_path": str(annotated_video),
                    "output_video_web_playable": False,
                },
            )
            fake_service = SimpleNamespace(
                _build_web_preview_video=lambda _p: (web_preview_video, True),
            )

            with self.app.test_request_context("/api/detection/video/tasks/task-3/preview"):
                with patch.object(detection, "get_current_user", return_value=self.user):
                    with patch.object(detection.VideoTask, "query", _DummyQuery(task)):
                        with patch.object(detection, "_get_detection_service", return_value=fake_service):
                            with patch.object(detection.db.session, "commit", Mock()):
                                response = detection.preview_video_task.__wrapped__("task-3")

            try:
                self.assertEqual(response.status_code, 200)
                response.direct_passthrough = False
                self.assertEqual(response.get_data(), b"WEB_PREVIEW_VIDEO")
                self.assertEqual(task.result_json.get("output_video_preview_path"), str(web_preview_video))
                self.assertTrue(bool(task.result_json.get("output_video_web_playable")))
            finally:
                response.close()


if __name__ == "__main__":
    unittest.main()
