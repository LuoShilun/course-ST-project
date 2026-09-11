# 海迅智检 Web 系统 · 软件测试（ST）

被测对象：**海迅智检 — 水下智能作业平台**
测试范围：**检测模块**（检测页面 `/detect`，后端接口 `/api/detection/*`）与**检测记录模块**（检测记录页面 `/records`，后端接口 `/api/records/*`）。

本仓库为软件测试与质量保证课程的实践产物，包含两位成员分别负责的两个被测模块的全部自动化测试用例及共用测试基础设施。

## 一、团队分工与目录结构

两位成员各自独立负责一个被测模块，**代码按成员分目录，互不交叉**；登录、断言、测试数据、浏览器驱动等测试基础设施放在 `common/` 供两人共用。

| 成员 | 负责模块 | 代码目录 | 用例数 | 其中自动化 |
|---|---|---|---|---|
| 罗时伦 | 检测模块（`/detect`） | `member_lsl/` | 17 条 | 17 条 |
| 肖云峰 | 检测记录模块（`/records`） | `member_xyf/` | 22 条 | 22 条 |
| 两人共用 | 测试基础设施（登录、断言、测试数据、浏览器驱动） | `common/` | — | — |
| **合计** | | | **39 条** | **39 条** |

```
module1/
├─ pytest.ini                       用例发现与标记配置
├─ conftest.py                      共享：登录客户端、数据清理、浏览器驱动、结果采集
├─ requirements.txt                 依赖清单
├─ common/                          ← 两人共用的测试基础设施
│   ├─ paths.py                     被测地址、账号、路径常量
│   ├─ api_client.py                被测接口封装（登录态复用）
│   ├─ assertions.py                统一断言与“实际结果”记录
│   ├─ assets.py                    测试数据准备（真实水下图像 / 视频 / 非法文件）
│   └─ ui.py                        浏览器驱动（Selenium + Chrome headless）与页面基类
├─ member_lsl/                      ← 罗时伦：检测模块
│   ├─ README.md                    本模块用例清单与运行方式
│   └─ test_detection.py            检测模块全部用例：接口 13 + UI 1 + 单元 3
├─ member_xyf/      ← 肖云峰：检测记录模块
├─  ├─   README.md                      
│   └─ test_records.py              `_validate_record_fields` 字段校验单元用例，TC-REC-01 ~ TC-REC-18-3
├─ assets/                          测试数据
└─ reports/                         执行产物：junit.xml、results.json、截图
```

## 二、环境要求

| 项 | 版本/说明 |
|---|---|
| Python | 3.12+ |
| pytest | ≥ 7.0（`pytest.ini` 使用了 `pythonpath` 配置项） |
| 依赖 | 见 `requirements.txt`（pytest / requests / selenium / openpyxl / Pillow），安装：`pip install -r requirements.txt` |
| 被测后端 | `http://127.0.0.1:5000`（`backend/` 下 `python run.py`） |
| 被测前端 | `http://127.0.0.1:5173`（`frontend/` 下 `npm run dev`） |
| 数据库 | MySQL 8.0，库名 `underwater_system` |
| 浏览器 | Google Chrome 128 + 同大版本 chromedriver（UI 自动化用，headless 运行） |
| 测试账号 | `admin/admin123`、`user1/user123`、`user2/user123` |


> **按模块的依赖差异**：检测记录模块（`member_xyf/`）为**纯单元测试**，直接导入被测函数、不经HTTP层，因此**不需要启动后端服务、也不需要 MySQL**；检测模块（`member_lsl/`）的接口层与 UI 层自动化则需要上述后端、前端与数据库运行。

## 三、运行方式

**必须先进入 `module1` 目录再执行。** `pytest.ini` 位于 `module1/`，pytest 只从“参数所在目录”向上查找配置文件、不会往子目录找。

```bash
cd module1
pip install -r requirements.txt

python -m pytest                       # 全部自动化用例（39 条）
python -m pytest member_lsl            # 只跑罗时伦的检测模块（17 条）
python -m pytest member_xyf            # 只跑肖云峰的检测记录模块（22 条）
python -m pytest -m api                # 只跑接口层
python -m pytest -m ui                 # 只跑浏览器 UI 层
python -m pytest -m unit               # 只跑单元测试
python -m pytest -k test_detection     # 按用例名关键字执行
python -m pytest --lf -v               # 只重跑上次失败的
```

在仓库根目录也可用 `python -m pytest module1`（把 module1 作为参数传入，pytest 便能向上找到 `module1/pytest.ini`）。

**筛选说明**：`-m` 只能按**标记名**筛选（`api` / `ui` / `unit` / `defect`），**不能按 `case("TC-xxx-xx")` 里的编号筛选**；想看某条用例的确切 node id 可先执行 `python -m pytest --collect-only -q`。只跑单条用例用 `文件路径::函数名`，如 `python -m pytest member_xyf/test_records.py::test_creating_valid -v`。

