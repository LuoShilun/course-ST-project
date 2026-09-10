# 成员B · 检测记录模块自动化测试（XiaoYunfeng）

被测对象：检测记录模块后端接口 `/api/records/*` 的**字段校验逻辑**，即
`web_system/backend/app/api/records.py` 中的 `_validate_record_fields(data, *, creating)`。

本模块当前采用**单元测试**方式，直接导入被测函数、不经HTTP层，因此**不需要启动后端服务、也不需要 MySQL**
后续的接口层暂时未作测试

## 运行

**必须先进入 `module1` 目录再执行。** `pytest.ini` 位于 `module1/`，pytest 只从"参数所在目录"向上查找配置文件、不会往子目录找
```powershell
cd C:\Users\Lenovo\Desktop\test\st1\course-ST-project\module1

pytest member_xyf                                             # 本模块全部用例
pytest member_xyf/test_records.py -v                          # 指定文件
pytest -m unit -v                                             # 按标记（本模块用例全部为 unit）
pytest member_xyf/test_records.py::test_creating_valid -v     # 只跑单条（文件::函数名）
pytest -k confidence -v                                       # 按用例名关键字筛选
pytest --lf -v                                                # 只重跑上次失败的
```

在仓库根目录也可用 `pytest module1`（把 module1 作为参数传入，pytest 便能向上找到 `module1/pytest.ini`）。

`-m` 只能按**标记名**筛选（`unit` / `api` / `ui` / `defect`），**不能按 `case("TC-REC-xx")` 里的编号筛选**；想看某条的确切 node id 可先执行 `pytest --collect-only -q`。

执行结果自动写入 `module1/reports/results.json` 与 `module1/reports/junit.xml`（`--junitxml` 是相对当前工作目录的，所以请在 `module1` 下运行）。

## 环境与依赖

| 项 | 说明 |
|---|---|
| Python | 3.12+ |
| pytest | ≥ 7.0（`pytest.ini` 使用了 `pythonpath` 配置项） |
| 依赖 | `pip install -r ../requirements.txt` |
| 后端服务 | **不需要** |
| MySQL | **不需要** |


> `pytest.ini` 请保持**纯 ASCII**：pytest 通过 `iniconfig` 按系统 locale 编码（中文 Windows 上是 GBK）读取它，写入中文注释会导致启动阶段直接 `UnicodeDecodeError`。

## 文件

| 文件 | 说明 |
|---|---|
| `test_records.py` | `_validate_record_fields` 字段校验单元用例，TC-REC-01 ~ TC-REC-18-3 |

## 用例清单

共 **22 条**，全部为单元自动化用例（标记 `@pytest.mark.unit`，编号 `@pytest.mark.case("TC-REC-xx")`）。
设计方法分布：边界值分析 8 条、场景法 8 条、等价类划分 3 条、错误推测法 3 条。

### 一、创建场景 · 字段校验（`creating=True`）

