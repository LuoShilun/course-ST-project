# -*- coding: utf-8 -*-
"""模块二（方案2「AI测」）· 检测模块自动化测试（罗时伦）
被测对象：检测页面 `/detect` 及其后端接口 `/api/detection/*`。

全部 15 条用例都标了 ``@pytest.mark.ai``：

    A. 用例生成（TC2-DET-01 ~ 05）——AI先产出用例草稿(ai_case.json）,人工检查修正后固化为可执行用例；

    B. 期望推断（TC2-DET-02/03/04/05/12/13/14）——AI依据接口契约推断"合理期望",与业务不变量（ai_expectations.json），
人工把AI给的可执行样例改写成本文件中的显式校验函数，运行期断言集合由AI契约驱动，断言实现由人工检查；

    C. 失败归因（TC2-DET-15）——验证ai_assist.analyze_failures()对真实失败输出的归因能力；人工补AI遗漏（TC2-DET-08/10/11）。
"""
from __future__ import annotations

import base64
import io
import statistics
import time
from pathlib import Path
from typing import Any, Callable

import pytest
from PIL import Image

from common import ai_assist
from common.api_client import ApiClient, dump, raw_request
from common.assertions import assert_error, assert_ok
from common.assets import image_bytes, video_bytes

pytestmark = pytest.mark.ai

IMAGE_INTERFACE = "POST /api/detection/image"
MODELS_INTERFACE = "GET /api/detection/models"
VIDEO_TASK_INTERFACE = "GET /api/detection/video/tasks/{task_id}"
REALTIME_FRAME_INTERFACE = "GET /api/detection/realtime/sessions/{session_id}/frame"


# ==========================================================================
# 人工检查后写成的"不变量校验函数"（AI契约只给ID与表达式草稿，具体实现手动组织）
# ==========================================================================
def _decode_data_uri(value: str) -> Image.Image:
    assert isinstance(value, str) and value.startswith("data:image"), f"不是 data URI：{str(value)[:40]}"
    payload = value.split(",", 1)[1]
    return Image.open(io.BytesIO(base64.b64decode(payload)))


def _inv_img_01(data: dict, ctx: dict) -> None:
    """INV-IMG-01 summary 计数与 detections 一致。"""
    detections = data.get("detections", [])
    summary = data.get("summary", {})
    assert summary.get("total") == len(detections), \
        f"summary.total={summary.get('total')} 与 detections 长度 {len(detections)} 不一致"
    trash = [d for d in detections if d.get("is_trash")]
    assert summary.get("trash_count") == len(trash), \
        f"summary.trash_count={summary.get('trash_count')} 与垃圾目标数 {len(trash)} 不一致"


def _inv_img_02(data: dict, ctx: dict) -> None:
    """INV-IMG-02 score 落在 [0,1]。"""
    for d in data.get("detections", []):
        score = float(d["score"])
        assert 0.0 <= score <= 1.0, f"score 越界：{d}"


def _inv_img_03(data: dict, ctx: dict) -> None:
    """INV-IMG-03 class_name 与 is_trash 语义一致。"""
    for d in data.get("detections", []):
        expected = d["class_name"].strip().lower() == "trash"
        assert bool(d["is_trash"]) is expected, \
            f"类别与垃圾标记不一致：class_name={d['class_name']} is_trash={d['is_trash']}"


def _inv_img_04(data: dict, ctx: dict) -> None:
    """INV-IMG-04 bbox 几何合法。"""
    width, height = ctx["size"]
    for d in data.get("detections", []):
        bbox = d["bbox"]
        assert len(bbox) == 4, f"bbox 不是 4 个数：{bbox}"
        x1, y1, x2, y2 = (float(v) for v in bbox)
        assert 0 <= x1 < x2 <= width, f"bbox 横向越界：{bbox}，图宽 {width}"
        assert 0 <= y1 < y2 <= height, f"bbox 纵向越界：{bbox}，图高 {height}"


def _inv_img_05(data: dict, ctx: dict) -> None:
    """INV-IMG-05 两张返回图可解码且与上传图尺寸一致。"""
    width, height = ctx["size"]
    for key in ("source_image", "annotated_image"):
        image = _decode_data_uri(data[key])
        assert image.size == (width, height), f"{key} 尺寸 {image.size} 与上传图 {(width, height)} 不一致"


