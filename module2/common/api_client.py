# -*- coding: utf-8 -*-
"""被测系统HTTP接口封装（检测模块/检测记录模块）

1. 每个账号一个 ``ApiClient`` 实例，内部维持requests.Session与JWT；
2. 只封装"被测页面实际会调用的接口"，保证自动化用例与页面行为一致；
3. 断言全部落在返回值上，不在客户端做兜底转换，避免掩盖缺陷。
"""
from __future__ import annotations
import json
from typing import Any
import requests
from .paths import ACCOUNTS, BASE_URL


class ApiClient:
    def __init__(self, account: str, base_url: str = BASE_URL, timeout: int = 60) -> None:
        self.account = account
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.token: str | None = None
        self.user: dict[str, Any] | None = None
        if account in ACCOUNTS:
            self.login(ACCOUNTS[account]["username"], ACCOUNTS[account]["password"])

    # ---------------------------------------------------------------- 基础
    def login(self, username: str, password: str) -> dict[str, Any]:
        resp = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        self.token = data["access_token"]
        self.user = data["user"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        return data

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return self.session.request(method, f"{self.base_url}{path}", **kwargs)

    def get(self, path: str, **kw) -> requests.Response:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> requests.Response:
        return self.request("POST", path, **kw)

    def put(self, path: str, **kw) -> requests.Response:
        return self.request("PUT", path, **kw)

    def delete(self, path: str, **kw) -> requests.Response:
        return self.request("DELETE", path, **kw)

    @staticmethod
    def body(resp: requests.Response) -> dict[str, Any]:
        """解析 JSON 响应；非 JSON（如 500 调试页）返回占位结构。"""
        try:
            return resp.json()
        except ValueError:
            return {"code": None, "data": None, "message": resp.text[:200]}

    # ------------------------------------------------------------ 检测模块
    def list_models(self) -> requests.Response:
        return self.get("/api/detection/models")

    def detect_image(self, file_bytes: bytes, filename: str, **form) -> requests.Response:
        data = {k: str(v) for k, v in form.items()}
        files = {"file": (filename, file_bytes, "application/octet-stream")}
        return self.post("/api/detection/image", files=files, data=data)

    def detect_video(self, file_bytes: bytes, filename: str, **form) -> requests.Response:
        data = {k: str(v) for k, v in form.items()}
        files = {"file": (filename, file_bytes, "video/x-msvideo")}
        return self.post("/api/detection/video", files=files, data=data)

    def video_task(self, task_id: str) -> requests.Response:
        return self.get(f"/api/detection/video/tasks/{task_id}")

    def video_preview(self, task_id: str) -> requests.Response:
        return self.get(f"/api/detection/video/tasks/{task_id}/preview")

    def image_records(self) -> requests.Response:
        return self.get("/api/detection/image/records")

    def video_records(self) -> requests.Response:
        return self.get("/api/detection/video/records")

    def realtime_start(self, **payload) -> requests.Response:
        return self.post("/api/detection/realtime/start", json=payload)

    def realtime_status(self, session_id: str) -> requests.Response:
        return self.get(f"/api/detection/realtime/sessions/{session_id}")

    def realtime_frame(self, session_id: str) -> requests.Response:
        return self.get(f"/api/detection/realtime/sessions/{session_id}/frame")

    def realtime_stop(self, session_id: str) -> requests.Response:
        return self.post(f"/api/detection/realtime/sessions/{session_id}/stop")

    # -------------------------------------------------------- 检测记录模块
    def list_records(self, **params) -> requests.Response:
        clean = {k: v for k, v in params.items() if v is not None}
        return self.get("/api/records", params=clean)

    def create_record(self, payload: dict[str, Any]) -> requests.Response:
        return self.post("/api/records", json=payload)

    def update_record(self, record_id: int, payload: dict[str, Any]) -> requests.Response:
        return self.put(f"/api/records/{record_id}", json=payload)

    def delete_record(self, record_id: int) -> requests.Response:
        return self.delete(f"/api/records/{record_id}")

    def record_ids(self, **params) -> list[int]:
        resp = self.list_records(page=1, page_size=100, **params)
        return [item["id"] for item in self.body(resp)["data"]["items"]]

    def latest_record(self, source_type: str | None = None) -> dict[str, Any] | None:
        """取当前账号最新的检测记录（列表按 detected_at 降序）。"""
        resp = self.list_records(page=1, page_size=20, source_type=source_type)
        items = self.body(resp)["data"]["items"]
        return items[0] if items else None


def raw_request(method: str, path: str, **kwargs) -> requests.Response:
    """不带 JWT 的裸请求，用于验证鉴权分支。"""
    kwargs.setdefault("timeout", 30)
    return requests.request(method, f"{BASE_URL}{path}", **kwargs)


def dump(resp: requests.Response, limit: int = 300) -> str:
    """把响应压缩成一行，便于写入测试报告。"""
    try:
        text = json.dumps(resp.json(), ensure_ascii=False)
    except ValueError:
        text = resp.text
    text = " ".join(text.split())
    return f"HTTP {resp.status_code} {text[:limit]}"
