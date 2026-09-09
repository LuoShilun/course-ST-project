from __future__ import annotations



import base64

import importlib.util

import io

import os

import random

import shutil

import subprocess

import sys

import threading

import time

import uuid

from collections import Counter

from pathlib import Path

from typing import Any, Callable



import numpy as np

from PIL import Image, ImageDraw





class DetectionService:

    LABEL_MAP = {

        1: "trash",

        2: "bio",

        3: "rov",

    }

    TRASH_LABELS = {1}



    _lock = threading.Lock()



    def __init__(self, app):

        self.app = app

        self.enable_inference = bool(app.config.get("MODEL_ENABLE_INFERENCE", False))

        self.model_dir = self._resolve_model_dir()

        self._model_cache: dict[str, Any] = {}

        self._model_errors: dict[str, str] = {}

        self._student_runtime: dict[str, Any] | None = None

        self._cyclegan_runtime: dict[str, Any] | None = None

        self._cyclegan_error: str | None = None

        self._cyclegan_ckpt_path = self._resolve_cyclegan_checkpoint_path()

        self._cyclegan_ckpt_signature: tuple[int, int] | None = None



    def list_models(self) -> list[dict[str, Any]]:

        items: list[dict[str, Any]] = []

        if self.model_dir.exists():

            for path in sorted(self.model_dir.iterdir()):

                if not path.is_file() or path.suffix.lower() not in {".pt", ".pth", ".onnx"}:

                    continue

                engine = self._infer_engine(path)

                items.append(

                    {

                        "key": path.name,

                        "display_name": path.stem,

                        "file_name": path.name,

                        "engine": engine,

                        "size_mb": round(path.stat().st_size / (1024 * 1024), 2),

                    }

                )



        if not items:

            items.append(

                {

                    "key": "mock-default",

                    "display_name": "榛樿�ゆā鎷熸ā鍨�",

                    "file_name": "-",

                    "engine": "mock",

                    "size_mb": 0.0,

                }

            )

        return items



    def detect_image(

        self,

        image_path: Path,

        score_thresh: float = 0.25,

        model_key: str | None = None,

        use_cyclegan: bool = False,

    ) -> dict[str, Any]:

        infer_image_path = image_path

        render_image_path = image_path

        cyclegan_applied = False

        cyclegan_error = None

        cyclegan_runtime = None



        if use_cyclegan:

            enhanced_path, enhance_err = self._enhance_image_with_cyclegan(image_path)

            if enhanced_path is not None:

                infer_image_path = enhanced_path

                render_image_path = enhanced_path

                cyclegan_applied = True

                cyclegan_runtime = self._cyclegan_runtime

            else:

                cyclegan_error = enhance_err



        selected_model = self._resolve_model(model_key)

        detections, model_status, model_error = self._predict(

            image_path=infer_image_path,

            score_thresh=score_thresh,

            selected_model=selected_model,

        )

        trash_count = sum(1 for d in detections if d["is_trash"])

        source_image = self._encode_image_data_url(render_image_path)

        annotated_image = self._render_annotated_image(render_image_path, detections)

        return {

            "detections": detections,

            "summary": {

                "total": len(detections),

                "trash_count": trash_count,

            },

            "model_status": model_status,

            "model_error": model_error,

            "selected_model": selected_model,

            "inference_enabled": self.enable_inference,

            "enhanced_by_cyclegan": use_cyclegan,

            "cyclegan_applied": cyclegan_applied,

            "cyclegan_error": cyclegan_error,

            "cyclegan_checkpoint": (cyclegan_runtime or {}).get("checkpoint"),

            "cyclegan_epoch": (cyclegan_runtime or {}).get("epoch"),

            "cyclegan_arch": (cyclegan_runtime or {}).get("arch"),

            "source_image": source_image,

            "annotated_image": annotated_image,

        }



    def detect_video_summary(

        self,

        video_path: Path,

        score_thresh: float = 0.25,

        model_key: str | None = None,

        use_cyclegan: bool = False,

        use_tracking: bool = False,

        simulate_realtime: bool = True,

        realtime_fps: float = 8.0,

        save_annotated: bool = False,

        output_video_path: Path | None = None,

        progress_callback: Callable[[int], None] | None = None,

    ) -> dict[str, Any]:

        selected_model = self._resolve_model(model_key)

        key = str(selected_model.get("key", "mock-default"))

        engine = str(selected_model.get("engine", "mock"))

        tracking_backend = "bytetrack" if use_tracking else "disabled"

        tracking_error: str | None = None



        if key == "mock-default":

            summary = self._mock_video_summary(video_path=video_path, model_key=key, score_thresh=score_thresh)

            summary.update(

                {

                    "model_status": "mock_only",

                    "model_error": None,

                    "enhanced_by_cyclegan": use_cyclegan,

                    "tracking_enabled": use_tracking,

                    "tracking_backend": "mock",

                    "tracking_error": None,

                    "simulate_realtime": simulate_realtime,

                    "realtime_fps": realtime_fps,

                    "inference_enabled": self.enable_inference,

                }

            )

            if progress_callback:

                progress_callback(100)

            return summary



        model_path = self.model_dir / key

        if not model_path.exists() or not self.enable_inference or engine != "yolo":

            reason = None

            status = "mock_only"

            if not model_path.exists():

                status = "fallback"

                reason = f"妯″瀷鏂囦欢涓嶅瓨鍦? {model_path}"

            elif engine != "yolo":

                status = "fallback"

                reason = f"瑙嗛�戞帹鐞嗘殏涓嶆敮鎸佽�ユā鍨嬬被鍨? {engine}"



            summary = self._mock_video_summary(video_path=video_path, model_key=key, score_thresh=score_thresh)

            summary.update(

                {

                    "model_status": status,

                    "model_error": reason,

                    "enhanced_by_cyclegan": use_cyclegan,

                    "tracking_enabled": use_tracking,

                    "tracking_backend": "fallback",

                    "tracking_error": None,

                    "simulate_realtime": simulate_realtime,

                    "realtime_fps": realtime_fps,

                    "inference_enabled": self.enable_inference,

                }

            )

            if progress_callback:

                progress_callback(100)

            return summary



        try:

            from ultralytics import YOLO

            import cv2



            cache_key = model_path.name

            model = self._model_cache.get(cache_key)

            if model is None:

                model = YOLO(str(model_path))

                self._model_cache[cache_key] = model



            total_frames = 0

            fps = 0.0

            width = 0

            height = 0

            cap = cv2.VideoCapture(str(video_path))

            if cap.isOpened():

                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

                fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)

                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)

                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

            cap.release()



            device = self._resolve_ultralytics_device()

            stream = model.predict(source=str(video_path), conf=score_thresh, device=device, verbose=False, stream=True)



            class_counts: Counter[str] = Counter()

            frames_processed = 0

            conf_sum = 0.0

            conf_count = 0

            last_progress = 0

            writer = None

            selected_codec = None

            web_playable = False

            target_w = width if width and width > 0 else 640

            target_h = height if height and height > 0 else 480



            if save_annotated:

                if output_video_path is None:

                    output_video_path = video_path.with_name(f"annotated_{video_path.name}")

                output_video_path.parent.mkdir(parents=True, exist_ok=True)

                out_fps = fps if fps and fps > 0 else 25.0

                codec_candidates = [

                    ("avc1", True),

                    ("H264", True),

                    ("X264", True),

                    ("mp4v", False),

                ]

                for codec_name, can_web_play in codec_candidates:

                    fourcc = cv2.VideoWriter_fourcc(*codec_name)

                    trial = cv2.VideoWriter(str(output_video_path), fourcc, out_fps, (target_w, target_h))

                    if trial is not None and trial.isOpened():

                        writer = trial

                        selected_codec = codec_name

                        web_playable = can_web_play

                        break

                    if trial is not None:

                        trial.release()

                if writer is None:

                    raise RuntimeError("Error initializing writer")



            cyclegan_applied = False

            cyclegan_error = None



            try:

                if use_cyclegan:

                    cap = cv2.VideoCapture(str(video_path))

                    if not cap.isOpened():

                        raise RuntimeError(f"Error reading video: {video_path}")

                    try:

                        while True:

                            ok, frame = cap.read()

                            if not ok or frame is None:

                                break

                            frame_start = time.perf_counter()

                            frames_processed += 1



                            enhanced_frame, enhanced_ok, enhance_err = self._apply_cyclegan_to_frame(frame, cv2)

                            if enhanced_ok:

                                cyclegan_applied = True

                            elif cyclegan_error is None and enhance_err:

                                cyclegan_error = enhance_err



                            try:

                                if use_tracking:

                                    outputs = model.track(

                                        source=enhanced_frame,

                                        conf=score_thresh,

                                        device=device,

                                        verbose=False,

                                        persist=True,

                                        tracker="bytetrack.yaml",

                                    )

                                else:

                                    outputs = model.predict(

                                        source=enhanced_frame,

                                        conf=score_thresh,

                                        device=device,

                                        verbose=False,

                                    )

                            except Exception as exc:

                                if use_tracking and tracking_error is None:

                                    tracking_error = f"杩借釜鍣ㄥ垵濮嬪寲澶辫触锛屽凡鍥為��鏅�閫氭��娴? {exc}"

                                outputs = model.predict(

                                    source=enhanced_frame,

                                    conf=score_thresh,

                                    device=device,

                                    verbose=False,

                                )

                            if outputs:

                                output = outputs[0]

                                boxes = output.boxes

                                names = output.names or {}

                                if boxes is not None and boxes.cls is not None:

                                    clses = boxes.cls.cpu().numpy().astype(np.int64)

                                    confs = boxes.conf.cpu().numpy() if boxes.conf is not None else np.array([])

                                    for idx, cls_id in enumerate(clses):

                                        class_name = str(names.get(int(cls_id), f"绫诲埆_{int(cls_id)}"))

                                        class_counts[class_name] += 1

                                        if idx < len(confs):

                                            conf_sum += float(confs[idx])

                                            conf_count += 1



                                if writer is not None:

                                    frame_out = output.plot()

                                    if frame_out is not None:

                                        if frame_out.shape[1] != target_w or frame_out.shape[0] != target_h:

                                            frame_out = cv2.resize(frame_out, (target_w, target_h))

                                        writer.write(frame_out)



                            if progress_callback and total_frames > 0:

                                progress = min(99, int((frames_processed / max(total_frames, 1)) * 100))

                                if progress >= last_progress + 2:

                                    progress_callback(progress)

                                    last_progress = progress



                            if simulate_realtime and realtime_fps > 0:

                                elapsed = time.perf_counter() - frame_start

                                target = 1.0 / max(realtime_fps, 1e-6)

                                if elapsed < target:

                                    time.sleep(target - elapsed)

                    finally:

                        cap.release()

                else:

                    if use_tracking:

                        try:

                            stream = model.track(

                                source=str(video_path),

                                conf=score_thresh,

                                device=device,

                                verbose=False,

                                stream=True,

                                persist=True,

                                tracker="bytetrack.yaml",

                            )

                        except Exception as exc:

                            tracking_error = f"杩借釜鍣ㄥ垵濮嬪寲澶辫触锛屽凡鍥為��鏅�閫氭��娴? {exc}"

                            stream = model.predict(source=str(video_path), conf=score_thresh, device=device, verbose=False, stream=True)

                    else:

                        stream = model.predict(source=str(video_path), conf=score_thresh, device=device, verbose=False, stream=True)



                    for output in stream:

                        frame_start = time.perf_counter()

                        frames_processed += 1



                        boxes = output.boxes

                        names = output.names or {}

                        if boxes is not None and boxes.cls is not None:

                            clses = boxes.cls.cpu().numpy().astype(np.int64)

                            confs = boxes.conf.cpu().numpy() if boxes.conf is not None else np.array([])

                            for idx, cls_id in enumerate(clses):

                                class_name = str(names.get(int(cls_id), f"绫诲埆_{int(cls_id)}"))

                                class_counts[class_name] += 1

                                if idx < len(confs):

                                    conf_sum += float(confs[idx])

                                    conf_count += 1



                        if writer is not None:

                            frame = output.plot()

                            if frame is not None:

                                if frame.shape[1] != target_w or frame.shape[0] != target_h:

                                    frame = cv2.resize(frame, (target_w, target_h))

                                writer.write(frame)



                        if progress_callback and total_frames > 0:

                            progress = min(99, int((frames_processed / max(total_frames, 1)) * 100))

                            if progress >= last_progress + 2:

                                progress_callback(progress)

                                last_progress = progress



                        if simulate_realtime and realtime_fps > 0:

                            elapsed = time.perf_counter() - frame_start

                            target = 1.0 / max(realtime_fps, 1e-6)

                            if elapsed < target:

                                time.sleep(target - elapsed)

            finally:

                if writer is not None:

                    writer.release()



            dominant_type = max(class_counts.items(), key=lambda x: x[1])[0] if class_counts else "none"

            avg_conf = float(conf_sum / conf_count) if conf_count > 0 else 0.0

            if progress_callback:

                progress_callback(100)

            result = {

                "class_counts": dict(class_counts),

                "frames_processed": frames_processed,

                "dominant_type": dominant_type,

                "model_key": key,

                "score_thresh": score_thresh,

                "enhanced_by_cyclegan": use_cyclegan,

                "cyclegan_applied": cyclegan_applied,

                "cyclegan_error": cyclegan_error,

                "tracking_enabled": use_tracking,

                "tracking_backend": ("predict-fallback" if tracking_error else tracking_backend),

                "tracking_error": tracking_error,

                "simulate_realtime": simulate_realtime,

                "realtime_fps": realtime_fps,

                "avg_confidence": round(avg_conf, 4),

                "model_status": "loaded",

                "model_error": None,

                "inference_enabled": self.enable_inference,

            }

            if save_annotated and output_video_path is not None:

                if not web_playable:

                    web_path = output_video_path.with_name(f"{output_video_path.stem}_web.mp4")

                    ok = self._transcode_to_web_mp4(output_video_path, web_path)

                    if not ok:

                        raise RuntimeError("妫�娴嬪悗瑙嗛�戣浆鐮佸け璐ワ紝鏃犳硶鐢熸垚娴忚�堝櫒鍙�鎾�鏀剧殑甯︽�嗚�嗛��")

                    output_video_path = web_path

                    selected_codec = "libx264"

                    web_playable = True

                result["output_video_path"] = str(output_video_path)

                result["output_video_codec"] = selected_codec

                result["output_video_web_playable"] = web_playable

            return result

        except Exception as exc:

            self._model_errors[key] = str(exc)

            summary = self._mock_video_summary(video_path=video_path, model_key=key, score_thresh=score_thresh)

            summary.update(

                {

                    "model_status": "fallback",

                    "model_error": str(exc),

                    "enhanced_by_cyclegan": use_cyclegan,

                    "tracking_enabled": use_tracking,

                    "tracking_backend": "fallback",

                    "tracking_error": tracking_error,

                    "simulate_realtime": simulate_realtime,

                    "realtime_fps": realtime_fps,

                    "inference_enabled": self.enable_inference,

                }

            )

            if progress_callback:

                progress_callback(100)

            return summary



    def start_realtime_session(

        self,

        user_id: int,

        robot_id: int | None,

        source: str,

        score_thresh: float = 0.25,

        model_key: str | None = None,

        use_cyclegan: bool = False,

        use_tracking: bool = False,

        realtime_fps: float = 8.0,

    ) -> dict[str, Any]:

        source = str(source or "").strip()

        if not source:

            raise ValueError("Invalid value")



        selected_model = self._resolve_model(model_key)

        session_id = uuid.uuid4().hex

        now = time.time()

        stop_event = threading.Event()



        session: dict[str, Any] = {

            "id": session_id,

            "user_id": int(user_id),

            "robot_id": int(robot_id) if robot_id is not None else None,

            "source": source,

            "score_thresh": float(score_thresh),

            "model_key": selected_model.get("key", "mock-default"),

            "selected_model": selected_model,

            "use_cyclegan": bool(use_cyclegan),

            "use_tracking": bool(use_tracking),

            "tracking_backend": ("bytetrack" if use_tracking else "disabled"),

            "tracking_error": "",

            "cyclegan_applied": False,

            "cyclegan_error": "",

            "realtime_fps": float(max(1.0, min(30.0, realtime_fps))),

            "status": "running",

            "error_message": "",

            "started_at": now,

            "last_frame_at": None,

            "frames_processed": 0,

            "current_class_counts": {},

            "total_class_counts": {},

            "latest_jpeg": None,

            "latest_raw_frame": None,

            "max_infer_fps": float(max(2.0, min(20.0, realtime_fps))),

            "last_on_demand_infer_at": 0.0,

            "stop_event": stop_event,

            "lock": threading.Lock(),

            "thread": None,

        }



        with self._lock:

            self._model_errors.pop(str(selected_model.get("key", "")), None)

            if "realtime_sessions" not in self.app.extensions:

                self.app.extensions["realtime_sessions"] = {}

            sessions: dict[str, dict[str, Any]] = self.app.extensions["realtime_sessions"]

            sessions[session_id] = session



        t = threading.Thread(target=self._run_realtime_session, args=(session_id,), daemon=True)

        session["thread"] = t

        t.start()

        return self.get_realtime_session_status(session_id=session_id, user_id=user_id)



    def stop_realtime_session(self, session_id: str, user_id: int, is_admin: bool = False) -> dict[str, Any]:

        session = self._get_realtime_session(session_id)

        if session is None:

            raise KeyError("会话不存在")

        if not is_admin and int(session.get("user_id", -1)) != int(user_id):

            raise PermissionError("无权访问该会话")



        stop_event = session.get("stop_event")

        if stop_event is not None:

            stop_event.set()

        with session["lock"]:

            if session.get("status") not in {"failed", "stopped"}:

                session["status"] = "stopped"

        return self._serialize_realtime_session(session)



    def get_realtime_session_status(self, session_id: str, user_id: int, is_admin: bool = False) -> dict[str, Any]:

        session = self._get_realtime_session(session_id)

        if session is None:

            raise KeyError("会话不存在")

        if not is_admin and int(session.get("user_id", -1)) != int(user_id):

            raise PermissionError("无权访问该会话")

        return self._serialize_realtime_session(session)



    def get_realtime_session_frame(self, session_id: str, user_id: int, is_admin: bool = False) -> bytes | None:

        session = self._get_realtime_session(session_id)

        if session is None:

            raise KeyError("会话不存在")

        if not is_admin and int(session.get("user_id", -1)) != int(user_id):

            raise PermissionError("无权访问该会话")



        with session["lock"]:

            payload = session.get("latest_jpeg")

            status = str(session.get("status", ""))

            source = str(session.get("source", ""))



        if payload is None:

            if status == "running" and (source.isdigit() or source.lower().startswith("rtsp://")):

                with session["lock"]:

                    if int(session.get("frames_processed", 0)) == 0:

                        if source.isdigit():

                            session["error_message"] = (

                                f"本地摄像头索引 {source} 当前不可读，请确认未被其他程序占用，并检查系统相机权限。"

                            )

                        else:

                            session["error_message"] = f"RTSP 流正在连接或暂无数据，请检查推流状态: {source}"

        return payload



    def _get_realtime_session(self, session_id: str) -> dict[str, Any] | None:

        with self._lock:

            sessions: dict[str, dict[str, Any]] = self.app.extensions.get("realtime_sessions", {})

            return sessions.get(session_id)



    def _serialize_realtime_session(self, session: dict[str, Any]) -> dict[str, Any]:

        with session["lock"]:

            started_at = float(session.get("started_at") or time.time())

            now = time.time()

            frames_processed = int(session.get("frames_processed") or 0)

            uptime = max(0.0, now - started_at)

            last_frame_at = session.get("last_frame_at")

            no_frame_sec = round(max(0.0, now - float(last_frame_at)), 2) if last_frame_at else None

            return {

                "id": str(session.get("id", "")),

                "status": str(session.get("status", "unknown")),

                "error_message": str(session.get("error_message") or ""),

                "source": str(session.get("source") or ""),

                "model_key": str(session.get("model_key") or ""),

                "score_thresh": float(session.get("score_thresh") or 0.25),

                "realtime_fps": float(session.get("realtime_fps") or 8.0),

                "max_infer_fps": float(session.get("max_infer_fps") or 2.0),

                "use_cyclegan": bool(session.get("use_cyclegan", False)),

                "cyclegan_applied": bool(session.get("cyclegan_applied", False)),

                "cyclegan_error": str(session.get("cyclegan_error") or ""),

                "use_tracking": bool(session.get("use_tracking", False)),

                "tracking_backend": str(session.get("tracking_backend") or "disabled"),

                "tracking_error": str(session.get("tracking_error") or ""),

                "frames_processed": frames_processed,

                "current_class_counts": dict(session.get("current_class_counts") or {}),

                "total_class_counts": dict(session.get("total_class_counts") or {}),

                "started_at": started_at,

                "last_frame_at": last_frame_at,

                "uptime_sec": round(uptime, 2),

                "observed_fps": round((frames_processed / uptime), 2) if uptime > 0 else 0.0,

                "no_frame_sec": no_frame_sec,

                "inference_enabled": self.enable_inference,

            }



    def _grab_local_camera_snapshot(self, camera_index: int) -> np.ndarray | None:

        try:

            import cv2

        except Exception:

            return None



        backend_candidates = [

            getattr(cv2, "CAP_DSHOW", None),

            getattr(cv2, "CAP_MSMF", None),

            None,

        ]

        for backend in backend_candidates:

            cap = cv2.VideoCapture(camera_index, backend) if backend is not None else cv2.VideoCapture(camera_index)

            if cap is None or not cap.isOpened():

                if cap is not None:

                    cap.release()

                continue

            ok, frame = cap.read()

            cap.release()

            if ok and frame is not None:

                return frame

        return None



    def _open_rtsp_capture(self, source: str, cv2: Any):

        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;2000000|timeout;2000000"

        backend_candidates = [

            getattr(cv2, "CAP_FFMPEG", None),

            None,

        ]

        for backend in backend_candidates:

            cap = cv2.VideoCapture(source, backend) if backend is not None else cv2.VideoCapture(source)

            if cap is not None and cap.isOpened():

                try:

                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                except Exception:

                    pass

                return cap

            if cap is not None:

                cap.release()

        return None



    def _capture_rtsp_via_ffmpeg_pipe(self, session: dict[str, Any], source: str) -> bool:

        try:

            import cv2

        except Exception:

            return False



        ffmpeg_exe = self._resolve_ffmpeg_exe()

        if not ffmpeg_exe:

            return False



        cmd = [

            ffmpeg_exe,

            "-hide_banner",

            "-loglevel",

            "error",

            "-rtsp_transport",

            "tcp",

            "-fflags",

            "nobuffer",

            "-flags",

            "low_delay",

            "-i",

            source,

            "-an",

            "-vf",

            "fps=20",

            "-f",

            "image2pipe",

            "-vcodec",

            "mjpeg",

            "-q:v",

            "5",

            "-",

        ]



        proc = None

        try:

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

        except Exception:

            return False



        if proc.stdout is None:

            try:

                proc.terminate()

            except Exception:

                pass

            return False



        got_frame = False

        buf = bytearray()

        try:

            while not session["stop_event"].is_set():

                chunk = proc.stdout.read(4096)

                if not chunk:

                    if proc.poll() is not None:

                        break

                    continue

                buf.extend(chunk)



                while True:

                    start = buf.find(b"\xff\xd8")

                    if start < 0:

                        if len(buf) > 1024 * 1024:

                            del buf[:-1024]

                        break

                    end = buf.find(b"\xff\xd9", start + 2)

                    if end < 0:

                        if start > 0:

                            del buf[:start]

                        break



                    jpg = bytes(buf[start : end + 2])

                    del buf[: end + 2]

                    arr = np.frombuffer(jpg, dtype=np.uint8)

                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

                    if frame is None:

                        continue



                    got_frame = True

                    with session["lock"]:

                        session["latest_raw_frame"] = frame

                        session["last_frame_at"] = time.time()

                        if session.get("error_message"):

                            session["error_message"] = ""

        finally:

            try:

                proc.terminate()

            except Exception:

                pass

            try:

                proc.wait(timeout=1.0)

            except Exception:

                try:

                    proc.kill()

                except Exception:

                    pass



        return got_frame



    def _run_realtime_session(self, session_id: str) -> None:

        session = self._get_realtime_session(session_id)

        if session is None:

            return



        with session["lock"]:

            session["status"] = "running"



        try:

            import cv2

        except Exception as exc:

            with session["lock"]:

                session["status"] = "failed"

                session["error_message"] = f"实时推理依赖加载失败: {exc}"

            return



        cap = None

        try:

            source = str(session.get("source", "")).strip()

            source_for_cv: Any = source

            is_rtsp_source = source.lower().startswith("rtsp://")

            is_local_camera_source = source.isdigit()

            rtsp_candidates: list[str] = [source] if is_rtsp_source else []

            if is_rtsp_source and "/live/cam01" in source.lower():

                rtsp_candidates.append(source.replace("/live/cam01", "/live/cam02"))

                rtsp_candidates.append(source.replace("/live/cam01", "/live/cam03"))

            if source.isdigit():

                source_for_cv = int(source)



            # RTSP sources are more stable over TCP in many LAN/NAT setups.

            if is_rtsp_source:

                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;2000000|timeout;2000000"



            if not is_rtsp_source and not is_local_camera_source:

                if isinstance(source_for_cv, int):

                    backend_candidates = [

                        getattr(cv2, "CAP_DSHOW", None),

                        getattr(cv2, "CAP_MSMF", None),

                        None,

                    ]

                    for backend in backend_candidates:

                        trial = cv2.VideoCapture(source_for_cv, backend) if backend is not None else cv2.VideoCapture(source_for_cv)

                        if trial is not None and trial.isOpened():

                            cap = trial

                            break

                        if trial is not None:

                            trial.release()

                else:

                    cap = cv2.VideoCapture(source_for_cv)

            if (not is_rtsp_source and not is_local_camera_source) and (cap is None or not cap.isOpened()):

                with session["lock"]:

                    session["status"] = "failed"

                    session["error_message"] = (

                        f"无法打开监控源: {source}。"
                        "若使用 0/1 等本地摄像头索引，请确认后端机器有可用摄像头、"
                        "未被其他程序占用，并已授予系统相机权限。"

                    )

                return



            selected_model = session.get("selected_model") or {}

            model_key = str(selected_model.get("key", "mock-default"))

            model_engine = str(selected_model.get("engine", "mock"))

            model_path = self.model_dir / model_key

            model = None

            model_init_attempted = False

            device: Any = "cpu"

            need_yolo_model = (

                model_key != "mock-default"

                and self.enable_inference

                and model_engine == "yolo"

                and model_path.exists()

            )



            if is_local_camera_source:

                opened_cap = None

                backend_candidates = [

                    getattr(cv2, "CAP_DSHOW", None),

                    getattr(cv2, "CAP_MSMF", None),

                    None,

                ]

                for backend in backend_candidates:

                    trial = cv2.VideoCapture(int(source_for_cv), backend) if backend is not None else cv2.VideoCapture(int(source_for_cv))

                    if trial is not None and trial.isOpened():

                        opened_cap = trial

                        break

                    if trial is not None:

                        trial.release()



                if opened_cap is None:

                    with session["lock"]:

                        session["status"] = "failed"

                        session["error_message"] = (

                            f"无法打开本地摄像头索引 {source}。请确认摄像头存在、未被占用，且系统已授予相机权限。"

                        )

                    return



                try:

                    opened_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                except Exception:

                    pass



                def _local_reader():

                    try:

                        while not session["stop_event"].is_set():

                            ok, raw = opened_cap.read()

                            if not ok or raw is None:

                                time.sleep(0.01)

                                continue

                            with session["lock"]:

                                session["latest_raw_frame"] = raw

                                if session.get("error_message"):

                                    session["error_message"] = ""

                    finally:

                        opened_cap.release()

                threading.Thread(target=_local_reader, daemon=True).start()



            elif is_rtsp_source:

                selected_rtsp_source = source

                cap_rtsp = None

                for cand in rtsp_candidates:

                    trial = self._open_rtsp_capture(cand, cv2)

                    if trial is not None:

                        cap_rtsp = trial

                        selected_rtsp_source = cand

                        break



                if selected_rtsp_source != source:

                    with session["lock"]:

                        session["source"] = selected_rtsp_source

                        session["error_message"] = f"已自动切换到可读 RTSP 路径: {selected_rtsp_source}"



                if cap_rtsp is None:

                    def _ffmpeg_pipe_runner():

                        for cand in rtsp_candidates:

                            if self._capture_rtsp_via_ffmpeg_pipe(session, cand):

                                if cand != source:

                                    with session["lock"]:

                                        session["source"] = cand

                                        session["error_message"] = f"已自动切换到可读 RTSP 路径: {cand}"

                                return

                        # 鏈�鍚庡皾璇曚竴娆″師濮?source锛屽�傛灉浠嶇劧澶辫触鍒欑粰鍑烘洿鍏蜂綋鐨勮瘖鏂�寤鸿��

                        if not self._capture_rtsp_via_ffmpeg_pipe(session, source):

                            ffexe = self._resolve_ffmpeg_exe()

                            with session["lock"]:

                                session["status"] = "failed"

                                if not ffexe:

                                    session["error_message"] = (

                                        f"无法打开 RTSP: {source}。检测到系统未找到可执行文件 ffmpeg。"
                                        "请在后端机器安装 ffmpeg 并确保在 PATH 中，或安装 Python 包 imageio-ffmpeg。"

                                    )

                                else:

                                    session["error_message"] = f"无法通过 ffmpeg 打开 RTSP: {source}（ffmpeg: {ffexe}）"

                    threading.Thread(target=_ffmpeg_pipe_runner, daemon=True).start()

                else:

                    def _rtsp_reader():

                        nonlocal cap_rtsp

                        nonlocal selected_rtsp_source

                        try:

                            consecutive_failures = 0

                            fallback_attempted = False

                            while not session["stop_event"].is_set():

                                ok, raw = cap_rtsp.read()

                                if not ok or raw is None:

                                    consecutive_failures += 1

                                    if consecutive_failures >= 300:

                                        if cap_rtsp:

                                            cap_rtsp.release()

                                        cap_rtsp = self._open_rtsp_capture(selected_rtsp_source, cv2)

                                        if cap_rtsp is None:

                                            with session["lock"]:

                                                session["error_message"] = f"RTSP 重连失败，尝试 ffmpeg 管道: {selected_rtsp_source}"

                                            if not fallback_attempted:

                                                fallback_attempted = True

                                                pipe_ok = False

                                                for cand in rtsp_candidates:

                                                    if self._capture_rtsp_via_ffmpeg_pipe(session, cand):

                                                        pipe_ok = True

                                                        selected_rtsp_source = cand

                                                        if cand != source:

                                                            with session["lock"]:

                                                                session["source"] = cand

                                                                session["error_message"] = f"已自动切换到可读 RTSP 路径: {cand}"

                                                        break

                                                if pipe_ok:

                                                    return

                                            consecutive_failures = 0

                                            time.sleep(0.2)

                                            continue



                                        # OpenCV can open the stream but still can't decode frames reliably.

                                        # Switch to ffmpeg pipe once to improve compatibility with certain encoders.

                                        if not fallback_attempted:

                                            # 褰?OpenCV 鑳借繛鎺ヤ絾涓嶈兘瑙ｇ爜甯ф椂锛屾彁绀哄彲鑳戒负缂栫爜/瑙ｇ爜鍏煎�规�ч棶棰?

                                            with session["lock"]:

                                                session["error_message"] = (

                                                    f"RTSP 可连接但无法解码视频帧，正在尝试 ffmpeg 管道以兼容更多编码器: {selected_rtsp_source}"

                                                )

                                            fallback_attempted = True

                                            pipe_ok = False

                                            for cand in rtsp_candidates:

                                                if self._capture_rtsp_via_ffmpeg_pipe(session, cand):

                                                    pipe_ok = True

                                                    selected_rtsp_source = cand

                                                    if cand != source:

                                                        with session["lock"]:

                                                            session["source"] = cand

                                                            session["error_message"] = f"已自动切换到可读 RTSP 路径: {cand}"

                                                    break

                                            if pipe_ok:

                                                return



                                        consecutive_failures = 0

                                    time.sleep(0.01)

                                    continue

                                consecutive_failures = 0

                                with session["lock"]:

                                    session["latest_raw_frame"] = raw

                                    if session.get("error_message"):

                                        session["error_message"] = ""

                        finally:

                            if cap_rtsp:

                                cap_rtsp.release()

                    threading.Thread(target=_rtsp_reader, daemon=True).start()



            target_interval = 1.0 / max(float(session.get("realtime_fps") or 8.0), 1.0)

            consecutive_failures = 0



            while not session["stop_event"].is_set():

                tick = time.perf_counter()

                

                frame = None

                with session["lock"]:

                    cached_raw = session.get("latest_raw_frame")

                if cached_raw is not None:

                    frame = cached_raw.copy()

                elif (not is_rtsp_source and not is_local_camera_source):

                    assert cap is not None

                    ok, frame = cap.read()

                    if not ok or frame is None:

                        frame = None



                if frame is None:

                    consecutive_failures += 1

                    if consecutive_failures >= 200:

                        with session["lock"]:

                            session["status"] = "failed"

                            session["error_message"] = f"读取监控流失败: {source}，连接已中断或不可用。"

                        break

                    time.sleep(0.05)

                    continue

                consecutive_failures = 0



                current_counts: Counter[str] = Counter()



                # Always publish frames first; don't block on heavyweight model initialization.

                if model is None:

                    if need_yolo_model and not model_init_attempted:

                        model_init_attempted = True

                        def _load_model():

                            try:

                                from ultralytics import YOLO



                                device = self._resolve_ultralytics_device()

                                m = self._model_cache.get(model_path.name)

                                if m is None:

                                    m = YOLO(str(model_path))

                                    # Use lock to safely update the shared model or just thread-safe dict

                                    with self._lock:

                                        self._model_cache[model_path.name] = m

                            except Exception as exc:

                                with session["lock"]:

                                    session["error_message"] = f"模型加载失败，已降级为仅视频监控模式: {exc}"

                        threading.Thread(target=_load_model, daemon=True).start()

                    

                    # Update local model reference if loaded in background

                    if need_yolo_model and model_init_attempted:

                        model = self._model_cache.get(model_path.name)

                    

                    if need_yolo_model and model is None:

                        cv2.putText(

                            frame,

                            "Model loading...",

                            (12, 30),

                            cv2.FONT_HERSHEY_SIMPLEX,

                            0.8,

                            (0, 255, 255),

                            2,

                        )

                if model is not None:

                    infer_frame = frame

                    if bool(session.get("use_cyclegan", False)):

                        infer_frame, enhanced_ok, enhance_err = self._apply_cyclegan_to_frame(frame, cv2)

                        with session["lock"]:

                            if enhanced_ok:

                                session["cyclegan_applied"] = True

                                session["cyclegan_error"] = ""

                            elif enhance_err:

                                session["cyclegan_error"] = enhance_err

                    use_tracking = bool(session.get("use_tracking", False))

                    try:

                        if use_tracking:

                            outputs = model.track(

                                source=infer_frame,

                                conf=float(session.get("score_thresh", 0.25)),

                                verbose=False,

                                device=device,

                                persist=True,

                                tracker="bytetrack.yaml",

                            )

                        else:

                            outputs = model.predict(

                                source=infer_frame,

                                conf=float(session.get("score_thresh", 0.25)),

                                verbose=False,

                                device=device,

                            )

                    except Exception as exc:

                        with session["lock"]:

                            if use_tracking and not session.get("tracking_error"):

                                session["tracking_error"] = f"跟踪器不可用，已回退普通检测: {exc}"

                                session["tracking_backend"] = "predict-fallback"

                        outputs = model.predict(

                            source=infer_frame,

                            conf=float(session.get("score_thresh", 0.25)),

                            verbose=False,

                            device=device,

                        )

                    if outputs:

                        output = outputs[0]

                        boxes = output.boxes

                        names = output.names or {}

                        if boxes is not None and boxes.cls is not None:

                            clses = boxes.cls.cpu().numpy().astype(np.int64)

                            for cls_id in clses:

                                class_name = str(names.get(int(cls_id), f"绫诲埆_{int(cls_id)}"))

                                current_counts[class_name] += 1

                        frame = output.plot()

                elif not need_yolo_model:

                    cv2.putText(

                        frame,

                        "Mock Realtime Mode",

                        (12, 30),

                        cv2.FONT_HERSHEY_SIMPLEX,

                        0.8,

                        (0, 255, 255),

                        2,

                    )



                ok_jpg, enc = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

                if not ok_jpg:

                    continue



                with session["lock"]:

                    session["latest_jpeg"] = bytes(enc.tobytes())

                    session["frames_processed"] = int(session.get("frames_processed", 0)) + 1

                    session["last_frame_at"] = time.time()

                    session["current_class_counts"] = dict(current_counts)

                    total_counter = Counter(session.get("total_class_counts") or {})

                    total_counter.update(current_counts)

                    session["total_class_counts"] = dict(total_counter)



                elapsed = time.perf_counter() - tick

                if elapsed < target_interval:

                    time.sleep(target_interval - elapsed)

        except Exception as exc:

            with session["lock"]:

                session["status"] = "failed"

                session["error_message"] = f"实时会话异常: {exc}"

        finally:

            if cap is not None:

                cap.release()

            with session["lock"]:

                if session.get("status") not in {"failed", "stopped"}:

                    session["status"] = "stopped"



    def _resolve_model_dir(self) -> Path:

        base_dir = Path(self.app.config.get("BASE_DIR")).resolve()

        repo_root = Path(self.app.config.get("REPO_ROOT")).resolve()

        candidates = [

            base_dir / "app" / "models",

            base_dir / "models",

            repo_root / "models",

            base_dir.parent.parent / "models",

        ]

        for path in candidates:

            if path.exists():

                return path.resolve()

        return (base_dir / "app" / "models").resolve()



    def _resolve_cyclegan_checkpoint_path(self) -> Path:

        base_dir = Path(self.app.config.get("BASE_DIR")).resolve()

        configured = str(self.app.config.get("MODEL_CYCLEGAN_CKPT") or "").strip()

        if configured:

            candidate = Path(configured)

            if not candidate.is_absolute():

                search_candidates = [

                    (base_dir / configured).resolve(),

                    (base_dir / "app" / configured).resolve(),

                ]

                for path in search_candidates:

                    if path.exists():

                        return path

                candidate = search_candidates[0]

            return candidate

        fallback_candidates = [

            (base_dir / "app" / "models" / "ami_cyclegan.pth").resolve(),

            (base_dir / "models" / "ami_cyclegan.pth").resolve(),

        ]

        for path in fallback_candidates:

            if path.exists():

                return path

        return fallback_candidates[0]



    def _resolve_torch_device(self, torch_module):

        device_opt = str(self.app.config.get("MODEL_DEVICE", "auto")).lower()

        if device_opt == "auto":

            return torch_module.device("cuda" if torch_module.cuda.is_available() else "cpu")

        if device_opt.startswith("cuda") and not torch_module.cuda.is_available():

            return torch_module.device("cpu")

        return torch_module.device(device_opt)



    def _load_cyclegan_runtime(self) -> dict[str, Any]:

        ckpt_path = self._cyclegan_ckpt_path

        if not ckpt_path.exists():

            raise FileNotFoundError(f"CycleGAN 鏉冮噸涓嶅瓨鍦? {ckpt_path}")



        stat = ckpt_path.stat()

        ckpt_signature = (int(stat.st_mtime_ns), int(stat.st_size))

        if self._cyclegan_runtime is not None and self._cyclegan_ckpt_signature == ckpt_signature:

            return self._cyclegan_runtime



        import torch



        repo_root = Path(self.app.config.get("REPO_ROOT")).resolve()

        networks_path = repo_root / "enhancement(CycleGAN)" / "models" / "networks.py"

        if not networks_path.exists():

            raise FileNotFoundError(f"CycleGAN 缃戠粶瀹氫箟涓嶅瓨鍦? {networks_path}")



        spec = importlib.util.spec_from_file_location("uw_cyclegan_networks", str(networks_path))

        if spec is None or spec.loader is None:

            raise RuntimeError("鏃犳硶鍔犺浇 CycleGAN 缃戠粶瀹氫箟妯″潡")

        module = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(module)



        build_generator = getattr(module, "build_generator", None)

        if build_generator is None:

            raise RuntimeError("CycleGAN 缃戠粶妯″潡缂哄皯 build_generator")



        device = self._resolve_torch_device(torch)

        checkpoint = torch.load(ckpt_path, map_location=device)

        model_cfg = dict(checkpoint.get("model_cfg", {}))

        arch = str(model_cfg.get("generator_arch", "ami"))

        generator_kwargs = dict(model_cfg.get("generator_kwargs", {}))

        epoch = checkpoint.get("epoch")



        generator = build_generator(arch=arch, generator_kwargs=generator_kwargs).to(device)

        state_dict = checkpoint.get("net_g_a2b")

        if state_dict is None:

            raise RuntimeError(f"CycleGAN 妫�鏌ョ偣缂哄皯 net_g_a2b: {ckpt_path}")

        generator.load_state_dict(state_dict, strict=True)

        generator.eval()



        self._cyclegan_runtime = {

            "torch": torch,

            "generator": generator,

            "device": device,

            "arch": arch,

            "epoch": epoch,

            "checkpoint": str(ckpt_path),

        }

        self._cyclegan_ckpt_signature = ckpt_signature

        self._cyclegan_error = None

        return self._cyclegan_runtime



    def _apply_cyclegan_to_frame(self, frame_bgr: np.ndarray, cv2_module) -> tuple[np.ndarray, bool, str | None]:

        if not self.enable_inference:

            return frame_bgr, False, "褰撳墠涓烘ā鎷熸ā寮忥紝鏈�鍚�鐢ㄧ湡瀹炴帹鐞?"



        try:

            runtime = self._load_cyclegan_runtime()

            torch = runtime["torch"]

            generator = runtime["generator"]

            device = runtime["device"]



            frame_rgb = cv2_module.cvtColor(frame_bgr, cv2_module.COLOR_BGR2RGB)

            image = frame_rgb.astype(np.float32) / 255.0

            tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)

            tensor = (tensor * 2.0 - 1.0).to(device)



            # 鍔ㄦ�?Padding锛氬洜涓?AMI-CycleGAN 鐢熸垚鍣ㄤ腑鍖呭惈鐢变簬璺ㄥ眰鎷兼帴 (UNet/ASFF) 鐨勭綉缁滅粨鏋?

            # 缁忚繃浜?3 娆?2 鍊嶄笅閲囨牱 (2^3 = 8 鍊?銆傛墍浠ュ�藉拰楂樺繀椤绘槸鍙�浠ヨ�� 8 鏁撮櫎鐨勶紝鍚﹀垯璺宠穬杩炴帴鏃朵細鍑虹幇灏哄�镐笉鍖归厤闂�棰?

            import torch.nn.functional as F

            _, _, orig_h, orig_w = tensor.shape

            pad_h = (8 - orig_h % 8) % 8

            pad_w = (8 - orig_w % 8) % 8

            

            if pad_h > 0 or pad_w > 0:

                tensor = F.pad(tensor, (0, pad_w, 0, pad_h), mode='reflect')



            with torch.no_grad():

                pred = generator(tensor)

                pred = ((pred + 1.0) * 0.5).clamp(0.0, 1.0)



            # 瑁佸垏鍥炲師濮嬪昂瀵?

            if pad_h > 0 or pad_w > 0:

                pred = pred[:, :, :orig_h, :orig_w]



            out_rgb = pred.squeeze(0).permute(1, 2, 0).cpu().numpy()

            out_rgb = np.clip(out_rgb * 255.0, 0.0, 255.0).astype(np.uint8)

            out_bgr = cv2_module.cvtColor(out_rgb, cv2_module.COLOR_RGB2BGR)

            return out_bgr, True, None

        except Exception as exc:

            self._cyclegan_error = str(exc)

            return frame_bgr, False, self._cyclegan_error



    def _enhance_image_with_cyclegan(self, image_path: Path) -> tuple[Path | None, str | None]:

        try:

            import cv2

        except Exception as exc:

            return None, f"OpenCV 涓嶅彲鐢�锛屾棤娉曟墽琛屽浘鐗囧�炲己: {exc}"



        frame = cv2.imread(str(image_path))

        if frame is None:

            return None, f"鏃犳硶璇诲彇鍥剧墖: {image_path}"



        enhanced_frame, ok, err = self._apply_cyclegan_to_frame(frame, cv2)

        if not ok:

            return None, err



        enhanced_dir = image_path.parent / "enhanced"

        enhanced_dir.mkdir(parents=True, exist_ok=True)

        enhanced_path = enhanced_dir / f"{image_path.stem}_cyclegan.jpg"

        success = cv2.imwrite(str(enhanced_path), enhanced_frame)

        if not success:

            return None, f"澧炲己缁撴灉鍐欏叆澶辫触: {enhanced_path}"

        return enhanced_path, None



    def _resolve_model(self, model_key: str | None) -> dict[str, Any]:

        from app.models.entities import SystemConfig



        models = self.list_models()

        if model_key:

            for item in models:

                if item["key"] == model_key:

                    return item

        else:

            default_config = SystemConfig.query.get("default_model_key")

            if default_config and default_config.value:

                for item in models:

                    if item["key"] == default_config.value:

                        return item

        return models[0]



    def _predict(

        self,

        image_path: Path,

        score_thresh: float,

        selected_model: dict[str, Any],

    ) -> tuple[list[dict[str, Any]], str, str | None]:

        key = str(selected_model.get("key", "mock-default"))

        engine = str(selected_model.get("engine", "mock"))



        if key == "mock-default":

            return self._apply_thresh(self._mock_predict(image_path, key), score_thresh), "mock_only", None



        model_path = self.model_dir / key

        if not model_path.exists():

            return (

                self._apply_thresh(self._mock_predict(image_path, key), score_thresh),

                "fallback",

                f"妯″瀷鏂囦欢涓嶅瓨锟? {model_path}",

            )



        if not self.enable_inference:

            return self._apply_thresh(self._mock_predict(image_path, key), score_thresh), "mock_only", None



        try:

            if engine == "yolo":

                results = self._predict_yolo(model_path=model_path, image_path=image_path, score_thresh=score_thresh)

                return results, "loaded", None

            if engine == "student":

                results = self._predict_student(model_path=model_path, image_path=image_path, score_thresh=score_thresh)

                return results, "loaded", None

            if engine == "fasterrcnn":

                results = self._predict_fasterrcnn(model_path=model_path, image_path=image_path, score_thresh=score_thresh)

                return results, "loaded", None



            return (

                self._apply_thresh(self._mock_predict(image_path, key), score_thresh),

                "fallback",

                f"鏆備笉鏀�鎸佺殑妯″瀷绫伙�? {engine}",

            )

        except Exception as exc:

            self._model_errors[key] = str(exc)

            return self._apply_thresh(self._mock_predict(image_path, key), score_thresh), "fallback", str(exc)



    @staticmethod

    def _apply_thresh(detections: list[dict[str, Any]], score_thresh: float) -> list[dict[str, Any]]:

        return [d for d in detections if float(d.get("score", 0.0)) >= score_thresh]



    def _predict_yolo(self, model_path: Path, image_path: Path, score_thresh: float) -> list[dict[str, Any]]:

        from ultralytics import YOLO



        cache_key = model_path.name

        model = self._model_cache.get(cache_key)

        if model is None:

            model = YOLO(str(model_path))

            self._model_cache[cache_key] = model



        device = self._resolve_ultralytics_device()

        outputs = model.predict(source=str(image_path), conf=score_thresh, verbose=False, device=device)

        if not outputs:

            return []



        output = outputs[0]

        boxes = output.boxes

        names = output.names or {}



        results: list[dict[str, Any]] = []

        if boxes is None:

            return results



        xyxy = boxes.xyxy.cpu().numpy()

        clses = boxes.cls.cpu().numpy().astype(np.int64)

        confs = boxes.conf.cpu().numpy()



        for box, cls_id, conf in zip(xyxy, clses, confs):

            class_name = str(names.get(int(cls_id), f"绫诲埆_{int(cls_id)}"))

            results.append(

                {

                    "class_id": int(cls_id),

                    "class_name": class_name,

                    "score": float(conf),

                    "bbox": [float(v) for v in box.tolist()],

                    "is_trash": self._is_trash_class(class_name),

                }

            )

        return results



    def _predict_student(self, model_path: Path, image_path: Path, score_thresh: float) -> list[dict[str, Any]]:

        runtime = self._get_student_runtime()

        cache_key = model_path.name

        bundle = self._model_cache.get(cache_key)

        if bundle is None:

            bundle = self._load_student_model(model_path=model_path, runtime=runtime)

            self._model_cache[cache_key] = bundle



        model = bundle["model"]

        device = bundle["device"]

        torch = bundle["torch"]

        tf = bundle["tf"]



        image = Image.open(image_path).convert("RGB")

        tensor = tf.to_tensor(image).to(device)



        with torch.no_grad():

            output = model([tensor])[0]



        boxes = output["boxes"].detach().cpu().numpy()

        labels = output["labels"].detach().cpu().numpy().astype(np.int64)

        scores = output["scores"].detach().cpu().numpy()



        results: list[dict[str, Any]] = []

        for box, label, score in zip(boxes, labels, scores):

            if float(score) < score_thresh:

                continue

            class_name = self.LABEL_MAP.get(int(label), f"绫诲埆_{int(label)}")

            results.append(

                {

                    "class_id": int(label),

                    "class_name": class_name,

                    "score": float(score),

                    "bbox": [float(v) for v in box.tolist()],

                    "is_trash": int(label) in self.TRASH_LABELS,

                }

            )

        return results



    def _predict_fasterrcnn(self, model_path: Path, image_path: Path, score_thresh: float) -> list[dict[str, Any]]:

        bundle = self._model_cache.get(model_path.name)

        if bundle is None:

            bundle = self._load_fasterrcnn_model(model_path)

            self._model_cache[model_path.name] = bundle



        model = bundle["model"]

        device = bundle["device"]

        torch = bundle["torch"]

        tf = bundle["tf"]



        image = Image.open(image_path).convert("RGB")

        tensor = tf.to_tensor(image).to(device)



        with torch.no_grad():

            output = model([tensor])[0]



        boxes = output["boxes"].detach().cpu().numpy()

        labels = output["labels"].detach().cpu().numpy().astype(np.int64)

        scores = output["scores"].detach().cpu().numpy()



        results: list[dict[str, Any]] = []

        for box, label, score in zip(boxes, labels, scores):

            if float(score) < score_thresh:

                continue

            class_name = self.LABEL_MAP.get(int(label), f"绫诲埆_{int(label)}")

            results.append(

                {

                    "class_id": int(label),

                    "class_name": class_name,

                    "score": float(score),

                    "bbox": [float(v) for v in box.tolist()],

                    "is_trash": int(label) in self.TRASH_LABELS,

                }

            )

        return results



    @staticmethod

    def _is_trash_class(class_name: str) -> bool:

        name = class_name.lower()

        keywords = ["trash", "garbage", "debris", "鍨冨溇"]

        return any(k in name for k in keywords)



    @staticmethod

    def _seed_name(path: Path) -> str:

        # Uploaded files are saved as "<timestamp>_<original>", normalize to original for stable mock behavior.

        name = path.name

        if "_" in name:

            prefix, rest = name.split("_", 1)

            if prefix.isdigit() and rest:

                return rest

        return name



    def _mock_predict(self, image_path: Path, model_key: str = "") -> list[dict[str, Any]]:

        seed = sum(ord(ch) for ch in self._seed_name(image_path)) + sum(ord(ch) for ch in model_key)

        random.seed(seed)

        n = random.randint(1, 3)

        detections: list[dict[str, Any]] = []

        for _ in range(n):

            label = random.choice([1, 2, 3])

            x1 = random.uniform(0.0, 300.0)

            y1 = random.uniform(0.0, 200.0)

            x2 = x1 + random.uniform(20.0, 160.0)

            y2 = y1 + random.uniform(20.0, 160.0)

            detections.append(

                {

                    "class_id": label,

                    "class_name": self.LABEL_MAP[label],

                    "score": round(random.uniform(0.35, 0.95), 4),

                    "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],

                    "is_trash": label in self.TRASH_LABELS,

                }

            )

        return detections



    def _mock_video_summary(self, video_path: Path, model_key: str, score_thresh: float) -> dict[str, Any]:

        seed = sum(ord(ch) for ch in self._seed_name(video_path)) + sum(ord(ch) for ch in model_key)

        rng = random.Random(seed)

        class_counts = {

            "trash": rng.randint(3, 18),

            "bio": rng.randint(1, 10),

            "rov": rng.randint(0, 4),

        }

        dominant = max(class_counts.items(), key=lambda x: x[1])[0]

        return {

            "class_counts": class_counts,

            "frames_processed": rng.randint(120, 480),

            "dominant_type": dominant,

            "model_key": model_key,

            "score_thresh": score_thresh,

            "avg_confidence": round(max(0.45, min(0.95, score_thresh + 0.3)), 4),

        }



    @staticmethod

    def _resolve_ffmpeg_exe() -> str | None:

        exe = shutil.which("ffmpeg")

        if exe:

            return exe

        try:

            import imageio_ffmpeg



            return imageio_ffmpeg.get_ffmpeg_exe()

        except Exception:

            return None



    def _build_web_preview_video(self, src_path: Path) -> tuple[Path, bool]:
        """Provide a reusable browser preview, falling back to the annotated source."""
        web_path = src_path.with_name(f"{src_path.stem}_web.mp4")
        if (web_path.is_file() and web_path.stat().st_size > 0
                and web_path.stat().st_mtime >= src_path.stat().st_mtime):
            return web_path, True
        if self._transcode_to_web_mp4(src_path, web_path):
            return web_path, True
        return src_path, False

    def _transcode_to_web_mp4(self, src_path: Path, dst_path: Path) -> bool:

        ffmpeg_exe = self._resolve_ffmpeg_exe()

        if not ffmpeg_exe:

            return False

        dst_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [

            ffmpeg_exe,

            "-y",

            "-i",

            str(src_path),

            "-c:v",

            "libx264",

            "-pix_fmt",

            "yuv420p",

            "-movflags",

            "+faststart",

            "-an",

            str(dst_path),

        ]

        try:

            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)

            return proc.returncode == 0 and dst_path.exists() and dst_path.stat().st_size > 0

        except Exception:

            return False



    def _grab_rtsp_snapshot_ffmpeg(self, source: str, timeout_sec: float = 6.0):

        ffmpeg_exe = self._resolve_ffmpeg_exe()

        if not ffmpeg_exe:

            return None

        cmd = [

            ffmpeg_exe,

            "-hide_banner",

            "-loglevel",

            "error",

            "-rtsp_transport",

            "tcp",

            "-i",

            source,

            "-frames:v",

            "1",

            "-f",

            "image2pipe",

            "-vcodec",

            "mjpeg",

            "-",

        ]

        try:

            proc = subprocess.run(cmd, capture_output=True, check=False, timeout=timeout_sec)

            if proc.returncode != 0 or not proc.stdout:

                return None

            import cv2



            arr = np.frombuffer(proc.stdout, dtype=np.uint8)

            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            return frame

        except Exception:

            return None



    @staticmethod

    def _encode_image_data_url(image_path: Path) -> str:

        image = Image.open(image_path).convert("RGB")

        buf = io.BytesIO()

        image.save(buf, format="JPEG", quality=88)

        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")



    def _render_annotated_image(self, image_path: Path, detections: list[dict[str, Any]], is_enhanced: bool = False) -> str:

        image = Image.open(image_path).convert("RGB")

        draw = ImageDraw.Draw(image)



        for det in detections:

            bbox = det.get("bbox") or []

            if len(bbox) != 4:

                continue

            x1, y1, x2, y2 = [float(v) for v in bbox]

            cls = str(det.get("class_name", "鏈�鐭�"))

            score = float(det.get("score", 0.0))

            is_trash = bool(det.get("is_trash", False))

            color = (230, 57, 70) if is_trash else (41, 128, 185)

            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

            label = f"{cls} {score:.2f}"

            ty = max(0, y1 - 18)

            draw.rectangle([x1, ty, min(x2, x1 + 180), ty + 18], fill=color)

            draw.text((x1 + 4, ty + 2), label, fill=(255, 255, 255))



        buf = io.BytesIO()

        image.save(buf, format="JPEG", quality=88)

        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")



    @staticmethod

    def _infer_engine(path: Path) -> str:

        suffix = path.suffix.lower()

        stem = path.stem.lower()

        if suffix == ".pt":

            return "yolo"

        if suffix == ".pth" and "student" in stem:

            return "student"

        if suffix == ".pth" and ("faster" in stem or "rcnn" in stem):

            return "fasterrcnn"

        if suffix == ".onnx":

            return "onnx"

        return "unknown"



    def _get_student_runtime(self) -> dict[str, Any]:

        if self._student_runtime is not None:

            return self._student_runtime



        import torch

        import yaml

        from torchvision.transforms import functional as TF



        repo_root = Path(self.app.config["REPO_ROOT"]).resolve()

        distill_root = repo_root / "distillation"



        if str(repo_root) not in sys.path:

            sys.path.insert(0, str(repo_root))

        if str(distill_root) not in sys.path:

            sys.path.insert(0, str(distill_root))



        from distillation.models.student_mbv3_small_detector import build_student_detector



        self._student_runtime = {

            "torch": torch,

            "yaml": yaml,

            "tf": TF,

            "build_student_detector": build_student_detector,

            "distill_root": distill_root,

        }

        return self._student_runtime



    def _load_student_model(self, model_path: Path, runtime: dict[str, Any]) -> dict[str, Any]:

        torch = runtime["torch"]

        yaml = runtime["yaml"]

        tf = runtime["tf"]

        build_student_detector = runtime["build_student_detector"]

        distill_root: Path = runtime["distill_root"]



        cfg_path = distill_root / "configs" / "distill_config_rxiaotian_refactor.yaml"

        num_classes = 4

        student_variant = "ssdlite_mbv3_large"

        if cfg_path.exists():

            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

            num_classes = int(cfg.get("num_classes", 4))

            student_variant = str((cfg.get("student") or {}).get("variant", "ssdlite_mbv3_large"))



        device_opt = str(self.app.config.get("MODEL_DEVICE", "auto")).lower()

        if device_opt == "auto":

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        else:

            device = torch.device(device_opt)



        model = build_student_detector(num_classes=num_classes, variant=student_variant).to(device)

        payload = torch.load(model_path, map_location=device)

        state = payload.get("student_state") if isinstance(payload, dict) else None

        if state is None and isinstance(payload, dict):

            state = payload.get("state_dict")

        if state is None and isinstance(payload, dict):

            state = payload

        if state is None and hasattr(payload, "keys"):

            state = payload

        if state is None:

            raise RuntimeError("Invalid checkpoint: missing student_state")



        try:

            model.load_state_dict(state, strict=True)

        except RuntimeError:

            with torch.no_grad():

                if hasattr(model, "backbone"):

                    _ = model.backbone(torch.zeros((1, 3, 384, 384), device=device))

            model.load_state_dict(state, strict=True)



        model.eval()

        return {"model": model, "device": device, "torch": torch, "tf": tf}



    def _resolve_ultralytics_device(self):

        import torch



        device_opt = str(self.app.config.get("MODEL_DEVICE", "auto")).lower()

        if device_opt == "auto":

            return 0 if torch.cuda.is_available() else "cpu"

        if device_opt.startswith("cuda"):

            return 0 if torch.cuda.is_available() else "cpu"

        return device_opt



    def _load_fasterrcnn_model(self, model_path: Path) -> dict[str, Any]:

        import torch

        import torchvision

        from torchvision.transforms import functional as TF



        device_opt = str(self.app.config.get("MODEL_DEVICE", "auto")).lower()

        if device_opt == "auto":

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        else:

            device = torch.device(device_opt)



        model = torchvision.models.detection.fasterrcnn_resnet50_fpn(

            weights=None,

            weights_backbone=None,

            num_classes=4,

        ).to(device)



        payload = torch.load(model_path, map_location=device)

        state = payload.get("model_state") if isinstance(payload, dict) else None

        if state is None and isinstance(payload, dict):

            state = payload.get("state_dict")

        if state is None and isinstance(payload, dict):

            state = payload

        if state is None and hasattr(payload, "keys"):

            state = payload

        if state is None:

            raise RuntimeError("Invalid FasterRCNN checkpoint")



        model.load_state_dict(state, strict=False)

        model.eval()

        return {"model": model, "device": device, "torch": torch, "tf": TF}



