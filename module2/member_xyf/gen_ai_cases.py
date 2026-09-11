# -*- coding: utf-8 -*-
"""生成模块二 · 检测记录模块（member_xyf）的用例目录与测试数据快照。

用法（在 module2 目录下）：

    python member_xyf/gen_ai_cases.py

会在本目录生成 ``ai_cases.json``：包含 15 条用例的目录（编号/标题/侧重）
以及由 ``common.ai_assist`` 提供的测试数据样本。整个过程离线、确定性。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 让脚本无论从哪个目录运行都能 import 到 module2/common
MODULE2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE2_ROOT))

from common import ai_assist  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent / "ai_cases.json"


def main() -> None:
    payload = ai_assist.generate_cases("records")
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写出 {OUT_PATH}（{payload['case_count']} 条用例）")


if __name__ == "__main__":
    main()
