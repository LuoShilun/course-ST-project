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


# (场景法1) 创建新记录


#所有字段均正确填写（等价类）
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

#--------------------以下测试样例根据置信度字段做相应测试

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

# 测试置信度传入错误数据类型（非数字），且无法转换为数字
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



# 测试置信度传入错误数据类型（布尔），可以转换为数字，但应报错
@pytest.mark.unit
@pytest.mark.case("TC-REC-08")
def test_creating_confidence_bool_invalid():
   
    data = {
        "detected_type": "trash",
        "confidence": True,
        "is_trash": True
    }
    with pytest.raises(ValueError, match="confidence 必须为 0 到 1 之间的有限数值"):
        _validate_record_fields(data, creating=True)

#---------------------------------------------------以下测试样例针对检测类型字段detected_type做相应测试



# 创建新记录时检测类型为空，应报错
@pytest.mark.unit
@pytest.mark.case("TC-REC-09")
def test_creating_detecting_not_exist():
   
    data = {
        "confidence": 0.5,
        "is_trash": True
    }
    with pytest.raises(ValueError, match="detected_type 必须为 1 到 50 个字符的非空字符串"):
        _validate_record_fields(data, creating=True)


# 创建新记录时检测类型传入空串
@pytest.mark.unit
@pytest.mark.case("TC-REC-10")
def test_creating_detecting_empty_string():
   
    data = {
        "detected_type": "",
        "confidence": 0.5,
        "is_trash": True
    }
    with pytest.raises(ValueError, match="detected_type 必须为 1 到 50 个字符的非空字符串"):
        _validate_record_fields(data, creating=True)

# 针对检测类型字符串的长度做检测


# detected_type长度为最小合法边界值1
@pytest.mark.unit
@pytest.mark.case("TC-REC-11")
def test_creating_detecting_min_string():
    data = {
        "detected_type": "a",
        "confidence": 0.5,
        "is_trash": True
    }
    creating = True
    result = _validate_record_fields(data, creating=creating)
    assert result == {
        "detected_type": "a",
        "confidence": 0.5,
        "is_trash": True
    }
  
    

# detected_type长度为最大合法边界值50
@pytest.mark.unit
@pytest.mark.case("TC-REC-12")
def test_creating_detecting_max_string():
    data = {
        "detected_type": "a"*50,
        "confidence": 0.5,
        "is_trash": True
    }
    creating = True
    result = _validate_record_fields(data, creating=creating)
    assert result == {
        "detected_type": "a"*50,
        "confidence": 0.5,
        "is_trash": True
    }

# detected_type长度超过50 
@pytest.mark.unit
@pytest.mark.case("TC-REC-13")
def test_creating_detecting_over_string():
    data = {
        "detected_type": "a"*51,
        "confidence": 0.5,
        "is_trash": True
    }
    with pytest.raises(ValueError, match="detected_type 必须为 1 到 50 个字符的非空字符串"):
        _validate_record_fields(data, creating=True)


# is_trash 传入非布尔值
@pytest.mark.unit
@pytest.mark.case("TC-REC-14")
def test_creating_trash_not_bool():
    data = {
      "detected_type": "trash",
      "confidenct": 0.5,
      "is_trash":1
    }
    creating = True
    with pytest.raises(ValueError, match="is_trash 必须为 JSON 布尔值 true 或 false"):
        _validate_record_fields(data, creating=True)



@pytest.mark.unit
@pytest.mark.case("TC-REC-15")
def test_updating_none():
    data = {
    }
    creating = False
    with pytest.raises(ValueError, match="更新时传入data不能为空"):
        _validate_record_fields(data, creating=False)