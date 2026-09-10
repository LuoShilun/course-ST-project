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

# 10：检测历史记录是否按用户隔离，user1/user2 各自只能看到自己的图片与视频记录。（场景法）
@pytest.mark.api
@pytest.mark.case("TC-DET-10")
def test_detection_history_isolation(api_user1, api_user2, actual):
    img1 = assert_ok(api_user1.image_records())
    vid1 = assert_ok(api_user1.video_records())
    img2 = assert_ok(api_user2.image_records())
    vid2 = assert_ok(api_user2.video_records())
    assert {r["user_id"] for r in img1} <= {api_user1.user["id"]}, "user1 看到了他人图片记录"
    assert {r["user_id"] for r in vid1} <= {api_user1.user["id"]}, "user1 看到了他人视频记录"
    assert {r["user_id"] for r in img2} <= {api_user2.user["id"]}, "user2 看到了他人图片记录"
    assert {r["user_id"] for r in vid2} <= {api_user2.user["id"]}, "user2 看到了他人视频记录"
    actual(f"user1 图片 {len(img1)} 条 / 视频 {len(vid1)} 条，user_id 集合={sorted({r['user_id'] for r in img1 + vid1})}；"
           f"user2 图片 {len(img2)} 条 / 视频 {len(vid2)} 条，user_id 集合={sorted({r['user_id'] for r in img2 + vid2})}")



# 11：视频检测任务全流程——提交任务、轮询状态、完成校验、结果字段与预览接口是否正常。（场景法）
@pytest.mark.api
@pytest.mark.case("TC-DET-11")
def test_video_task_full_flow(api_user1, actual):
    submitted = assert_ok(api_user1.detect_video(video_bytes(), "sample_clip.avi",
                                                 model_key="student.pt", score_thresh=0.25))
    task_id = submitted["id"]
    assert submitted["status"] in ("queued", "running"), f"提交后状态异常：{submitted}"

    final = None
    deadline = time.time() + 180
    seen = []
    while time.time() < deadline:
        final = assert_ok(api_user1.video_task(task_id))
        seen.append(final["status"])
        if final["status"] in ("finished", "failed"):
            break
        time.sleep(3)

    assert final and final["status"] == "finished", f"任务未正常完成：{final}"
    assert final["progress"] == 100, f"完成后进度应为 100：{final}"
    result = final["result"]
    assert result.get("frames_processed", 0) > 0, f"应处理到视频帧：{result}"
    assert "class_counts" in result

    preview = api_user1.video_preview(task_id)
    assert preview.status_code == 200, f"预览接口异常：{dump(preview)}"
    assert preview.headers.get("Content-Type", "").startswith("video/"), preview.headers
    assert len(preview.content) > 0, "预览内容为空"
    actual(f"任务 {task_id} 状态流转 {'->'.join(dict.fromkeys(seen))}，progress=100，"
           f"frames_processed={result['frames_processed']}，class_counts={result['class_counts']}；"
           f"预览 HTTP 200，{preview.headers.get('Content-Type')}，{len(preview.content)} 字节")


# 12：user2访问user1的视频任务详情/预览是否被拒绝（403+code=4031）。（场景法）
@pytest.mark.api
@pytest.mark.case("TC-DET-12")
def test_video_task_cross_user_denied(api_user1, api_user2, actual):
    submitted = assert_ok(api_user1.detect_video(video_bytes(), "cross_user.avi",
                                                 model_key="student.pt", score_thresh=0.25))
    task_id = submitted["id"]
    detail = api_user2.video_task(task_id)
    preview = api_user2.video_preview(task_id)
    b1 = assert_error(detail, http_status=403, code=4031)
    b2 = assert_error(preview, http_status=403, code=4031)
    actual(f"user2 查询 user1 的任务 {task_id}：详情 HTTP {detail.status_code}/code={b1['code']}，"
           f"预览 HTTP {preview.status_code}/code={b2['code']}")

# 13：实时监控会话生命周期——启动、查询状态、取帧、越权访问、停止后状态是否为 stopped。（场景法）
@pytest.mark.api
@pytest.mark.case("TC-DET-13")
def test_realtime_session_lifecycle(api_user1, api_user2, actual):
    started = assert_ok(api_user1.realtime_start(source="0", model_key="student.pt",
                                                 score_thresh=0.25, realtime_fps=8))
    session_id = started["id"]
    assert started["status"] in ("queued", "running"), f"会话初始状态异常：{started}"

    time.sleep(3)
    status = assert_ok(api_user1.realtime_status(session_id))
    assert status["id"] == session_id
    assert status["status"] in ("queued", "running"), f"会话状态异常：{status}"

    frame = api_user1.realtime_frame(session_id)
    assert frame.status_code in (200, 204), f"取帧接口异常：{dump(frame)}"

    denied = api_user2.realtime_status(session_id)
    assert_error(denied, http_status=403, code=4031)

    stopped = assert_ok(api_user1.realtime_stop(session_id))
    assert stopped["status"] == "stopped", f"停止后状态应为 stopped：{stopped}"
    again = assert_ok(api_user1.realtime_status(session_id))
    assert again["status"] == "stopped"
    actual(f"会话 {session_id} 启动成功（status={started['status']}），3 秒后 status={status['status']}、"
           f"frames_processed={status['frames_processed']}；取帧 HTTP {frame.status_code}；"
           f"user2 访问 HTTP {denied.status_code}；停止后 status={again['status']}")
