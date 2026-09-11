# 海迅智检 Web 系统 · 软件测试（ST）· 模块二

被测对象：**海迅智检 — 水下智能作业平台**
阶段：**模块二（AI 融合）**，采用 **方案2「AI 测」**——用 AI 辅助生成/补全用例、推断期望、归因失败。
测试范围：**检测模块**（`/detect`，`/api/detection/*`）与**检测记录模块**（`/records`，`/api/records/*`）。

> 本目录为**骨架阶段**：目录结构、`pytest.ini`、`conftest.py`、`common/` 基础设施已就位，`member_*/` 下的
> 用例文件为占位（模块级 `pytest.skip`），待两位成员补全。目标是满足模块二要求：**≥15 条 AI 相关用例、≥1 个缺陷**。

## 一、团队分工与目录结构

结构与模块一保持一致：代码按成员分目录、互不交叉；登录、断言、测试数据、浏览器驱动等基础设施放在 `common/` 供两人共用。

| 成员 | 负责模块 | 代码目录 |
|---|---|---|
| 罗时伦 | 检测模块（`/detect`） | `member_lsl/` |
| 肖云峰 | 检测记录模块（`/records`） | `member_xyf/` |
| 两人共用 | 测试基础设施 + AI 辅助接入点 | `common/` |

```
module2/
├─ pytest.ini                       用例发现与标记配置（新增 ai 标记）
├─ conftest.py                      共享：登录客户端、数据清理、浏览器驱动、结果采集
├─ requirements.txt                 依赖清单
├─ common/                          ← 两人共用的测试基础设施
│   ├─ paths.py                     被测地址、账号、路径常量
│   ├─ api_client.py                被测接口封装（登录态复用）
│   ├─ assertions.py                统一断言与“实际结果”记录
│   ├─ assets.py                    测试数据准备（真实水下图像 / 视频 / 非法文件）
│   ├─ ui.py                        浏览器驱动（Selenium + Chrome headless）与页面基类
│   └─ ai_assist.py                 ← 方案2「AI测」接入点（用例生成/期望推断/失败归因，骨架待实现）
├─ member_lsl/                      ← 罗时伦：检测模块（用例待补充）
│   ├─ README.md
│   └─ test_detection.py
├─ member_xyf/                      ← 肖云峰：检测记录模块（用例待补充）
│   ├─ README.md
│   └─ test_records.py
├─ assets/                          测试数据
└─ reports/                         执行产物：junit.xml、results.json、截图
```

## 二、环境要求

| 项 | 版本/说明 |
|---|---|
| Python | 3.12+ |
| pytest | ≥ 7.0（`pytest.ini` 使用了 `pythonpath` 配置项） |
| 依赖 | 见 `requirements.txt`，安装：`pip install -r requirements.txt` |
| 被测后端 | `http://127.0.0.1:5000`（`backend/` 下 `python run.py`） |
| 被测前端 | `http://127.0.0.1:5173`（`frontend/` 下 `npm run dev`） |
| 数据库 | MySQL 8.0，库名 `underwater_system` |
| 浏览器 | Google Chrome 128 + 同大版本 chromedriver（UI 自动化用，headless 运行） |
| 测试账号 | `admin/admin123`、`user1/user123`、`user2/user123` |

> 单元测试（直接 import 被测函数）**不需要**后端服务与 MySQL；接口层 / UI 层用例需要上述环境全部运行。

## 三、运行方式

**必须先进入 `module2` 目录再执行。** `pytest.ini` 位于 `module2/`，pytest 只从“参数所在目录”向上查找配置文件、不会往子目录找。

```bash
cd module2
pip install -r requirements.txt

python -m pytest                       # 全部自动化用例
python -m pytest member_lsl            # 只跑罗时伦的检测模块
python -m pytest member_xyf            # 只跑肖云峰的检测记录模块
python -m pytest -m api                # 只跑接口层
python -m pytest -m ui                 # 只跑浏览器 UI 层
python -m pytest -m unit               # 只跑单元测试
python -m pytest -m ai                 # 只跑 AI 辅助生成的用例（模块二标记）
python -m pytest --lf -v               # 只重跑上次失败的
```

在仓库根目录也可用 `python -m pytest module2`（把 module2 作为参数传入，pytest 便能向上找到 `module2/pytest.ini`）。

**筛选说明**：`-m` 只能按标记名筛选（`api` / `ui` / `unit` / `defect` / `ai`），不能按 `case("TC2-xxx-xx")` 里的编号筛选；只跑单条用例用 `文件路径::函数名`。

执行结果自动写入 `reports/results.json` 与 `reports/junit.xml`（`--junitxml` 相对当前工作目录，所以请在 `module2` 下运行）。

> ⚠️ `pytest.ini` 请保持**纯 ASCII**：pytest 通过 `iniconfig` 按系统 locale 编码（中文 Windows 上是 GBK）读取它，写入中文注释会导致启动阶段直接 `UnicodeDecodeError`。

## 四、测试基础设施（`common/`）

与模块一相同，`common/` 封装两个模块共用的支撑能力：`paths.py`（地址/账号/常量）、`api_client.py`（接口封装）、`assertions.py`（统一断言与实际结果记录）、`assets.py`（测试数据准备）、`ui.py`（浏览器驱动与页面基类）。

模块二是 AI 融合阶段，额外提供 `ai_assist.py` 作为**“AI 如何参与测试”的唯一接入点**，与具体大模型解耦，预置三类骨架：

- `generate_cases()`：把被测函数/接口描述交给 LLM，批量产出用例草稿，人工审校后固化；
- `infer_expectation()`：让 LLM 依据接口契约推断“合理期望”，与真实响应比对，检出语义级缺陷；
- `analyze_failures()`：把 pytest 失败输出交给 LLM 做归因与修复建议。

三者均为待实现骨架；密钥一律走环境变量，不写进仓库。

## 五、模块二用例规划

模块二要求：**≥15 条 AI 相关用例、≥1 个缺陷**。用例编号建议用 `TC2-` 前缀（`TC2-DET-xx` / `TC2-REC-xx`）以区别于模块一，并用 `@pytest.mark.ai` 标记 AI 参与方式。

| 模块 | 负责人 | 规划用例数 | 已编写 |
|---|---|---|---|
| 检测模块（`/detect`） | 罗时伦 | 待定 | 0 |
| 检测记录模块（`/records`） | 肖云峰 | 待定 | 0 |
| **合计** | | **≥15** | **0** |

各模块的用工清单占位见 `member_lsl/README.md` 与 `member_xyf/README.md`。

## 六、与模块一的差异

| 维度 | 模块一 | 模块二 |
|---|---|---|
| 阶段定位 | 测试基础（**禁用** AI 生成用例/做自动化） | AI 融合（**方案2「AI测」**，鼓励 AI 辅助） |
| 数量要求 | ≥30 条用例、≥3 缺陷 | ≥15 条 AI 相关用例、≥1 缺陷 |
| 新增标记 | — | `@pytest.mark.ai` |
| 新增基础设施 | — | `common/ai_assist.py` |
| 用例编号前缀 | `TC-DET-` / `TC-REC-` | `TC2-DET-` / `TC2-REC-` |
