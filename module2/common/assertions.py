# -*- coding: utf-8 -*-
"""通用断言与"实际结果"记录工具。"""
from __future__ import annotations

from typing import Any

import requests

from .api_client import ApiClient, dump


def assert_ok(resp: requests.Response, expected_code: int = 0) -> Any:
    """断言业务成功响应，返回 data。"""
    body = ApiClient.body(resp)
    assert resp.status_code == 200, f"期望 HTTP 200，实际 {dump(resp)}"
    assert body.get("code") == expected_code, f"期望 code={expected_code}，实际 {dump(resp)}"
    return body["data"]


def assert_error(resp: requests.Response, http_status: int | None = None, code: int | None = None) -> dict:
    """断言业务失败响应（统一 JSON 结构，且不携带业务数据）。"""
    body = ApiClient.body(resp)
    if http_status is not None:
        assert resp.status_code == http_status, f"期望 HTTP {http_status}，实际 {dump(resp)}"
    if code is not None:
        assert body.get("code") == code, f"期望 code={code}，实际 {dump(resp)}"
    assert body.get("data") is None, f"错误响应不应携带业务数据：{dump(resp)}"
    return body


def set_actual(node, text: str) -> str:
    """把实际结果挂到 pytest item 上，供结果采集器写入 reports/results.json。"""
    node._dsh_actual = " ".join(str(text).split())
    return node._dsh_actual