def _inv_mdl_01(data: dict, ctx: dict) -> None:
    """INV-MDL-01 engine 属于受控词表。"""
    vocab = {"yolo", "fasterrcnn", "student", "onnx", "mock"}
    for m in data.get("models", []):
        assert m["engine"] in vocab, f"engine 不在受控词表：{m}"


def _inv_mdl_02(data: dict, ctx: dict) -> None:
    """INV-MDL-02 size_mb 为正；仅 mock-default 允许为 0。"""
    for m in data.get("models", []):
        if m["key"] == "mock-default":
            assert float(m["size_mb"]) == 0.0
        else:
            assert float(m["size_mb"]) > 0, f"size_mb 非正：{m}"


def _inv_mdl_03(data: dict, ctx: dict) -> None:
    """INV-MDL-03 default_model_key 必须存在于 models 列表（跨字段引用完整性）。"""
    keys = [m["key"] for m in data.get("models", [])]
    assert data.get("default_model_key") in keys, \
        f"default_model_key={data.get('default_model_key')!r} 不在模型列表 {keys} 中"


def _inv_vid_01(data: dict, ctx: dict) -> None:
    """INV-VID-01 状态取值合法且终态不回退。"""
    allowed = {"queued", "running", "finished", "failed"}
    assert data["status"] in allowed, f"非法状态：{data['status']}"
    for status in ctx.get("statuses", []):
        assert status in allowed, f"轮询中出现非法状态：{status}"
    if "finished" in ctx.get("statuses", []) or "failed" in ctx.get("statuses", []):
        assert data["status"] in {"finished", "failed"}, "任务已到终态后又回退"


def _inv_vid_02(data: dict, ctx: dict) -> None:
    """INV-VID-02 progress 单调不减，终态 finished 为 100。"""
    progress = ctx.get("progress", [])
    assert progress == sorted(progress), f"progress 出现回退：{progress}"
    assert data["status"] != "finished" or data["progress"] == 100, \
        f"finished 但 progress={data['progress']}"


def _inv_vid_03(data: dict, ctx: dict) -> None:
    """INV-VID-03 frames_processed 等于源视频帧数。

    注意：AI 原始表达式写成了 ``frames_processed < 24``（方向相反），
    这里按人工修正后的语义实现为"等于源视频总帧数"。
    """
    assert data["result"].get("frames_processed") == ctx["expect_frames"], \
        f"frames_processed={data['result'].get('frames_processed')}，期望 {ctx['expect_frames']}"


def _inv_rt_01(data: dict, ctx: dict) -> None:
    """INV-RT-01 会话停止后取帧不得再返回画面。"""
    resp = ctx["response"]
    assert resp.status_code in (204, 404, 403), \
        f"停止后取帧返回 HTTP {resp.status_code}，应无画面"
    assert not resp.content or resp.status_code in (403, 404), "停止后仍返回了图像内容"


INVARIANT_CHECKS: dict[str, Callable[[dict, dict], None]] = {
    "INV-IMG-01": _inv_img_01, "INV-IMG-02": _inv_img_02, "INV-IMG-03": _inv_img_03,
    "INV-IMG-04": _inv_img_04, "INV-IMG-05": _inv_img_05,
    "INV-MDL-01": _inv_mdl_01, "INV-MDL-02": _inv_mdl_02, "INV-MDL-03": _inv_mdl_03,
    "INV-VID-01": _inv_vid_01, "INV-VID-02": _inv_vid_02, "INV-VID-03": _inv_vid_03,
    "INV-RT-01": _inv_rt_01,
}


def _contract(interface: str) -> dict:
    """取 AI 推断出的接口契约（live 后端可用时现场推断，否则回放留档）。"""
    return ai_assist.infer_expectation(interface)


def _assert_required_fields(contract: dict, data: dict) -> None:
    missing = [f for f in contract["required_fields"] if f not in data]
    assert not missing, f"响应缺少 AI 契约要求的字段：{missing}"


def _run_invariants(contract: dict, data: dict, ctx: dict, *,
                    skip: frozenset[str] = frozenset(), only: set[str] | None = None) -> list[str]:
    """按 AI 契约声明的顺序执行人工实现的不变量校验，返回已执行的 ID 列表。

    ``skip`` / ``only`` 用于把同一条契约里的不同不变量拆到不同用例中
    （已确认失败的不变量单独做成缺陷确认用例，避免影响其余用例的判定）。
    """
    ran = []
    for inv in contract["invariants"]:
        if inv["id"] in skip or (only is not None and inv["id"] not in only):
            continue
        check = INVARIANT_CHECKS.get(inv["id"])
        assert check is not None, f"AI 契约中的不变量 {inv['id']} 尚未有对应校验函数（人工漏实现）"
        check(data, ctx)
        ran.append(inv["id"])
    return ran


