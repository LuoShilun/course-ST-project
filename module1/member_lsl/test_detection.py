# -*- coding: utf-8 -*-
"""检测模块自动化测试（罗时伦）
被测对象：检测页面 /detect 及其后端接口 /api/detection/*。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from common.api_client import ApiClient, dump, raw_request
from common.assertions import assert_error, assert_ok
from common.assets import image_bytes, video_bytes
from common.paths import BACKEND_ROOT

# ==========================================================================
# 一、接口自动化用例（TC-DET-01 ~ 06）
# ==========================================================================
def _image_total(client) -> int:
    """/api/detection/image/records 最多返回 200 条，改用 /api/records 的 total 统计。"""
    return assert_ok(client.list_records(page=1, page_size=1, source_type="image"))["total"]

#01：GET/api/detection/models返回的模型列表结构是否完整（key/display_name/engine/size_mb），
# 以及inference_enabled、default_model_key字段是否正确（等价类划分）。
@pytest.mark.api
@pytest.mark.case("TC-DET-01")
def test_models_list_ok(api_user1, actual):
    data = assert_ok(api_user1.list_models())
    models = data["models"]
    assert isinstance(models, list) and models, f"模型列表为空：{data}"
    for item in models:
        for key in ("key", "display_name", "engine", "size_mb"):
            assert key in item, f"模型项缺少字段 {key}：{item}"
    assert isinstance(data["inference_enabled"], bool)
    actual(f"HTTP 200，返回 {len(models)} 个模型：{', '.join(m['key'] for m in models)}；"
           f"inference_enabled={data['inference_enabled']}，default_model_key={data['default_model_key']}")


# 02：未携带 token 访问检测接口是否被拒绝（GET /models、POST /image 均应返回 401）（等价类划分）。
@pytest.mark.api
@pytest.mark.case("TC-DET-02")
def test_detection_requires_token(actual):
    r1 = raw_request("GET", "/api/detection/models")
    r2 = raw_request("POST", "/api/detection/image")
    assert r1.status_code == 401, f"期望 401，实际 {dump(r1)}"
    assert r2.status_code == 401, f"期望 401，实际 {dump(r2)}"
    actual(f"GET /models -> HTTP {r1.status_code}；POST /image -> HTTP {r2.status_code}，均未返回业务数据")


# 03：上传图片时文件名为空，接口是否返回 400 + code=4002。（边界值分析法）
@pytest.mark.api
@pytest.mark.case("TC-DET-03")
def test_detect_image_empty_filename(api_user1, actual):
    resp = api_user1.detect_image(image_bytes("plain"), "")
    body = assert_error(resp, http_status=400, code=4002)
    actual(f"HTTP {resp.status_code}，code={body['code']}，message={body['message']}")



# 04：上传伪装成图片的 .txt 文件，接口是否返回 400 + code=4003，并验证非法文件不产生检测记录。（等价类划分）
@pytest.mark.api
@pytest.mark.case("TC-DET-04")
def test_detect_image_not_an_image(api_user1, actual):
    before = _image_total(api_user1)
    resp = api_user1.detect_image(image_bytes("not_image"), "not_an_image.txt")
    body = assert_error(resp, http_status=400, code=4003)
    after = _image_total(api_user1)
    assert after == before, "非法文件不应产生检测记录"
    actual(f"HTTP {resp.status_code}，code={body['code']}，message={body['message']}；记录数保持 {after} 条不变")



# 05：正常图片检测能否成功，检测记录数是否 +1，落库记录的user_id/source_type/media_path是否正确。（等价类划分）
@pytest.mark.api
@pytest.mark.case("TC-DET-05")
def test_detect_image_success_and_persist(api_user1, actual):
    before = _image_total(api_user1)
    resp = api_user1.detect_image(image_bytes("trash_bio"), "underwater_trash_bio.jpg",
                                  model_key="student.pt", score_thresh=0.25)
    data = assert_ok(resp)
    assert isinstance(data.get("detections"), list) and data["detections"], "预期检测到目标"
    after = _image_total(api_user1)
    assert after == before + 1, f"应新增 1 条记录，实际 {before} -> {after}"
    rec = api_user1.latest_record("image")
    assert rec["user_id"] == api_user1.user["id"]
    assert rec["source_type"] == "image"
    assert rec["media_path"], "落库记录应包含媒体路径"
    actual(f"HTTP 200，检测到 {len(data['detections'])} 个目标，summary={data['summary']}；"
           f"记录数 {before}->{after}，最新记录 id={rec['id']}、user_id={rec['user_id']}")


# 06：检测接口返回的 detections 与落库记录是否一致（is_trash、detected_type、confidence）。（等价类划分）
@pytest.mark.api
@pytest.mark.case("TC-DET-06")
def test_detect_image_record_consistency(api_user1, actual):
    before = _image_total(api_user1)
    data = assert_ok(api_user1.detect_image(image_bytes("trash_bio"), "consistency.jpg",
                                            model_key="student.pt", score_thresh=0.25))
    detections = data["detections"]
    trash = [d for d in detections if d.get("is_trash")]
    pool = trash or detections
    rep = max(pool, key=lambda d: float(d["score"])) if pool else None

    after = _image_total(api_user1)
    assert after == before + 1, "一张图片应只生成一条记录"
    rec = api_user1.latest_record("image")

    assert rec["is_trash"] is bool(trash), f"垃圾标记与检测结果不一致：{rec}"
    if rep is None:
        assert rec["detected_type"] == "none" and float(rec["confidence"]) == 0.0
    else:
        assert rec["detected_type"] == rep["class_name"], f"代表目标不一致：{rec} vs {rep}"
        assert abs(float(rec["confidence"]) - float(rep["score"])) < 1e-6, f"置信度不一致：{rec} vs {rep}"
    actual(f"记录数 {before}->{after}；检测到 {len(detections)} 个目标（垃圾 {len(trash)} 个），"
           f"落库 detected_type={rec['detected_type']}、confidence={rec['confidence']}、is_trash={rec['is_trash']}")

# 07：传入非法 model_key 时，接口是否应返回错误而非静默降级。（错误推测法）
@pytest.mark.api
@pytest.mark.defect
@pytest.mark.case("TC-DET-07")
@pytest.mark.xfail(strict=True, reason="BUG-04：非法 model_key 被静默降级，未返回错误")
def test_invalid_model_key_rejected(api_user1, actual):
    resp = api_user1.detect_image(image_bytes("trash_bio"), "bad_model.jpg",
                                  model_key="not-exist.pt", score_thresh=0.25)
    body = ApiClient.body(resp)
    rec = api_user1.latest_record("image")
    actual(f"HTTP {resp.status_code}，model_status={body['data'].get('model_status') if body.get('data') else None}，"
           f"detections={len(body['data'].get('detections', [])) if body.get('data') else None}，"
           f"落库 detected_type={rec['detected_type']}、model_key={rec['details'].get('model_key')}")
    assert resp.status_code >= 400, f"非法模型键应被拒绝，实际 {dump(resp)}"


# 08：中文文件名上传后，落盘 media_path 是否保留中文原名与 .png 扩展名。（边界值分析）
@pytest.mark.api
@pytest.mark.defect
@pytest.mark.case("TC-DET-08")
@pytest.mark.xfail(strict=True, reason="BUG-05：中文文件名被 secure_filename 破坏，落盘名丢失原名与扩展名")
def test_chinese_filename_kept(api_user1, actual):
    assert_ok(api_user1.detect_image(image_bytes("png"), "水下垃圾样本.png",
                                     model_key="student.pt", score_thresh=0.25))
    rec = api_user1.latest_record("image")
    media_path = rec["media_path"] or ""
    actual(f"落库 media_path={media_path}")
    assert "水下垃圾样本" in media_path and media_path.lower().endswith(".png"), \
        f"落盘文件名应保留中文原名与扩展名，实际 {media_path}"

# 09：robot_id 传入非整数 "abc" 时，接口是否返回 4xx 而非500调试页。（错误推测法）
@pytest.mark.api
@pytest.mark.defect
@pytest.mark.case("TC-DET-09")
@pytest.mark.xfail(strict=True, reason="BUG-01：robot_id 非整数导致未捕获异常，返回 500 调试页")
def test_admin_invalid_robot_id(api_admin, actual):
    resp = api_admin.detect_image(image_bytes("plain"), "plain.jpg", robot_id="abc")
    actual(dump(resp, 200))
    assert resp.status_code < 500, f"参数错误不应返回 5xx，实际 {dump(resp)}"
    assert_error(resp, http_status=400)

