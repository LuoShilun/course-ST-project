# -*- coding: utf-8 -*-
"""模块二（方案2「AI测」）· 检测记录模块自动化测试（肖云峰）

被测对象（唯一）：``web_system/backend/app/api/records.py`` 的
``_validate_record_fields(data, *, creating)``。

准则：**只依据源码与 `common.ai_assist.FIELD_CONTRACT` 推断预期**，不引入二者之外的需求假设；
且每条用例只针对一个"侧重"，避免同义反复、保证判别力（改错源码对应分支即应失败）。

测试数据由 ``common.ai_assist`` 批量生成/枚举，用例据此断言**具体**预期结果。
全部用例离线可复现，不需要后端服务与数据库。
"""
from __future__ import annotations

import pytest

from common import ai_assist


@pytest.fixture(scope="module")
def validate():
    """加载被测函数；后端源码/依赖不可用时本模块统一跳过，而不是让整场报错。"""
    try:
        from app.api.records import _validate_record_fields
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"无法导入被测函数 _validate_record_fields：{exc}")
    return _validate_record_fields


def _valid_base(**overrides):
    """三字段齐全的合法请求体，用于"只改动一个字段"的用例，确保拒绝只由被测字段引起。"""
    base = {"detected_type": "trash", "confidence": 0.5, "is_trash": True}
    base.update(overrides)
    return base


# ==========================================================================
# 一、detected_type 字段校验（TC2-REC-01 ~ 06）
# ==========================================================================
@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-01")
def test_detected_type_rejects_non_string(validate, actual):
    """侧重：detected_type 的类型检查——非字符串一律拒绝。"""
    for value in ai_assist.NON_STRING_DETECTED_TYPES:
        with pytest.raises(ValueError):
            validate(_valid_base(detected_type=value), creating=True)
    actual(f"{len(ai_assist.NON_STRING_DETECTED_TYPES)} 种非字符串输入均被拒绝")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-02")
def test_detected_type_rejects_blank_only(validate, actual):
    """侧重：纯空白串应在 strip 后判为"空"而被拒绝。"""
    for value in ai_assist.BLANK_DETECTED_TYPES:
        with pytest.raises(ValueError):
            validate(_valid_base(detected_type=value), creating=True)
    actual(f"{len(ai_assist.BLANK_DETECTED_TYPES)} 种纯空白输入均被拒绝")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-03")
def test_detected_type_is_stripped(validate, actual):
    """侧重：detected_type 的首尾空白应被去除后写回。"""
    out = validate(_valid_base(detected_type="  trash  "), creating=True)
    assert out["detected_type"] == "trash"
    actual(f"输入 '  trash  '，返回值 detected_type='{out['detected_type']}'")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-04")
def test_detected_type_length_upper_bound(validate, actual):
    """侧重：detected_type 长度上界——恰好 50 通过、51 拒绝。"""
    out = validate(_valid_base(detected_type="a" * 50), creating=True)
    assert out["detected_type"] == "a" * 50
    with pytest.raises(ValueError):
        validate(_valid_base(detected_type="a" * 51), creating=True)
    actual("长度 50 通过、51 拒绝")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-05")
def test_detected_type_length_lower_bound(validate, actual):
    """侧重：detected_type 长度下界——恰好 1 通过、0 拒绝。"""
    out = validate(_valid_base(detected_type="a"), creating=True)
    assert out["detected_type"] == "a"
    with pytest.raises(ValueError):
        validate(_valid_base(detected_type=""), creating=True)
    actual("长度 1 通过、0（空串）拒绝")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-06")
def test_detected_type_non_ascii(validate, actual):
    """侧重：多字节字符按"字符数"计长且内容不被破坏（非 ASCII 正常通过）。"""
    for value in ai_assist.NON_ASCII_DETECTED_TYPES:
        out = validate(_valid_base(detected_type=value), creating=True)
        assert out["detected_type"] == value
    actual(f"{len(ai_assist.NON_ASCII_DETECTED_TYPES)} 个非 ASCII 样本原样通过")


