# 模块二 · 检测模块自动化测试（罗时伦）

被测对象：检测页面 `/detect` 及其后端接口 `/api/detection/*`。
方案：**方案2「AI测」**——用 AI 辅助生成/补全用例、推断期望、归因失败，人工审校后固化本目录。
本目录只包含检测模块的测试代码，不涉及检测记录模块。

## 运行

**必须先进入 `module2` 目录再执行。** `pytest.ini` 位于 `module2/`，pytest 只从"参数所在目录"向上查找配置。

```bash
cd module2
python -m pytest member_lsl -v          # 本模块全部用例
python -m pytest member_lsl -m api      # 只跑接口层
python -m pytest member_lsl -m ai       # 只跑 AI 辅助生成的用例（模块二标记）
python -m pytest member_lsl -m unit     # 只跑单元测试
```

## 文件

| 文件 | 说明 |
|---|---|
| `test_detection.py` | 检测模块全部用例（**骨架，待补充**） |

## 用例清单（规划中，待补充）

模块二要求：**≥15 条 AI 相关用例、≥1 个缺陷**。下表为待补充的用例规划占位，编号建议用 `TC2-DET-xx` 前缀以区别于模块一。

| 用例编号 | 用例标题 | 设计方法 | AI 参与方式 | 备注 |
|---|---|---|---|---|
| TC2-DET-01 | 待填 | 待填 | 用例生成 / 期望推断 / 失败归因 | |

> 骨架阶段 `test_detection.py` 以模块级 `pytest.skip` 占位，补全用例后请删除该行。
> 接口与 UI 基础设施见 `../common/`；缺陷确认用例请用 `@pytest.mark.xfail(strict=True, reason="BUG-xx ...")`。
