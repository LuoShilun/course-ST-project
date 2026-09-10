# -*- coding: utf-8 -*-
"""pytest全局配置与执行结果记录。
除常规 fixture 外，本文件实现一个轻量结果记录器：把每个用例的 nodeid、
用例编号、执行状态、实际结果写入 reports/results.json
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from common.api_client import ApiClient
from common.assertions import set_actual
from common.assets import ensure_assets
from common.paths import BASE_URL, REPORTS_DIR, WEB_URL

RESULTS: dict[str, dict] = {}
STARTED_AT = datetime.now().isoformat(timespec="seconds")


def pytest_addoption(parser):
    parser.addoption("--results-json", action="store", default=str(REPORTS_DIR / "results.json"),
                     help="测试执行结果输出文件")


def pytest_configure(config):
    config.addinivalue_line("markers", "case(case_id): 关联附录1测试用例编号")
    config.addinivalue_line("markers", "api: 接口层自动化用例")
    config.addinivalue_line("markers", "ui: 浏览器UI自动化用例")
    config.addinivalue_line("markers", "defect: 缺陷确认用例（记录已知缺陷，修复后应转为通过）")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    case_id = None
    for mark in item.iter_markers(name="case"):
        case_id = mark.args[0]
    entry = RESULTS.setdefault(item.nodeid, {"nodeid": item.nodeid, "case_id": case_id})

    if call.when == "setup" and call.excinfo is not None:
        entry.update(status="error", actual=f"用例准备失败：{call.excinfo.exconly()}")
        return
    if call.when != "call":
        return

    entry["duration"] = round(call.duration, 3)
    actual = getattr(item, "_dsh_actual", "")
    if call.excinfo is None:
        entry.update(status="passed", actual=actual or "实际结果与预期一致")
    else:
        detail = " ".join(str(call.excinfo.value).split())[:400] or call.excinfo.exconly()[:400]
        entry.update(status="failed", actual=(f"{actual}；断言失败：{detail}" if actual else detail))

    xfail_mark = item.get_closest_marker("xfail")
    if xfail_mark and entry["status"] == "failed":
        entry["status"] = "xfailed"
        entry["reason"] = xfail_mark.kwargs.get("reason", "")


def pytest_sessionstart(session):
    ensure_assets()


def pytest_sessionfinish(session, exitstatus):
    path = Path(session.config.getoption("--results-json"))
    payload = {
        "run_started_at": STARTED_AT,
        "run_finished_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "web_url": WEB_URL,
        "case_count": len(RESULTS),
        "results": list(RESULTS.values()),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def api_admin() -> ApiClient:
    return ApiClient("admin")


@pytest.fixture(scope="session")
def api_user1() -> ApiClient:
    return ApiClient("user1")


@pytest.fixture(scope="session")
def api_user2() -> ApiClient:
    return ApiClient("user2")


@pytest.fixture
def temp_records():
    """用例中创建的记录，测试结束后统一清理，避免污染业务数据。"""
    created: list[int] = []
    yield created
    admin = ApiClient("admin")
    for rid in created:
        try:
            admin.delete_record(rid)
        except Exception:  # noqa: BLE001
            pass


@pytest.fixture
def actual(request):
    """把实际结果写入采集器。"""
    return lambda text: set_actual(request.node, text)


@pytest.fixture(scope="session")
def ui_driver():
    """浏览器实例；无法启动时相关用例标记为未执行。"""
    from common.ui import build_driver

    try:
        driver = build_driver(headless=True)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"浏览器驱动不可用：{exc}")
    yield driver
    driver.quit()


@pytest.fixture
def ui_user1(ui_driver):
    from common.ui import ui_login

    ui_login(ui_driver, "user1")
    yield ui_driver
