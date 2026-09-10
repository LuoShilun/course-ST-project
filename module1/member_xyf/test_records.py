# -*- coding: utf-8 -*-

from __future__ import annotations

import pytest

from common.api_client import raw_request, dump
from common.assertions import assert_ok, assert_error
from common.paths import USER_ROBOT

from app.api.records import _validate_record_fields


def _payload(**overrides) -> dict:
    """构造创建/更新记录的默认合法请求体，可按需覆盖字段。"""
    base = {"detected_type": "trash", "confidence": 0.5, "is_trash": True}
    base.update(overrides)
    return base


def _list_ids(client, **params) -> set[int]:
    """查询列表并返回首屏（page_size=100）所有记录 id 集合。"""
    data = assert_ok(client.list_records(page=1, page_size=100, **params))
    return {item["id"] for item in data["items"]}


# --------------------------------------------------------------------- 以下样例针对api/records.py 中的字段校验函数_validate_record_fields做单元测试


# (场景法) 创建新记录时，所有字段均正确填写（等价类）

"""创建记录：所有字段合法，detected_type 首尾空格自动去除"""
@pytest.mark.unit
@pytest.mark.case("TC-REC-01")
def test_creating_valid():
    
    data = {
        "detected_type": "  trash  ",
        "confidence": 0.5,
        "is_trash": True
    }
    creating = True
    result = _validate_record_fields(data, creating=creating)
    assert result == {
        "detected_type": "trash",
        "confidence": 0.5,
        "is_trash": True
    }


# 根据置信度在0~1范围内，分别测试<0,0,1,>1四种情况，对应两种合法临界值和两种非法情况（边界值法）


@pytest.mark.unit
@pytest.mark.case("TC-REC-02")
def test_creating_confidence_less_than_zero():
    """创建模式：confidence <0（-0.1），非法抛异常"""
    data = {
        "detected_type": "trash",
        "confidence": -0.1,
        "is_trash": True
    }
    with pytest.raises(ValueError, match="confidence 必须为 0 到 1 之间的有限数值"):
        _validate_record_fields(data, creating=True)


@pytest.mark.unit
@pytest.mark.case("TC-REC-03")
def test_creating_confidence_equal_zero():
    """创建模式：confidence =0，合法边界下限"""
    data = {
        "detected_type": "trash",
        "confidence": 0.0,
        "is_trash": True
    }
    result = _validate_record_fields(data, creating=True)
    assert result == {
        "detected_type": "trash",
        "confidence": 0.0,
        "is_trash": True
    }


@pytest.mark.unit
@pytest.mark.case("TC-REC-04")
def test_creating_confidence_equal_one():
    """创建模式：confidence =1，合法边界上限"""
    data = {
        "detected_type": "trash",
        "confidence": 1.0,
        "is_trash": True
    }
    result = _validate_record_fields(data, creating=True)
    assert result == {
        "detected_type": "trash",
        "confidence": 1.0,
        "is_trash": True
    }


@pytest.mark.unit
@pytest.mark.case("TC-REC-05")
def test_creating_confidence_greater_than_one():
    data = {
        "detected_type": "trash",
        "confidence": 1.1,
        "is_trash": True
    }
    with pytest.raises(ValueError, match="confidence 必须为 0 到 1 之间的有限数值"):
        _validate_record_fields(data, creating=True)


# 测试置信度传入数字串能否正常转换
@pytest.mark.unit
@pytest.mark.case("TC-REC-06")
def test_creating_confidence_str_number_valid():
    """置信度：传入数字字符串"0.5"，可正常转为float，校验通过"""
    data = {
        "detected_type": "trash",
        "confidence": "0.5",
        "is_trash": True
    }
    result = _validate_record_fields(data, creating=True)
    assert result == {
        "detected_type": "trash",
        "confidence": 0.5,
        "is_trash": True
    }

# 测试置信度传入错误数据类型，且无法转换
@pytest.mark.unit
@pytest.mark.case("TC-REC-07")
def test_creating_confidence_str_non_number_invalid():
   
    data = {
        "detected_type": "trash",
        "confidence": "abc",
        "is_trash": True
    }
    with pytest.raises(ValueError, match="confidence 必须为 0 到 1 之间的有限数值"):
        _validate_record_fields(data, creating=True)





