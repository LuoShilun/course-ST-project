# 模块二 · 检测模块自动化测试（罗时伦）

被测对象：检测页面 `/detect` 及其后端接口 `/api/detection/*`。

方案：用 AI 辅助生成用例草稿、推断接口契约不变量、归因失败，人工审校后固化本目录。

## 运行

**必须先进入 `module2` 目录再执行**（`pytest.ini` 位于 `module2/`）：

```bash
cd module2
python -m pytest member_lsl -v          # 本模块全部 16 条用例
python -m pytest member_lsl -m ai       # 只跑 AI 相关用例（本模块全部）
python -m pytest member_lsl -m api      # 只跑接口层
python -m pytest member_lsl -m unit     # 只跑单元/元测试
python -m pytest member_lsl -m defect   # 只跑缺陷确认用例
```

## 文件

| 文件 | 说明 |
|---|---|
| `test_detection.py` | 检测模块全部 16 条用例（TC2-DET-01 ~ TC2-DET-16），全部标记 `@pytest.mark.ai` |
| `ai_case.json` | AI 原始用例（15 条）＋ 逐条人工审校结论 |

## 用例清单

用例编号 `TC2-DET-xx` 以区别模块一的 `TC-DET-xx`；

| 用例编号 | 用例标题 | 设计方法 | AI 参与方式 | 结果 |
|---|---|---|---|---|
| TC2-DET-01 | 模型列表满足 AI 推断的契约（engine 受控词表 + size_mb 为正） | 等价类划分 | AI 生成草稿 A-01，人工补 2 个字段与词表 | OK |
| TC2-DET-02 | 检测响应的 summary 统计与 detections 逐项一致 | 等价类划分 | AI 生成草稿 A-05，直接采用 | OK |
| TC2-DET-03 | 返回的原图与标注图可 base64 解码且尺寸一致 | 等价类划分 | AI 草稿 A-02/A-13 合并，弱断言改真解码 | OK |
| TC2-DET-04 | 置信度在 [0,1] 且类别与垃圾标记语义一致 | 等价类划分 | AI 草稿 A-03 ＋人工补交叉约束 | OK |
| TC2-DET-05 | 目标框坐标几何合法且不越界 | 边界值分析 | AI 草稿 A-04，人工补几何范围 | OK |
| TC2-DET-06 | 传入不存在的 model_key 应按契约返回 4xx | 错误推测法 | AI 期望推断（草稿 A-06） | **NG → BUG2-01** |
| TC2-DET-07 | score_thresh 非数值字符串形态不应导致 5xx | 边界值分析 | AI 草稿 A-07，人工修正输入形态 | OK |
| TC2-DET-08 | 极小尺寸与极端宽高比图片不应导致 5xx | 边界值分析 | AI 草稿 A-08 ＋人工补 4:1 长条图 | OK |
| TC2-DET-09 | 阈值单调性：阈值升高时检出数不得增加 | 性质测试 | AI 草稿 A-09（AI 提出的性质测试思路） | OK |
| TC2-DET-10 | 扩展名与真实内容不一致时行为应自洽 | 错误推测法 | **人工补充**（AI 未提出） | OK |
| TC2-DET-11 | 同模型同阈值重复检测结果应可复现 | 性质测试 | AI 草稿 A-14 | OK |
| TC2-DET-12 | 视频任务状态机合法且 progress 单调不减 | 场景法 | AI 期望推断（草稿 A-10）＋人工补单调性 | OK |
| TC2-DET-13 | 完成的视频任务 frames_processed 等于源视频帧数 | 边界值分析 | AI 草稿 A-11 **断言方向写反**，人工重写 | OK |
| TC2-DET-14 | 实时会话停止后取帧不得再返回画面 | 场景法 | AI 期望推断（草稿 A-12），人工放宽状态码 | OK |
| TC2-DET-15 | AI 失败归因能力：必须给出根因与修复建议 | 元测试 | **人工补充**（验证 AI 归因本身是否可靠） | OK |
| TC2-DET-16 | default_model_key 必须能在 models 列表中找到 | 等价类划分 | **AI 推断的跨字段不变量** INV-MDL-03 | **NG → BUG2-02** |

结果统计：**16 条用例，通过 14 条，缺陷确认 2 条**（均为 `xfail(strict=True)`，缺陷修复后会自动转为失败以提醒更新预期）。

## 实现要点

- **断言集合由AI契约驱动**：用例先调用 `ai_assist.infer_expectation()` 取回 AI 推断的必填字段与不变量
  （如 `INV-IMG-01` summary 计数一致、`INV-MDL-03` 默认模型键引用完整性），再逐条执行
  `INVARIANT_CHECKS` 中**人工编写**的校验函数；
- **运行期不 eval AI 产出的表达式**：AI 给的 `ai_expression` 只作为溯源留档，
  实现一律是显式 Python 函数，避免执行不可信字符串；
- **同一条契约的不同不变量可拆到不同用例**：`_run_invariants(..., skip=/only=)` 让已确认失败的不变量
  单独做成缺陷确认用例（TC2-DET-16），不影响其余用例判定；
- **双后端**：配置 `MODULE2_AI_BACKEND=dashscope` + `DASHSCOPE_API_KEY` 时自动走真实 LLM，
  否则回放 `common/ai_artifacts/*.json`，同一批用例无需改动。