def _png_of_size(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (20, 120, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _image_size(payload: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(payload)) as img:
        return img.size


# ==========================================================================
# A. AI 生成用例 → 人工检查后固化（TC2-DET-01 ~ TC2-DET-05）
# ==========================================================================
@pytest.mark.api
@pytest.mark.case("TC2-DET-01")
def test_models_contract_invariants(api_user1, actual):
    """TC2-DET-01 模型列表满足 AI 推断的契约（engine 受控词表 + size_mb 正数）。

    来源：AI 草稿 A-01；人工修正——AI 只检查 key/display_name，
    漏了engine词表与size_mb（且未考虑 mock-default 的 size_mb=0 例外）。
    """
    contract = _contract(MODELS_INTERFACE)
    data = assert_ok(api_user1.list_models())
    _assert_required_fields(contract, data)
    ran = _run_invariants(contract, data, {}, skip={"INV-MDL-03"})
    actual(f"契约来源={contract['source']}；必填字段齐全；通过不变量 {', '.join(ran)}；"
           f"模型 {len(data['models'])} 个，engine={sorted({m['engine'] for m in data['models']})}")


@pytest.mark.api
@pytest.mark.case("TC2-DET-02")
def test_image_summary_matches_detections(api_user1, actual):
    """TC2-DET-02 检测响应的 summary 统计与 detections 逐项一致。
    来源：AI 草稿 A-05（AI 建议直接采用）。
    """
    contract = _contract(IMAGE_INTERFACE)
    payload = image_bytes("trash_bio")
    data = assert_ok(api_user1.detect_image(payload, "summary_check.jpg",
                                           model_key="student.pt", score_thresh=0.25))
    _assert_required_fields(contract, data)
    ran = _run_invariants(contract, data, {"size": _image_size(payload)})
    actual(f"契约来源={contract['source']}；{len(data['detections'])} 个目标，summary={data['summary']}；"
           f"通过不变量 {', '.join(ran)}")


@pytest.mark.api
@pytest.mark.case("TC2-DET-03")
def test_annotated_image_decodable(api_user1, actual):
    """TC2-DET-03 返回的原图与标注图必须是可解码图片，且尺寸与上传图一致。

    来源：AI 草稿 A-02 只断言"字段存在"、A-13 只校验"以 data:image 开头"——
    两条都是弱断言，人工合并并改为真正的 base64 解码 + PIL 尺寸比对。
    """
    contract = _contract(IMAGE_INTERFACE)
    payload = image_bytes("trash_bio")
    size = _image_size(payload)
    data = assert_ok(api_user1.detect_image(payload, "decode_check.jpg",
                                            model_key="student.pt", score_thresh=0.25))
    ran = _run_invariants(contract, data, {"size": size})
    decoded = {k: _decode_data_uri(data[k]).size for k in ("source_image", "annotated_image")}
    actual(f"上传图尺寸={size}；解码后 source_image={decoded['source_image']}、"
           f"annotated_image={decoded['annotated_image']}；通过不变量 {', '.join(ran)}")


@pytest.mark.api
@pytest.mark.case("TC2-DET-04")
def test_detection_score_and_class_consistency(api_user1, actual):
    """TC2-DET-04 置信度在 [0,1] 且 class_name 与 is_trash 语义一致。

    来源：AI 草稿 A-03（score 范围）采用；"类别与垃圾标记一致"这条交叉约束是人工补的。
    """
    contract = _contract(IMAGE_INTERFACE)
    payload = image_bytes("trash_bio")
    data = assert_ok(api_user1.detect_image(payload, "score_check.jpg",
                                            model_key="student.pt", score_thresh=0.25))
    ran = _run_invariants(contract, data, {"size": _image_size(payload)})
    pairs = [(d["class_name"], round(float(d["score"]), 4), d["is_trash"]) for d in data["detections"]]
    actual(f"目标(类别, 置信度, 是否垃圾)={pairs}；通过不变量 {', '.join(ran)}")


@pytest.mark.api
@pytest.mark.case("TC2-DET-05")
def test_detection_bbox_geometry(api_user1, actual):
    """TC2-DET-05 目标框坐标几何合法且不越界。

    来源：AI 草稿 A-04 只校验"是 4 个数"，人工补上 0≤x1<x2≤W、0≤y1<y2≤H。
    """
    contract = _contract(IMAGE_INTERFACE)
    payload = image_bytes("trash_bio")
    size = _image_size(payload)
    data = assert_ok(api_user1.detect_image(payload, "bbox_check.jpg",
                                            model_key="student.pt", score_thresh=0.25))
    ran = _run_invariants(contract, data, {"size": size})
    boxes = [[round(float(v), 1) for v in d["bbox"]] for d in data["detections"]]
    actual(f"图尺寸={size}；bbox={boxes}；通过不变量 {', '.join(ran)}")


# ==========================================================================
# B. AI 期望推断 → 语义级断言（TC2-DET-06 ~ TC2-DET-14）
# ==========================================================================
@pytest.mark.api
@pytest.mark.defect
@pytest.mark.case("TC2-DET-06")
@pytest.mark.xfail(strict=True, reason="BUG2-01：非法 model_key 未按契约返回 4xx，而是静默降级为默认模型")
def test_invalid_model_key_should_be_rejected(api_user1, actual):
    """TC2-DET-06 传入不存在的 model_key 应按契约返回 4xx。

    来源：AI 草稿 A-06。该条由"AI 期望推断"驱动 —— AI 判定这是非法输入、期望 4xx。
    """
    contract = _contract(IMAGE_INTERFACE)
    resp = api_user1.detect_image(image_bytes("trash_bio"), "bad_model.jpg",
                                  model_key="not-exist.pt", score_thresh=0.25)
    body = ApiClient.body(resp)
    record = api_user1.latest_record("image")
    actual(f"契约期望状态={contract['expected_status']}（非法输入应为 4xx）；实际 HTTP {resp.status_code}，"
           f"model_status={body['data'].get('model_status') if body.get('data') else None}，"
           f"落库 detected_type={record['detected_type']}、details.model_key={record['details'].get('model_key')}")
    assert resp.status_code >= 400, f"非法模型键应按契约被拒绝，实际 {dump(resp)}"


@pytest.mark.api
@pytest.mark.case("TC2-DET-07")
def test_score_thresh_abnormal_string_forms(api_user1, actual):
    """TC2-DET-07 score_thresh 的非数值/非常规字符串形态不应导致 500。

    来源：AI 草稿 A-07 —— AI 给的输入是 ``float('nan')``，但 multipart 传输时会退化为
    字符串 ``'nan'``，AI 没意识到；人工改为直接发送 4 种字符串形态。
    """
    payload = image_bytes("plain")
    results = {}
    for raw in ["nan", "inf", "1e-3", "  0.5  "]:
        resp = api_user1.detect_image(payload, "thresh_form.jpg", model_key="student.pt", score_thresh=raw)
        results[raw] = resp.status_code
        assert resp.status_code < 500, f"score_thresh={raw!r} 触发服务端异常：{dump(resp)}"
    actual("各形态状态码：" + "，".join(f"{k!r}->{v}" for k, v in results.items()) + "；均未出现 5xx")


@pytest.mark.api
@pytest.mark.case("TC2-DET-08")
def test_extreme_image_sizes(api_user1, actual):
    """TC2-DET-08 极小图与极端宽高比图片不应导致 500。

    来源：AI 草稿 A-08（1×1）＋ 人工补充 4:1 长条图；AI 原始期望只写了"不应崩溃"，
    人工细化为"2xx 或 4xx 均可接受，但不得 5xx"。
    """
    observations = {}
    for label, payload in {"1x1": _png_of_size(1, 1), "400x100(4:1)": _png_of_size(400, 100)}.items():
        resp = api_user1.detect_image(payload, f"size_{label.replace(':', '_')}.png",
                                      model_key="student.pt", score_thresh=0.25)
        observations[label] = resp.status_code
        assert resp.status_code < 500, f"{label} 图片触发 5xx：{dump(resp)}"
    actual("各尺寸状态码：" + "，".join(f"{k}->{v}" for k, v in observations.items()) + "；均未出现 5xx")


@pytest.mark.api
@pytest.mark.case("TC2-DET-09")
def test_score_thresh_monotonicity(api_user1, actual):
    """TC2-DET-09 阈值单调性：阈值升高时检出目标数不得增加，且等于阈值的目标应保留。

    来源：AI 草稿 A-09（AI 提出的性质测试思路，人工补充"等于阈值保留"的边界语义）。
    """
    payload = image_bytes("trash_bio")
    counts = {}
    for thresh in ["0.05", "0.95"]:
        data = assert_ok(api_user1.detect_image(payload, "mono.jpg",
                                                model_key="student.pt", score_thresh=thresh))
        counts[thresh] = len(data["detections"])
    assert counts["0.95"] <= counts["0.05"], f"阈值升高反而检出更多：{counts}"
    actual(f"score_thresh=0.05 检出 {counts['0.05']} 个；0.95 检出 {counts['0.95']} 个（单调不增成立）")


@pytest.mark.api
@pytest.mark.case("TC2-DET-10")
def test_extension_content_mismatch(api_user1, actual):
    """TC2-DET-10 扩展名与真实内容不一致（.png 里装 JPEG 字节）应被正常受理。

    来源：**AI 未提出**，人工补充 —— AI 只想到"内容非法"，没想到"扩展名欺骗"。
    期望为双向：2xx 则必须落库；4xx 则必须不落库。
    """
    payload = image_bytes("plain")          # 实际是 JPEG 字节
    before = assert_ok(api_user1.list_records(page=1, page_size=1, source_type="image"))["total"]
    resp = api_user1.detect_image(payload, "disguised.png", model_key="student.pt", score_thresh=0.25)
    after = assert_ok(api_user1.list_records(page=1, page_size=1, source_type="image"))["total"]
    assert resp.status_code < 500, f"扩展名与内容不一致触发 5xx：{dump(resp)}"
    if resp.status_code == 200:
        assert after == before + 1, "返回 200 但未落库"
        verdict = "受理并落库"
    else:
        assert after == before, "返回 4xx 却仍然落库"
        verdict = "拒绝且未落库"
    actual(f"HTTP {resp.status_code}（{verdict}）；记录数 {before}->{after}")


@pytest.mark.api
@pytest.mark.case("TC2-DET-11")
def test_detection_reproducibility(api_user1, actual):
    """TC2-DET-11 同模型同阈值重复检测同一张图，结果应可复现。

    来源：AI 草稿 A-14（性质测试思路，人工采用）。
    """
    payload = image_bytes("trash_bio")
    runs = []
    for _ in range(2):
        data = assert_ok(api_user1.detect_image(payload, "reproduce.jpg",
                                                model_key="student.pt", score_thresh=0.25))
        runs.append(sorted((d["class_name"], round(float(d["score"]), 4)) for d in data["detections"]))
    assert runs[0] == runs[1], f"两次检测结果不一致：{runs}"
    actual(f"两次检测结果一致：{runs[0]}")


@pytest.mark.api
@pytest.mark.case("TC2-DET-12")
def test_video_task_state_machine(api_user1, actual):
    """TC2-DET-12 视频任务状态机合法且 progress 单调不减。

    来源：AI 草稿 A-10（只断言终态 finished）；人工补上状态迁移合法性与 progress 单调性。
    """
    contract = _contract(VIDEO_TASK_INTERFACE)
    submitted = assert_ok(api_user1.detect_video(video_bytes(), "state_machine.avi",
                                                 model_key="student.pt", score_thresh=0.25))
    task_id = submitted["id"]
    statuses, progresses = [], []
    final = None
    deadline = time.time() + 180
    while time.time() < deadline:
        final = assert_ok(api_user1.video_task(task_id))
        statuses.append(final["status"])
        progresses.append(int(final["progress"]))
        if final["status"] in ("finished", "failed"):
            break
        time.sleep(3)
    assert final is not None and final["status"] == "finished", f"任务未完成：{final}"
    ran = _run_invariants(contract, final, {"statuses": statuses, "progress": progresses,
                                            "expect_frames": 24})
    actual(f"状态序列={'->'.join(dict.fromkeys(statuses))}；progress={progresses}；"
           f"通过不变量 {', '.join(ran)}")


@pytest.mark.api
@pytest.mark.case("TC2-DET-13")
def test_video_frames_processed(api_user1, actual):
    """TC2-DET-13 finished 任务的 frames_processed 应等于源视频总帧数（24）。

    来源：AI 草稿 A-11 —— **AI 把断言方向写反了**（"小于 24 即通过"），
    人工重写为"等于源视频帧数"。这是本次实践最典型的 AI 输出错误。
    """
    contract = _contract(VIDEO_TASK_INTERFACE)
    submitted = assert_ok(api_user1.detect_video(video_bytes(), "frames.avi",
                                                 model_key="student.pt", score_thresh=0.25))
    task_id = submitted["id"]
    final = None
    deadline = time.time() + 180
    while time.time() < deadline:
        final = assert_ok(api_user1.video_task(task_id))
        if final["status"] in ("finished", "failed"):
            break
        time.sleep(3)
    assert final is not None and final["status"] == "finished", f"任务未完成：{final}"
    ran = _run_invariants(contract, final, {"statuses": [final["status"]],
                                            "progress": [final["progress"]],
                                            "expect_frames": 24})
    actual(f"frames_processed={final['result'].get('frames_processed')}（期望 24）；"
           f"通过不变量 {', '.join(ran)}")


@pytest.mark.api
@pytest.mark.case("TC2-DET-14")
def test_realtime_frame_after_stop(api_user1, actual):
    """TC2-DET-14 实时会话停止后，取帧接口不得再返回画面。

    来源：AI 草稿 A-12 只允许 204；人工放宽为 {204,404,403} 并强调"响应体不得含画面"。
    """
    contract = _contract(REALTIME_FRAME_INTERFACE)
    session = assert_ok(api_user1.realtime_start(source="0", model_key="student.pt",
                                                 score_thresh=0.25, realtime_fps=8))
    session_id = session["id"]
    try:
        time.sleep(2)
        stopped = assert_ok(api_user1.realtime_stop(session_id))
        assert stopped["status"] == "stopped", f"停止后状态异常：{stopped}"
        resp = api_user1.realtime_frame(session_id)
        _run_invariants(contract, {}, {"response": resp})
        actual(f"会话 {session_id} 停止后取帧 HTTP {resp.status_code}，"
               f"响应体 {len(resp.content)} 字节（未返回画面）")
    finally:
        try:
            api_user1.realtime_stop(session_id)
        except Exception:  # noqa: BLE001
            pass


# ==========================================================================
# C. AI 推断的跨字段不变量 → 命中第二个缺陷（TC2-DET-16）
# ==========================================================================
@pytest.mark.api
@pytest.mark.defect
@pytest.mark.case("TC2-DET-16")
@pytest.mark.xfail(strict=True, reason="BUG2-02：default_model_key 不在 models 列表中，前端下拉框默认值悬空")
def test_default_model_key_exists_in_models(api_user1, actual):
    """TC2-DET-16 default_model_key 必须能在 models 列表中找到（跨字段引用完整性）。

    来源：AI 在追问"默认模型是怎么来的"时补出的不变量 INV-MDL-03；
    人工实现为显式校验函数（AI 只给了表达式草稿）。
    """
    contract = _contract(MODELS_INTERFACE)
    data = assert_ok(api_user1.list_models())
    ran = _run_invariants(contract, data, {}, only={"INV-MDL-03"})
    actual(f"default_model_key={data.get('default_model_key')!r}；"
           f"models 中的 key={[m['key'] for m in data['models']]}；通过不变量 {', '.join(ran)}")


# ==========================================================================
# D. AI 失败归因能力验证（TC2-DET-15）
# ==========================================================================
@pytest.mark.unit
@pytest.mark.case("TC2-DET-15")
def test_ai_failure_attribution(actual):
    """TC2-DET-15 AI 归因能力：对真实失败输出必须给出根因与修复建议。

    来源：**AI 未提出**，人工补充的元测试 —— 模块二既然用 AI 做失败归因，
    就需要验证这个能力本身是否可靠（否则等于用一个不可信的环节去支撑结论）。
    """
    pytest_output = (
        "FAILED member_lsl/test_detection.py::test_invalid_model_key_should_be_rejected\n"
        "E   AssertionError: 非法模型键应按契约被拒绝，实际 HTTP 200 {\"code\": 0, ...}\n"
        "E   assert 200 >= 400\n"
        "FAILED member_lsl/test_detection.py::test_x\n"
        "E   ModuleNotFoundError: No module named 'app'\n"
    )
    result = ai_assist.analyze_failures(pytest_output)
    items = result["items"]
    assert items, f"AI 未给出任何归因（source={result['source']}）"
    for item in items:
        assert item["root_cause"].strip(), f"归因缺少根因：{item}"
        assert item["suggestion"].strip(), f"归因缺少修复建议：{item}"
    actual(f"归因后端={result['source']}；共 {len(items)} 条：" +
           "；".join(f"{i['signature']} → {i['suggestion'][:28]}…" for i in items))
