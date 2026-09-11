# -*- coding: utf-8 -*-
"""模块二（方案2「AI测」）· AI 辅助测试的接入点（骨架 / 待实现）。

模块一禁用 AI 生成用例；模块二（AI 融合）允许并鼓励用 AI 辅助测试。
本文件是"AI 如何参与测试"的唯一接入点，保持与具体大模型解耦，供两位成员共用。

典型的"AI 测"用法（三选一或组合，按最终方案取舍）：
  A. 用例生成：把被测函数签名/接口文档交给 LLM，批量产出等价类、边界值、场景用例草稿，
     人工审校后落到各 member_*/test_*.py。→ 用 ``generate_cases()``。
  B. 断言/期望生成：让 LLM 依据接口契约推断"合理期望"，与真实响应比对，检出语义级缺陷。
     → 用 ``infer_expectation()``。
  C. 缺陷聚类/失败归因：把 pytest 失败输出交给 LLM 归类、给出疑似根因与修复建议。
     → 用 ``analyze_failures()``。

设计约束：
  * 本文件不硬编码任何 API Key / 模型厂商；密钥一律走环境变量，缺失时抛
    ``AIAssistUnavailable``，由调用方决定 skip 还是失败，避免 CI 无密钥即崩。
  * 任何 AI 产物都应视为"待人工审校的草稿"，不得直接作为判定被测系统正确性的唯一依据。
"""
from __future__ import annotations

import os
from typing import Any


class AIAssistUnavailable(RuntimeError):
    """未配置可用的 AI 后端（缺少 SDK 或密钥）时抛出。"""


# --- 后端选择：按实际选型实现其中一个即可 -------------------------------------
# 候选一：复用被测系统自带的 AI 能力（web_system/backend 的 assistant_service/ChatDocUtil）
# 候选二：外部 LLM，如 OPENAI_API_KEY / DASHSCOPE_API_KEY / SPARK_* 等环境变量
AI_BACKEND = os.getenv("MODULE2_AI_BACKEND", "")   # e.g. "system" | "openai" | "dashscope"


def _client() -> Any:
    raise AIAssistUnavailable(
        "尚未配置 AI 后端：请在 common/ai_assist.py 中按选定方案实现 _client()，"
        "并通过环境变量注入密钥（不要把 Key 写进仓库）。"
    )


def generate_cases(target: str, *, method: str = "boundary", n: int = 10) -> list[dict[str, Any]]:
    """[待实现] 依据被测对象描述生成用例草稿。

    返回形如 ``[{"case_id": "TC2-DET-01", "title": ..., "input": ..., "expected": ...}, ...]``。
    产物需人工审校后再固化为 member_*/test_*.py 中的真实用例。
    """
    raise AIAssistUnavailable("generate_cases() 待实现，见本文件模块说明。")


def infer_expectation(interface: str, request: dict[str, Any]) -> dict[str, Any]:
    """[待实现] 让 LLM 依据接口契约推断该请求的"合理期望响应"，用于语义级断言。"""
    raise AIAssistUnavailable("infer_expectation() 待实现，见本文件模块说明。")


def analyze_failures(pytest_output: str) -> str:
    """[待实现] 对 pytest 失败输出做归因分析，返回疑似根因与修复建议文本。"""
    raise AIAssistUnavailable("analyze_failures() 待实现，见本文件模块说明。")