# ==========================================================================
# 二、confidence 字段校验（TC2-REC-07 ~ 11）
# ==========================================================================
@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-07")
def test_confidence_accepts_numeric_string(validate, actual):
    """侧重：数字字符串应被 float() 转换后接受，返回值等于其数值。"""
    for value in ai_assist.NUMERIC_STRING_CONFIDENCE:
        out = validate(_valid_base(confidence=value), creating=True)
        assert out["confidence"] == float(value), f"{value!r} 应转换为 {float(value)}"
    actual(f"{len(ai_assist.NUMERIC_STRING_CONFIDENCE)} 个数字字符串均被转换为对应数值")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-08")
def test_confidence_rejects_non_numeric_string(validate, actual):
    """侧重：非数字字符串无法转换，应被拒绝。"""
    for value in ai_assist.NON_NUMERIC_STRING_CONFIDENCE:
        with pytest.raises(ValueError):
            validate(_valid_base(confidence=value), creating=True)
    actual(f"{len(ai_assist.NON_NUMERIC_STRING_CONFIDENCE)} 个非数字字符串均被拒绝")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-09")
def test_confidence_int_ok_but_bool_rejected(validate, actual):
    """侧重：int 与 bool 的分界——整数 0/1 通过，布尔 True/False 即使可转 1.0/0.0 也拒绝。"""
    for value in ai_assist.VALID_INT_CONFIDENCE:
        out = validate(_valid_base(confidence=value), creating=True)
        assert out["confidence"] == float(value)
    for value in ai_assist.REJECTED_BOOL_CONFIDENCE:
        with pytest.raises(ValueError):
            validate(_valid_base(confidence=value), creating=True)
    actual("整数 0/1 通过；布尔 True/False 被拒绝")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-10")
def test_confidence_rejects_out_of_range(validate, actual):
    """侧重：confidence 的取值区间 [0, 1]——越界值一律拒绝。"""
    for value in ai_assist.OUT_OF_RANGE_CONFIDENCE:
        with pytest.raises(ValueError):
            validate(_valid_base(confidence=value), creating=True)
    actual(f"{len(ai_assist.OUT_OF_RANGE_CONFIDENCE)} 个越界值均被拒绝")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-11")
def test_confidence_return_type_is_float(validate, actual):
    """侧重：confidence 的返回类型恒为 float（数值 0.5 与字符串 '0.5' 皆然）。"""
    for value in (0.5, "0.5"):
        out = validate(_valid_base(confidence=value), creating=True)
        assert type(out["confidence"]) is float, f"{value!r} 应返回 float"
    actual("0.5 与 '0.5' 的返回值类型均为 float")


# ==========================================================================
# 三、is_trash 字段校验（TC2-REC-12 ~ 13）
# ==========================================================================
@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-12")
def test_is_trash_rejects_non_bool(validate, actual):
    """侧重：is_trash 必须是 JSON 布尔值——1/0/"true"/None/[] 等一律拒绝。"""
    for value in ai_assist.IS_TRASH_NON_BOOL:
        with pytest.raises(ValueError):
            validate(_valid_base(is_trash=value), creating=True)
    actual(f"{len(ai_assist.IS_TRASH_NON_BOOL)} 种非布尔输入均被拒绝")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-13")
def test_is_trash_accepts_bool(validate, actual):
    """侧重：is_trash 合法布尔 True/False 通过并原样返回。"""
    for value in (True, False):
        out = validate(_valid_base(is_trash=value), creating=True)
        assert out["is_trash"] is value
    actual("True/False 均通过并原样返回")


# ==========================================================================
# 四、create / update 模式差异（TC2-REC-14 ~ 15）
# ==========================================================================
@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-14")
def test_update_mode_validates_given_fields(validate, actual):
    """侧重：update 模式同样校验请求体中出现的字段（非法值仍被拒绝）。"""
    with pytest.raises(ValueError):
        validate({"confidence": "abc"}, creating=False)
    with pytest.raises(ValueError):
        validate({"detected_type": 123}, creating=False)
    actual("update 传入非法 confidence / detected_type 均被拒绝")


@pytest.mark.unit
@pytest.mark.ai
@pytest.mark.case("TC2-REC-15")
def test_update_mode_returns_only_given_fields(validate, actual):
    """侧重：update 模式只校验并回传请求体中出现的字段。"""
    assert validate({"confidence": 0.5}, creating=False) == {"confidence": 0.5}
    assert validate({"detected_type": "trash"}, creating=False) == {"detected_type": "trash"}
    assert validate({"is_trash": False}, creating=False) == {"is_trash": False}
    actual("仅传入的字段被回传，未传入的不出现在返回值中")
