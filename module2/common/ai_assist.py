# -*- coding: utf-8 -*-
"""模块二（方案2「AI测」）· 检测记录模块的 AI 辅助测试数据与用例目录。

被测对象（唯一）：``web_system/backend/app/api/records.py`` 的
``_validate_record_fields(data, *, creating)``。

AI 在模块二中承担"批量生成/枚举测试数据、产出用例草稿"的角色；本文件集中存放：

  1. **生成的测试数据**（按侧重分组，供 ``member_xyf/test_records.py`` 逐条断言具体预期）；
  2. **用例目录**（``CASE_CATALOG`` / ``generate_cases``，供报告附录与 ``ai_cases.json``）。

准则：预期**只依据源码与该函数的字段契约推断**，不引入契约之外的假设；
数据与用例均为离线、确定性的，不依赖网络或大模型密钥。
"""
from __future__ import annotations

from typing import Any

# 被测对象与其字段契约（用例预期的唯一依据）
TARGET = "app.api.records._validate_record_fields"
FIELD_CONTRACT: dict[str, str] = {
    "detected_type": "字符串，strip() 后长度必须落在 [1, 50]",
    "confidence": "数值（非 bool），必须有限且落在 [0.0, 1.0]；数字字符串可被接受",
    "is_trash": "必须是 JSON 布尔值 true / false（Python bool）",
}


class AIAssistUnavailable(RuntimeError):
    """未配置可用的（真实）AI 后端时抛出。本地实现不使用它。"""


# --------------------------------------------------------------------------
# 一、生成的测试数据（按侧重分组）
# --------------------------------------------------------------------------
#: detected_type 类型检查：非字符串一律应拒绝
NON_STRING_DETECTED_TYPES: list[Any] = [123, 0, None, [], {}, ("t",), b"trash", 4.5]

#: detected_type 空白检查：strip() 后为空，应拒绝
BLANK_DETECTED_TYPES: list[str] = ["", "   ", "\t", "\n", "  \t\n ", "\r\n"]

#: detected_type 非 ASCII 正常值：按"字符数"计长，应通过并原样返回
NON_ASCII_DETECTED_TYPES: list[str] = ["水下垃圾", "垃圾" * 16, "Trash·垃圾"]

#: confidence 数字字符串：应被 float() 转换为对应数值
NUMERIC_STRING_CONFIDENCE: list[str] = ["0.5", "1e0", " 0.5 ", ".5", "0.50"]

#: confidence 非数字字符串：无法转换，应拒绝
NON_NUMERIC_STRING_CONFIDENCE: list[str] = ["abc", "", "0.5.6", "0,5", "½"]

#: confidence 整数（数值）应通过；布尔应拒绝（bool 虽可转 1.0/0.0）
VALID_INT_CONFIDENCE: list[int] = [0, 1]
REJECTED_BOOL_CONFIDENCE: list[bool] = [True, False]

#: confidence 越界值：应拒绝
OUT_OF_RANGE_CONFIDENCE: list[Any] = [-0.1, 1.1, -1.0, 2.0]

#: is_trash 非布尔：应拒绝
IS_TRASH_NON_BOOL: list[Any] = [1, 0, "true", "false", None, [], {}]