| 编号 | 用例标题 | 设计方法 | 输入 | 预期结果 | 状态 |
|---|---|---|---|---|---|
| TC-REC-01 | 三字段均合法，`detected_type` 首尾空格自动去除 | 等价类划分 | `"  trash  "` / `0.5` / `true` | 返回 `{"detected_type": "trash", "confidence": 0.5, "is_trash": true}` | 通过 |
| TC-REC-02 | `confidence` 低于下界 | 边界值分析 | `-0.1` | 抛 `ValueError("confidence 必须为 0 到 1 之间的有限数值")` | 通过 |
| TC-REC-03 | `confidence` 取下界值 | 边界值分析 | `0.0` | 校验通过，返回 `confidence = 0.0` | 通过 |
| TC-REC-04 | `confidence` 取上界值 | 边界值分析 | `1.0` | 校验通过，返回 `confidence = 1.0` | 通过 |
| TC-REC-05 | `confidence` 高于上界 | 边界值分析 | `1.1` | 抛 `ValueError("confidence 必须为 0 到 1 之间的有限数值")` | 通过 |
| TC-REC-06 | `confidence` 传入数字字符串可正常转换 | 等价类划分 | `"0.5"` | 校验通过，返回数值 `0.5`（非字符串） | 通过 |
| TC-REC-07 | `confidence` 传入非数字字符串 | 错误推测法 | `"abc"` | 抛 `ValueError("confidence 必须为 0 到 1 之间的有限数值")` | 通过 |
| TC-REC-08 | `confidence` 传入 JSON 布尔值 | 错误推测法 | `true` | 抛 `ValueError`（布尔虽可转 `1.0`，仍应被拒） | 通过 |
| TC-REC-09 | 缺失 `detected_type` | 等价类划分 | 不含该字段 | 抛 `ValueError("detected_type 必须为 1 到 50 个字符的非空字符串")` | 通过 |
| TC-REC-10 | `detected_type` 为空字符串 | 边界值分析 | `""` | 抛 `ValueError`（`strip()` 后长度为 0） | 通过 |
| TC-REC-11 | `detected_type` 取长度下界 | 边界值分析 | `"a"` | 校验通过，长度 1 | 通过 |
| TC-REC-12 | `detected_type` 取长度上界 | 边界值分析 | `"a" * 50` | 校验通过，长度 50 | 通过 |
| TC-REC-13 | `detected_type` 长度越界 | 边界值分析 | `"a" * 51` | 抛 `ValueError` | 通过 |
| TC-REC-14 | `is_trash` 传入非布尔值 | 错误推测法 | `1` | 抛 `ValueError("is_trash 必须为 JSON 布尔值 true 或 false")` | 通过 |

### 二、更新场景 · 字段校验（`creating=False`）

| 编号 | 用例标题 | 设计方法 | 输入 | 预期结果 | 状态 |
|---|---|---|---|---|---|
| TC-REC-15 | 更新时请求体为空对象 | 场景法 | `{}` | 抛 `ValueError("更新时传入data不能为空")` | **当前不通过**，见"已知问题" |
| TC-REC-16 | 更新时三字段均合法 | 场景法 | 三字段齐全 | 校验通过，返回三个字段 | 通过 |
| TC-REC-17-1 | 仅传 `confidence` + `is_trash` | 场景法 | 缺 `detected_type` | 校验通过，只返回传入的两个字段 | 通过 |
| TC-REC-17-2 | 仅传 `detected_type` + `is_trash` | 场景法 | 缺 `confidence` | 校验通过，只返回传入的两个字段 | 通过 |
| TC-REC-17-3 | 仅传 `detected_type` + `confidence` | 场景法 | 缺 `is_trash` | 校验通过，只返回传入的两个字段 | 通过 |
| TC-REC-18-1 | 创建时缺失 `detected_type` | 场景法 | 缺该字段 | 抛 `ValueError` 并含 `detected_type` 提示文案 | 通过 |
| TC-REC-18-2 | 创建时缺失 `confidence` | 场景法 | 缺该字段 | 期望抛 `ValueError` | **当前不通过**，见"已知问题" |
| TC-REC-18-3 | 创建时缺失 `is_trash` | 场景法 | 缺该字段 | 期望抛 `ValueError` | **当前不通过**，见"已知问题" |

> 说明：TC-REC-15 / TC-REC-17-* 体现"更新只校验请求体中**实际传入**的字段"这一设计意图；TC-REC-18-* 则检验创建场景下三个必填字段的缺失处理是否一致。

## 已知问题（待处理）

1. **TC-REC-15**：预期校验报错，但当前 `_validate_record_fields` 不会抛出异常。更新场景传入空 `data` 时，函数跳过全部校验分支直接返回 `{}`，缺少 data 非空校验，更新操作无意义，应当予以拒绝。后续无字段写入，但如果传入后续接口可能存在返回 200，提示更新成功的情况。该用例属于待修复缺陷。
2. **TC-REC-18-2**：预期校验报错，但当前 `_validate_record_fields` 不会抛出异常。创建场景缺失 `confidence` 字段时，代码使用 `data.get("confidence", 0.0)` 获取参数，字段缺失会取默认值直接放行，但默认值使得该记录无实际意义，直接拒绝更符合业务场景。
3. **TC-REC-18-3**：预期校验报错，但当前 `_validate_record_fields` 不会抛出异常。创建场景缺失 `is_trash` 字段时，代码使用 `data.get("is_trash", True)` 获取参数，字段缺失会取默认值直接放行；但默认值不具备正确性，可能引发误解。