执行结果自动写入 `reports/results.json` 与 `reports/junit.xml`（`--junitxml` 是相对当前工作目录的，所以请在 `module1` 下运行）。

> ⚠️ `pytest.ini` 请保持**纯 ASCII**：pytest 通过 `iniconfig` 按系统 locale 编码（中文 Windows 上是 GBK）读取它，写入中文注释会导致启动阶段直接 `UnicodeDecodeError`。

## 四、测试基础设施（`common/`）

`common/` 封装了两个模块共用的支撑能力，让各模块用例只需关注业务断言：

- `paths.py`：被测地址、账号、路径常量；
- `api_client.py`：被测接口封装，自动复用登录态；
- `assertions.py`：统一断言与“实际结果”记录；
- `assets.py`：测试数据准备（真实水下图像 / 视频 / 非法文件）；
- `ui.py`：浏览器驱动（Selenium + Chrome headless）与页面基类。

用例统一用 `@pytest.mark.case("TC-xxx-xx")` 标记编号，`@pytest.mark.api` / `@pytest.mark.ui` / `@pytest.mark.unit` 区分三个测试层级。


## 五、模块一 · 检测模块（罗时伦）

被测对象：检测页面 `/detect` 及其后端接口 `/api/detection/*`。本模块共 **17 条**自动化用例：接口自动化 13 条 + 浏览器 UI 自动化 1 条 + 单元测试 3 条。

### 5.1 接口自动化（13 条，`@pytest.mark.api`）

| 用例编号 | 用例标题 | 设计方法 | 备注 |
|---|---|---|---|
| TC-DET-01 | 检测模型列表接口正常返回且字段完整 | 等价类划分 | |
| TC-DET-02 | 未携带令牌访问检测接口被拒绝 | 等价类划分 | |
| TC-DET-03 | 上传文件名称为空字符串 | 边界值分析 | |
| TC-DET-04 | 上传非图片内容应被拒绝 | 等价类划分 | |
| TC-DET-05 | 合法水下图像检测成功并写入检测记录 | 等价类划分 | |
| TC-DET-06 | 一张图片生成一条记录且字段与检测结果一致 | 等价类划分 | |
| TC-DET-07 | 传入不存在的 model_key 应明确报错 | 错误推测法 | 缺陷确认 |
| TC-DET-08 | 中文文件名上传后应保留可识别文件名 | 边界值分析 | 缺陷确认 |
| TC-DET-09 | admin 传入非法 robot_id 应返回 4xx 而非 500 | 错误推测法 | 缺陷确认 |
| TC-DET-10 | 检测历史记录的用户数据隔离 | 场景法 | |
| TC-DET-11 | 视频检测任务全流程（提交→运行→完成→预览） | 场景法 | |
| TC-DET-12 | 其他用户访问他人视频任务应被拒绝 | 场景法 | |
| TC-DET-13 | 实时监控会话生命周期与越权访问 | 场景法 | |

### 5.2 浏览器 UI 自动化（1 条，`@pytest.mark.ui`）

| 用例编号 | 用例标题 | 设计方法 | 备注 |
|---|---|---|---|
| TC-DET-14 | 检测页面模型下拉框默认选中项应存在于选项列表 | 等价类划分 | 缺陷确认 |

### 5.3 单元测试（3 条，`@pytest.mark.unit`）

直接导入后端源码中的被测函数，不经过 HTTP 与数据库，精确验证纯逻辑的边界行为。

| 用例编号 | 被测函数 | 用例标题 | 设计方法 |
|---|---|---|---|
| TC-DET-15 | `DetectionService._apply_thresh` | 置信度阈值过滤的边界行为 | 边界值分析 |
| TC-DET-16 | `_parse_score_thresh` | 置信度阈值解析与区间钳制 | 边界值分析 |
| TC-DET-17 | `DetectionService._infer_engine` | 模型文件引擎类型识别 | 等价类划分 |

### 5.4 实现要点

- 单元测试通过 `sys.path` 注入 `backend/` 后直接 `import` 被测函数，不启动 Flask 服务、不连数据库；若后端源码不可用，`_load_backend()` 会 `pytest.skip`，不会让整份用例报错；
- 检测结果一致性用例（TC-DET-06）以“垃圾目标中置信度最高者”为代表目标，校验落库记录的 `detected_type`、`confidence`、`is_trash` 与接口返回的 `detections` 完全一致；
- 记录数统计使用 `/api/records` 的 `total`，避免 `/api/detection/image/records` 的 200 条上限干扰。

## 六、模块二 · 检测记录模块（肖云峰）

被测对象：检测记录模块后端接口 `/api/records/*` 的**字段校验逻辑**，即 `web_system/backend/app/api/records.py` 中的 `_validate_record_fields(data, *, creating)`。

本模块当前采用**单元测试**方式，直接导入被测函数、不经 HTTP 层，因此**不需要启动后端服务、也不需要 MySQL**；后续的接口层暂时未作测试。

### 6.1 用例清单