# --------------------------------------------------------------------------
# 二、用例目录（15 条，每条一个侧重）
# --------------------------------------------------------------------------
CASE_CATALOG: list[dict[str, str]] = [
    {"case_id": "TC2-REC-01", "title": "detected_type 类型检查：非字符串一律拒绝",
     "focus": "detected_type 必须为 str"},
    {"case_id": "TC2-REC-02", "title": "detected_type 纯空白串应拒绝",
     "focus": "strip 后长度为 0"},
    {"case_id": "TC2-REC-03", "title": "detected_type 首尾空白应被去除后写回",
     "focus": "返回值 = value.strip()"},
    {"case_id": "TC2-REC-04", "title": "detected_type 长度上界：50 通过 / 51 拒绝",
     "focus": "len <= 50"},
    {"case_id": "TC2-REC-05", "title": "detected_type 长度下界：1 通过 / 0 拒绝",
     "focus": "len >= 1"},
    {"case_id": "TC2-REC-06", "title": "detected_type 非 ASCII：按字符计长且内容原样返回",
     "focus": "多字节字符"},
    {"case_id": "TC2-REC-07", "title": "confidence 数字字符串被转换为对应数值",
     "focus": "float() 转换"},
    {"case_id": "TC2-REC-08", "title": "confidence 非数字字符串应拒绝",
     "focus": "转换失败分支"},
    {"case_id": "TC2-REC-09", "title": "confidence 整数 0/1 通过、布尔 True/False 拒绝",
     "focus": "int 与 bool 的分界"},
    {"case_id": "TC2-REC-10", "title": "confidence 越界值（-0.1 / 1.1 / -1 / 2）应拒绝",
     "focus": "区间 [0, 1]"},
    {"case_id": "TC2-REC-11", "title": "confidence 返回类型恒为 float",
     "focus": "返回类型契约"},
    {"case_id": "TC2-REC-12", "title": "is_trash 非布尔（1/0/\"true\"/None/[]）应拒绝",
     "focus": "严格 bool"},
    {"case_id": "TC2-REC-13", "title": "is_trash 合法 True/False 通过并原样返回",
     "focus": "布尔往返"},
    {"case_id": "TC2-REC-14", "title": "update 模式同样校验传入字段（非法值拒绝）",
     "focus": "update 也执行字段校验"},
    {"case_id": "TC2-REC-15", "title": "update 模式只回传传入的字段",
     "focus": "create 与 update 的字段范围差异"},
]


def _jsonable(values: list[Any]) -> list[Any]:
    """把样本值转为 JSON 可序列化形式（bytes/元组等非原始类型用 repr 表示）。"""
    out: list[Any] = []
    for value in values:
        if value is None or isinstance(value, (str, int, float, bool)):
            out.append(value)
        elif isinstance(value, (list, tuple)):
            out.append(list(value))
        elif isinstance(value, dict):
            out.append(dict(value))
        else:
            out.append(repr(value))
    return out


def generate_cases(target: str = "records") -> dict[str, Any]:
    """产出用例目录 + 生成的测试数据样本（供报告附录与 ai_cases.json）。"""
    return {
        "generated_by": "common/ai_assist.py::generate_cases",
        "target": TARGET if target == "records" else target,
        "field_contract": FIELD_CONTRACT,
        "case_count": len(CASE_CATALOG),
        "cases": [dict(c) for c in CASE_CATALOG],
        "sample_data": {
            "non_string_detected_types": _jsonable(NON_STRING_DETECTED_TYPES),
            "blank_detected_types": _jsonable(BLANK_DETECTED_TYPES),
            "non_ascii_detected_types": _jsonable(NON_ASCII_DETECTED_TYPES),
            "numeric_string_confidence": _jsonable(NUMERIC_STRING_CONFIDENCE),
            "non_numeric_string_confidence": _jsonable(NON_NUMERIC_STRING_CONFIDENCE),
            "valid_int_confidence": _jsonable(VALID_INT_CONFIDENCE),
            "rejected_bool_confidence": _jsonable(REJECTED_BOOL_CONFIDENCE),
            "out_of_range_confidence": _jsonable(OUT_OF_RANGE_CONFIDENCE),
            "is_trash_non_bool": _jsonable(IS_TRASH_NON_BOOL),
        },
    }


def _client() -> Any:
    """可选的真实 LLM 客户端接入点（默认关闭）。

    如需让 LLM 真正参与生成：设置 ``MODULE2_AI_BACKEND`` 并注入对应密钥的环境变量，
    在这里按厂商 SDK 实现即可。密钥一律走环境变量，不要写进仓库。
    """
    raise AIAssistUnavailable(
        "未配置真实 AI 后端（MODULE2_AI_BACKEND 为空）；本模块默认走离线实现，"
        "无需 LLM 即可运行。"
    )
