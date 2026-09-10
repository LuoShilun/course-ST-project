# 成员A · 检测模块自动化测试（Lsl）

被测对象：检测页面 `/detect` 及其后端接口 `/api/detection/*`。
本目录只包含检测模块的测试代码，不涉及检测记录模块。

## 运行

```bash
cd testing
python -m pytest member_lsl -v          # 本模块全部 17 条自动化用例
python -m pytest member_lsl -m api      # 只跑接口层（16 条）
python -m pytest member_lsl -m ui       # 只跑浏览器 UI 层（1 条）
```

## 文件

| 文件 | 说明 |
|---|---|
| `test_detection_api.py` | 接口自动化用例 TC-DET-01 ~ TC-DET-16 |
| `test_detection_ui.py` | 浏览器 UI 自动化用例 TC-DET-17 |

## 用例清单

### 接口自动化（`test_detection_api.py`，16 条）

| 用例编号 | 用例标题 | 设计方法 | 类型 |
|---|---|---|---|
| TC-DET-01 | 检测模型列表接口正常返回且字段完整 | 等价类划分 | 自动化 |
| TC-DET-02 | 未携带令牌访问检测接口被拒绝 | 等价类划分 | 自动化 |
| TC-DET-03 | 上传图片时未携带文件字段 | 等价类划分 | 自动化 |
| TC-DET-04 | 上传文件名称为空字符串 | 边界值分析 | 自动化 |
| TC-DET-05 | 上传非图片内容应被拒绝 | 等价类划分 | 自动化 |
| TC-DET-06 | 上传被截断损坏的 JPEG 应被拒绝 | 错误推测法 | 自动化 |
| TC-DET-07 | 合法水下图像检测成功并写入检测记录 | 等价类划分 | 自动化 |
| TC-DET-08 | 一张图片生成一条记录且字段与检测结果一致 | 等价类划分 | 自动化 |
| TC-DET-09 | score_thresh 边界值与越界值的处理 | 边界值分析 | 自动化 |
| TC-DET-10 | 传入不存在的 model_key 应明确报错 | 错误推测法 | 自动化（缺陷确认 BUG-04） |
| TC-DET-11 | 中文文件名上传后应保留可识别文件名 | 边界值分析 | 自动化（缺陷确认 BUG-05） |
| TC-DET-12 | admin 传入非法 robot_id 应返回 4xx 而非 500 | 错误推测法 | 自动化（缺陷确认 BUG-01） |
| TC-DET-13 | 检测历史记录的用户数据隔离 | 场景法 | 自动化 |
| TC-DET-14 | 视频检测任务全流程（提交→运行→完成→预览） | 场景法 | 自动化 |
| TC-DET-15 | 其他用户访问他人视频任务应被拒绝 | 场景法 | 自动化 |
| TC-DET-16 | 实时监控会话生命周期与越权访问 | 场景法 | 自动化 |

### UI 自动化（`test_detection_ui.py`，1 条）

| 用例编号 | 用例标题 | 设计方法 | 类型 |
|---|---|---|---|
| TC-DET-17 | 检测页面模型下拉框默认选中项应存在于选项列表 | 等价类划分 | 自动化（缺陷确认 BUG-06） |

## 实现要点

- 用例统一用 `@pytest.mark.case("TC-DET-xx")` 标记编号，`@pytest.mark.api` / `@pytest.mark.ui` 区分层级；
- 缺陷确认用例用 `@pytest.mark.xfail(strict=True, reason="BUG-xx ...")`，缺陷修复后会自动转为失败；
- 检测结果一致性用例（TC-DET-08）以“垃圾目标中置信度最高者”为代表目标，校验落库记录的
  `detected_type`、`confidence`、`is_trash` 与接口返回的 `detections` 完全一致；
- 记录数统计使用 `/api/records` 的 `total`，避免 `/api/detection/image/records` 的 200 条上限干扰。
