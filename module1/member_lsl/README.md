# 检测模块自动化测试（罗时伦）

被测对象：检测页面 `/detect` 及其后端接口 `/api/detection/*`。
本目录只包含检测模块的测试代码，不涉及检测记录模块。

## 运行

```bash
cd testing
python -m pytest member_lsl -v          # 本模块全部 17 条自动化用例
python -m pytest member_lsl -m api      # 只跑接口层（13 条）
python -m pytest member_lsl -m ui       # 只跑浏览器 UI 层（1 条）
python -m pytest member_lsl -m unit     # 只跑单元测试（3 条）
```

## 文件

| 文件 | 说明 |
|---|---|
| `test_detection.py` | 检测模块全部自动化用例：接口 13 条 + UI 1 条 + 单元测试 3 条 |

## 用例清单

### 一、接口自动化（13 条，`@pytest.mark.api`）

| 用例编号 | 用例标题 | 设计方法 | 备注 |
|---|---|---|---|
| TC-DET-01 | 检测模型列表接口正常返回且字段完整 | 等价类划分 | |
| TC-DET-02 | 未携带令牌访问检测接口被拒绝 | 等价类划分 | |
| TC-DET-03 | 上传文件名称为空字符串 | 边界值分析 | |
| TC-DET-04 | 上传非图片内容应被拒绝 | 等价类划分 | |
| TC-DET-05 | 合法水下图像检测成功并写入检测记录 | 等价类划分 | |
| TC-DET-06 | 一张图片生成一条记录且字段与检测结果一致 | 等价类划分 | |
| TC-DET-07 | 传入不存在的 model_key 应明确报错 | 错误推测法 | 缺陷确认 BUG-04 |
| TC-DET-08 | 中文文件名上传后应保留可识别文件名 | 边界值分析 | 缺陷确认 BUG-05 |
| TC-DET-09 | admin 传入非法 robot_id 应返回 4xx 而非 500 | 错误推测法 | 缺陷确认 BUG-01 |
| TC-DET-10 | 检测历史记录的用户数据隔离 | 场景法 | |
| TC-DET-11 | 视频检测任务全流程（提交→运行→完成→预览） | 场景法 | |
| TC-DET-12 | 其他用户访问他人视频任务应被拒绝 | 场景法 | |
| TC-DET-13 | 实时监控会话生命周期与越权访问 | 场景法 | |

### 二、浏览器 UI 自动化（1 条，`@pytest.mark.ui`）

| 用例编号 | 用例标题 | 设计方法 | 备注 |
|---|---|---|---|
| TC-DET-14 | 检测页面模型下拉框默认选中项应存在于选项列表 | 等价类划分 | 缺陷确认 BUG-06 |

### 三、单元测试（3 条，`@pytest.mark.unit`）

直接导入后端源码中的被测函数，不经过 HTTP 与数据库，精确验证纯逻辑的边界行为。

| 用例编号 | 被测函数 | 用例标题 | 设计方法 |
|---|---|---|---|
| TC-DET-15 | `DetectionService._apply_thresh` | 置信度阈值过滤的边界行为 | 边界值分析 |
| TC-DET-16 | `_parse_score_thresh` | 置信度阈值解析与区间钳制 | 边界值分析 |
| TC-DET-17 | `DetectionService._infer_engine` | 模型文件引擎类型识别 | 等价类划分 |

## 实现要点

- 用例统一用 `@pytest.mark.case("TC-DET-xx")` 标记编号，`@pytest.mark.api` / `@pytest.mark.ui` /
  `@pytest.mark.unit` 区分三个测试层级；
- 单元测试通过 `sys.path` 注入 `backend/` 后直接 `import` 被测函数，不启动 Flask 服务、不连数据库；
  若后端源码不可用，`_load_backend()` 会 `pytest.skip`，不会让整份用例报错；
- 缺陷确认用例用 `@pytest.mark.xfail(strict=True, reason="BUG-xx ...")`，缺陷修复后会自动转为失败；
- 检测结果一致性用例（TC-DET-06）以“垃圾目标中置信度最高者”为代表目标，校验落库记录的
  `detected_type`、`confidence`、`is_trash` 与接口返回的 `detections` 完全一致；
- 记录数统计使用 `/api/records` 的 `total`，避免 `/api/detection/image/records` 的 200 条上限干扰。
