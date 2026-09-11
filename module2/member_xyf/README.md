# 模块二 · 检测记录模块自动化测试（肖云峰）

被测对象：检测记录模块后端接口 `/api/records/*` 的字段校验逻辑，即
`web_system/backend/app/api/records.py` 中的 `_validate_record_fields(data, *, creating)`。
方案：**方案2「AI测」**——用 AI 辅助生成/补全用例、推断期望、归因失败，人工审校后固化本目录。


## 运行

**必须先进入 `module2` 目录再执行。**

```powershell
cd C:\Users\Lenovo\Desktop\test\st1\course-ST-project\module2

pytest member_xyf                                             # 本模块全部用例
pytest member_xyf/test_records.py -v                          # 指定文件
pytest -m unit -v                                             # 按标记
pytest -m ai -v                                               # 只跑 AI 辅助生成的用例（模块二标记）
pytest member_xyf/test_records.py::test_placeholder -v        # 只跑单条（文件::函数名）
pytest -k confidence -v                                       # 按用例名关键字筛选
pytest --lf -v                                                # 只重跑上次失败的
```

在仓库根目录也可用 `pytest module2`（把 module2 作为参数传入，pytest 便能向上找到 `module2/pytest.ini`）。

执行结果自动写入 `module2/reports/results.json` 与 `module2/reports/junit.xml`（`--junitxml` 相对当前工作目录，所以请在 `module2` 下运行）。

> `pytest.ini` 请保持**纯 ASCII**：pytest 通过 `iniconfig` 按系统 locale 编码（中文 Windows 上是 GBK）读取它，写入中文注释会导致启动阶段直接 `UnicodeDecodeError`。

## 环境与依赖

| 项 | 说明 |
|---|---|
| Python | 3.12+ |
| pytest | ≥ 7.0（`pytest.ini` 使用了 `pythonpath` 配置项） |
| 依赖 | `pip install -r ../requirements.txt` |
| 后端服务 | 单元测试**不需要**；接口层用例需要 |
| MySQL | 单元测试**不需要**；接口层用例需要 |

## 文件

| 文件 | 说明 |
|---|---|
| `test_records.py` | 检测记录模块用例（**骨架，待补充**） |

## 用例清单（规划中，待补充）

模块二要求：**≥15 条 AI 相关用例、≥1 个缺陷**。编号建议用 `TC2-REC-xx` 前缀以区别于模块一。

| 编号 | 用例标题 | 设计方法 | AI 参与方式 | 状态 |
|---|---|---|---|---|
| TC2-REC-01 | 待填 | 待填 | 用例生成 / 期望推断 / 失败归因 | |

> 骨架阶段 `test_records.py` 以模块级 `pytest.skip` 占位，补全用例后请删除该行。
> 可复用模块一已确认的缺陷线索（如更新空 body 返回 200、创建缺字段取默认值放行）作为模块二的 AI 用例靶点。
