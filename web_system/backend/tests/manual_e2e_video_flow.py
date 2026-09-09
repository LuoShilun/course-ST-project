from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:5000/api"
USERNAME = "admin"
PASSWORD = "admin123"
VIDEO_PATH = Path(r"e:\MyProjectWorkSpace\underwater_project\web_system\backend\uploads\videos\1774858740241_demo.mp4")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check(resp: requests.Response, name: str) -> dict:
    if resp.status_code != 200:
        raise RuntimeError(f"{name} HTTP {resp.status_code}: {resp.text[:500]}")
    payload = resp.json()
    if int(payload.get("code", -1)) != 0:
        raise RuntimeError(f"{name} API failed: {json.dumps(payload, ensure_ascii=False)}")
    return payload


def main() -> None:
    if not VIDEO_PATH.exists():
        raise FileNotFoundError(f"视频不存在: {VIDEO_PATH}")

    s = requests.Session()

    login = _check(
        s.post(
            f"{BASE}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=15,
        ),
        "login",
    )
    token = str(login["data"]["access_token"])
    s.headers.update({"Authorization": f"Bearer {token}"})
    print("[OK] login")

    models = _check(s.get(f"{BASE}/detection/models", timeout=15), "list_models")
    model_data = models.get("data", {}) or {}
    model_rows = model_data.get("models", []) or []
    model_key = "mock-default"
    for m in model_rows:
        if str(m.get("key")) == "mock-default":
            model_key = "mock-default"
            break
    print(f"[OK] use model_key={model_key}")

    with VIDEO_PATH.open("rb") as f:
        submit = _check(
            s.post(
                f"{BASE}/detection/video",
                data={
                    "model_key": model_key,
                    "score_thresh": "0.25",
                    "use_cyclegan": "false",
                    "use_tracking": "false",
                },
                files={"file": (VIDEO_PATH.name, f, "video/mp4")},
                timeout=30,
            ),
            "submit_video",
        )

    task_id = str(submit["data"]["id"])
    print(f"[OK] submit task_id={task_id}")

    deadline = time.time() + 180
    task = None
    while time.time() < deadline:
        task_resp = _check(s.get(f"{BASE}/detection/video/tasks/{task_id}", timeout=15), "get_task")
        task = task_resp.get("data", {}) or {}
        status = str(task.get("status", ""))
        progress = int(task.get("progress", 0) or 0)
        print(f"[POLL] status={status} progress={progress}")
        if status in {"finished", "failed"}:
            break
        time.sleep(1.0)

    if task is None:
        raise RuntimeError("任务轮询失败: 无任务数据")
    if str(task.get("status")) != "finished":
        raise RuntimeError(f"任务未完成: status={task.get('status')} error={task.get('error_message')}")

    result = task.get("result", {}) or {}
    output_video_path = Path(str(result.get("output_video_path", "")))
    output_preview_path_raw = str(result.get("output_video_preview_path", "") or "")
    output_preview_path = Path(output_preview_path_raw) if output_preview_path_raw else output_video_path

    if not output_video_path.exists():
        raise RuntimeError(f"检测后视频不存在: {output_video_path}")
    if not output_preview_path.exists():
        raise RuntimeError(f"预览视频不存在: {output_preview_path}")

    preview_resp = s.get(f"{BASE}/detection/video/tasks/{task_id}/preview", timeout=60)
    if preview_resp.status_code != 200:
        raise RuntimeError(f"preview HTTP {preview_resp.status_code}: {preview_resp.text[:500]}")

    preview_bytes = preview_resp.content
    expected_bytes = output_preview_path.read_bytes()
    if _sha256_bytes(preview_bytes) != _sha256_bytes(expected_bytes):
        raise RuntimeError("preview 响应内容与检测后预览视频文件不一致")

    print("[OK] task finished")
    print(f"[OK] output_video_path={output_video_path}")
    print(f"[OK] output_video_preview_path={output_preview_path}")
    print(f"[OK] output_video_web_playable={bool(result.get('output_video_web_playable'))}")
    print(f"[OK] preview_bytes={len(preview_bytes)}")
    print("[PASS] 离线视频检测联调通过：preview 返回检测后视频")


if __name__ == "__main__":
    main()