共 **22 条**，全部为单元自动化用例（标记 `@pytest.mark.unit`，编号 `@pytest.mark.case("TC-REC-xx")`）。
设计方法分布：边界值分析 8 条、场景法 8 条、等价类划分 3 条、错误推测法 3 条。

**（一）创建场景 · 字段校验（`creating=True`）**

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

**（二）更新场景 · 字段校验（`creating=False`）**

| 编号 | 用例标题 | 设计方法 | 输入 | 预期结果 | 状态 |
|---|---|---|---|---|---|
| TC-REC-15 | 更新时请求体为空对象 | 场景法 | `{}` | 抛 `ValueError("更新时传入data不能为空")` | **当前不通过**，见“已知问题” |
| TC-REC-16 | 更新时三字段均合法 | 场景法 | 三字段齐全 | 校验通过，返回三个字段 | 通过 |
| TC-REC-17-1 | 仅传 `confidence` + `is_trash` | 场景法 | 缺 `detected_type` | 校验通过，只返回传入的两个字段 | 通过 |
| TC-REC-17-2 | 仅传 `detected_type` + `is_trash` | 场景法 | 缺 `confidence` | 校验通过，只返回传入的两个字段 | 通过 |
| TC-REC-17-3 | 仅传 `detected_type` + `confidence` | 场景法 | 缺 `is_trash` | 校验通过，只返回传入的两个字段 | 通过 |
| TC-REC-18-1 | 创建时缺失 `detected_type` | 场景法 | 缺该字段 | 抛 `ValueError` 并含 `detected_type` 提示文案 | 通过 |
| TC-REC-18-2 | 创建时缺失 `confidence` | 场景法 | 缺该字段 | 期望抛 `ValueError` | **当前不通过**，见“已知问题” |
| TC-REC-18-3 | 创建时缺失 `is_trash` | 场景法 | 缺该字段 | 期望抛 `ValueError` | **当前不通过**，见“已知问题” |

> 说明：TC-REC-15 / TC-REC-17-* 体现“更新只校验请求体中**实际传入**的字段”这一设计意图；TC-REC-18-* 则检验创建场景下三个必填字段的缺失处理是否一致。

### 6.2 已知问题（待处理）

以下为测试中确认的全部问题，均以**缺陷确认用例**（`@pytest.mark.xfail(strict=True)`）记录：缺陷存在时记为 `xfailed`（对应用例清单中的 `NG`）；缺陷修复后该用例会转为 `failed`，提醒测试人员更新预期并转为常规通过用例。


1. **TC-REC-15**：预期校验报错，但当前 `_validate_record_fields` 不会抛出异常。更新场景传入空 `data` 时，函数跳过全部校验分支直接返回 `{}`，缺少 data 非空校验，更新操作无意义，应当予以拒绝。后续无字段写入，但如果传入后续接口可能存在返回 200、提示更新成功的情况。该用例属于待修复缺陷。
2. **TC-REC-18-2**：预期校验报错，但当前 `_validate_record_fields` 不会抛出异常。创建场景缺失 `confidence` 字段时，代码使用 `data.get("confidence", 0.0)` 获取参数，字段缺失会取默认值直接放行，但默认值使得该记录无实际意义，直接拒绝更符合业务场景。
3. **TC-REC-18-3**：预期校验报错，但当前 `_validate_record_fields` 不会抛出异常。创建场景缺失 `is_trash` 字段时，代码使用 `data.get("is_trash", True)` 获取参数，字段缺失会取默认值直接放行；但默认值不具备正确性，可能引发误解。
4. **TC-DET-09**：admin 传入非法 `robot_id` 时，接口未拦截该非法参数而直接返回 5xx（服务器内部错误），期望应返回 4xx（客户端错误）并给出明确提示，不应把客户端参数问题暴露为服务端异常。该用例属于待修复缺陷。
5. **TC-DET-07**：传入不存在的 `model_key` 时，接口未给出明确错误提示，期望应显式识别非法模型并报错，而非静默失败或返回模糊结果。该用例属于待修复缺陷。
6. **TC-DET-08**：上传中文文件名后，落库/返回的文件名无法保留可识别的中文名称，期望上传后仍能保留可识别的文件名，避免出现乱码或名称丢失。该用例属于待修复缺陷。
7. **TC-DET-14**：检测页面模型下拉框的默认选中项不在选项列表中，导致页面初始状态与后端模型列表不一致，期望默认选中项应存在于选项列表内。该用例属于待修复缺陷。

## 七、用例统计汇总

| 模块 | 负责人 | 接口 | UI | 单元 | 小计 |
|---|---|---|---|---|---|
| 检测模块（`/detect`） | 罗时伦 | 13 | 1 | 3 | 17 |
| 检测记录模块（`/records`） | 肖云峰 | — | — | 22 | 22 |
| **合计** | | **13** | **1** | **25** | **39** |

设计方法分布（全部 39 条）：等价类划分、边界值分析、场景法、错误推测法等。

