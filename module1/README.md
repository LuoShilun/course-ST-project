# 海迅智检 Web 系统 · ST

被测对象：**海迅智检--水下智能作业平台**
测试范围：检测模块（检测页面 `/detect`）与检测记录模块（检测记录页面 `/records`）。

## 1. 两人分工与目录划分

两位成员各自独立负责一个被测模块，**代码按成员分目录，互不交叉**：

| 成员 | 负责模块 | 代码目录 | 用例 | 其中自动化 |
|---|---|---|---|---|
| 罗时伦 | 检测模块（/detect） | `member_lsl/` | 20 条 | 17 条 |
| 两人共用 | 测试基础设施（登录、断言、测试数据、浏览器驱动） | `common/` | — | — |

```
testing/
├─ pytest.ini                     用例发现与标记配置
├─ conftest.py                    共享：登录客户端、数据清理、浏览器驱动、结果采集
├─ requirements.txt               依赖清单
├─ common/                        ← 两人共用的测试基础设施
│   ├─ team.py                    小组成员与分工（改姓名只需改这里）
│   ├─ paths.py                   被测地址、账号、路径常量
│   ├─ api_client.py              被测接口封装（登录态复用）
│   ├─ assertions.py              统一断言与“实际结果”记录
│   ├─ assets.py                  测试数据准备（真实水下图像 / 视频 / 非法文件）
│   └─ ui.py                      浏览器驱动（Selenium + Chrome headless）与页面基类
├─ member_lsl/                    ← LuoShilun：检测模块
│   ├─ README.md                  本模块用例清单与运行方式
│   ├─ test_detection_api.py      TC-DET-01 ~ TC-DET-16（接口自动化 16 条）
│   └─ test_detection_ui.py       TC-DET-17（浏览器 UI 自动化 1 条）
├─ member_b_records/              ← XiaoYunfeng：检测记录模块
│   
├─ assets/                        测试数据
└─ reports/                       执行产物：junit.xml、results.json、截图
```

## 2. 环境要求

| 项 | 版本/说明 |
|---|---|
| Python | 3.12+ |
| 依赖 | 见 `requirements.txt`（pytest / requests / selenium / openpyxl / Pillow） |
| 被测后端 | `http://127.0.0.1:5000`（`backend/` 下 `python run.py`） |
| 被测前端 | `http://127.0.0.1:5173`（`frontend/` 下 `npm run dev`） |
| 数据库 | MySQL 8.0，库名 `underwater_system` |
| 浏览器 | Google Chrome 128 + 同大版本 chromedriver（UI 自动化用，headless 运行） |
| 测试账号 | `admin/admin123`、`user1/user123`、`user2/user123` |

浏览器与驱动路径可通过环境变量覆盖：`CHROME_BINARY`、`CHROMEDRIVER`；
被测地址可通过 `HXZJ_BASE_URL`、`HXZJ_WEB_URL` 覆盖。

## 3. 运行方式

```bash
cd testing
pip install -r requirements.txt

python -m pytest                          # 全部自动化用例（34 条）
python -m pytest member_lsl       # 只跑LuoShilun的检测模块用例（17 条）
python -m pytest -m api                   # 只跑接口层
python -m pytest -m ui                    # 只跑浏览器 UI 层
python -m pytest -k test_detect_image     # 按用例名执行
```

## 4. 用例与自动化

- 用例总数 **40** 条，其中自动化 **34** 条（**85%**），手工 6 条。
- 设计方法：等价类划分 14 条、场景法 11 条、错误推测法 8 条、边界值分析 7 条。
- 接口层自动化：`requests` 驱动真实后端，覆盖正常流程、参数校验、边界值、越权与数据隔离。
- UI 层自动化：`Selenium` + Chrome headless 登录真实前端，校验页面渲染与接口数据一致性。
- **缺陷确认用例**统一使用 `@pytest.mark.xfail(strict=True)`：缺陷存在时记为 `xfailed`（对应用例清单的 `NG`），
  缺陷修复后该用例会转为 `failed`，提醒测试人员更新预期并转为常规通过用例。

执行结果自动写入 `reports/results.json` 与 `reports/junit.xml`。

## 5. 测试数据与数据清理

- `assets/underwater_trash_bio.jpg`、`assets/underwater_bio_only.jpg` 取自项目数据集
  `TrashImage-2` 测试集，可稳定检出 Trash/Bio 目标；
- `assets/sample_clip.avi` 由 OpenCV 合成，用于视频检测任务；
- 用例中新建的检测记录通过 `temp_records` fixture 在用例结束后统一删除，
  不在业务库中残留测试数据；上传的图片/视频按被测系统正常行为落盘于 `backend/uploads/`。
