# 模块二 · 检测记录模块自动化测试（肖云峰）

被测对象（唯一）：`web_system/backend/app/api/records.py` 中的
`_validate_record_fields(data, *, creating)`。
方案：**方案2「AI测」**——由 AI 批量生成/枚举测试数据并产出用例草稿，人工审校后固化为本目录。

**测试准则：只依据源码与 `common.ai_assist.FIELD_CONTRACT` 推断预期，不引入二者之外的假设；
每条用例只针对一个"侧重"，保证判别力（改错源码对应分支即应失败），不做同义反复、不测浮点数的性质。**

## 运行

**必须先进入 `module2` 目录再执行。**

```powershell
cd C:\Users\Lenovo\Desktop\test\st1\course-ST-project\module2

pytest member_xyf -v                # 本模块全部用例（15 条）
pytest member_xyf -m ai -v          # 只跑"AI 参与"的用例（本模块全部）
pytest member_xyf -m unit           # 只跑单元层（本模块全部）
pytest member_xyf -k detected_type  # 按用例名关键字执行

python member_xyf/gen_ai_cases.py   # 生成 ai_cases.json（用例目录 + 测试数据快照）
```

在仓库根目录也可用 `pytest module2/member_xyf`（把路径作为参数传入，pytest 便能向上找到 `module2/pytest.ini`）。

## 环境与依赖

| 项 | 说明 |
|---|---|
| Python | 3.12+ |
| pytest | ≥ 7.0 |
| 依赖 | `pip install -r ../requirements.txt`（本模块只用标准库 + pytest，不需要额外依赖） |
| 后端服务 | **不需要**（纯单元测试，直接 import 被测函数） |
| MySQL | **不需要** |
| 网络 / LLM Key | **不需要**（离线实现；见下节"AI 参与方式"） |

## 文件

| 文件 | 说明 |
|---|---|
| `test_records.py` | 15 条用例，每条针对一个侧重 |
| `gen_ai_cases.py` | 生成器脚本：产出 `ai_cases.json` |
| `ai_cases.json` | 生成产物（运行脚本后出现）：用例目录 + 生成数据样本 |

## 与模块一（人工用例）的差异

| 维度 | 模块一（人工） | 模块二（AI 测） |
|---|---|---|
| 用例来源 | 人工逐条设计 | AI 批量生成/枚举数据与用例草稿，人工审校固化 |
| 测试数据 | 人工手写 | `common/ai_assist.py` 集中生成（按侧重分组） |
| 用例组织 | 按测试层级（接口/UI/单元） | 按**字段/侧重**组织，一条只测一点 |
| 预期依据 | 人工判断 | 仅源码 + `FIELD_CONTRACT` |
| 可复现性 | 固定用例 | 数据为确定性的枚举集合，逐条断言具体预期 |

## 用例清单（15 条）

| 编号 | 侧重（只测这一点） | 输入 → 预期 |
|---|---|---|
| TC2-REC-01 | detected_type 是否为字符串 | 123/None/[]/{}/b"trash"/4.5 → 拒绝 |
| TC2-REC-02 | detected_type 是否纯空白 | `""`/`"   "`/`"\t\n"` → 拒绝 |
| TC2-REC-03 | detected_type 是否去空白写回 | `"  trash  "` → 返回 `"trash"` |
| TC2-REC-04 | detected_type 长度上界 | 50 → 通过；51 → 拒绝 |
| TC2-REC-05 | detected_type 长度下界 | 1 → 通过；0 → 拒绝 |
| TC2-REC-06 | detected_type 非 ASCII 处理 | 中文按其字符数计长、内容原样返回 |
| TC2-REC-07 | confidence 数字字符串转换 | `"0.5"`/`"1e0"`/`".5"` → 通过，返回对应数值 |
| TC2-REC-08 | confidence 非数字字符串 | `"abc"`/`""`/`"0.5.6"` → 拒绝 |
| TC2-REC-09 | confidence 的 int / bool 分界 | `0`/`1` 通过；`True`/`False` 拒绝 |
| TC2-REC-10 | confidence 取值区间 | `-0.1`/`1.1`/`-1`/`2` → 拒绝 |
| TC2-REC-11 | confidence 返回类型 | 数值与字符串均返回 `float` |
| TC2-REC-12 | is_trash 是否严格布尔 | `1`/`0`/`"true"`/`None`/`[]` → 拒绝 |
| TC2-REC-13 | is_trash 合法布尔往返 | `True`/`False` → 通过并原样返回 |
| TC2-REC-14 | update 模式是否校验传入字段 | `{"confidence":"abc"}` → 拒绝 |
| TC2-REC-15 | update 模式的字段范围 | 只回传传入的字段 |

> 预期全部为**通过**：该函数忠实实现了上述契约，未发现契约级缺陷。
> 每条的判别力在于——只要源码里对应的那个判断被改错（如把 `<= 50` 写成 `< 50`、去掉 `isinstance(value, bool)` 剔除），对应那条就会失败。

## AI 参与方式（`../common/ai_assist.py`）

AI 在本模块里承担"批量生成/枚举测试数据 + 产出用例草稿"，产物集中在 `common/ai_assist.py`：

1. **测试数据**：按侧重分组的数据集合（如 `NON_STRING_DETECTED_TYPES`、`NUMERIC_STRING_CONFIDENCE`、
   `IS_TRASH_NON_BOOL` 等），供 `test_records.py` 逐条断言具体预期；
2. **用例目录**：`CASE_CATALOG` / `generate_cases()`，含每条用例的标题与侧重，导出为 `ai_cases.json`。



## 复现说明

`python member_xyf/gen_ai_cases.py` 会把用例目录与数据样本导出为 `ai_cases.json`。
