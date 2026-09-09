# 后端说明（Flask + MySQL）

## 1) 安装依赖

```powershell
Set-Location e:\MyProjectWorkSpace\underwater_project\web_system\backend
pip install -r requirements.txt
```

## 2) 配置环境变量

配置.env，并按实际环境修改数据库等配置。

必填配置项：
- SQLALCHEMY_DATABASE_URI
- SECRET_KEY
- JWT_SECRET_KEY

可选配置项：
- QWEN_API_KEY
- QWEATHER_API_KEY
- MODEL_DEFAULT_STUDENT_CKPT
- MODEL_ENABLE_INFERENCE
- MODEL_DEVICE

检测相关建议：
- `MODEL_ENABLE_INFERENCE=0`：默认使用稳定的模拟推理（推荐先联调前后端）。
- `MODEL_ENABLE_INFERENCE=1`：启用真实学生模型推理。
- 启用真实推理后若出现进程崩溃/连接重置，先改为 `MODEL_DEVICE=cpu` 再重启后端验证。

## 3) 初始化数据库

```powershell
flask --app run.py init-db
flask --app run.py seed-demo
```

## 4) 启动服务

```powershell
python run.py
```

默认服务地址：http://localhost:5000

## 主要接口

- GET /api/health
- POST /api/auth/login
- GET /api/dashboard/home
- GET /api/dashboard/bigscreen
- GET/POST/PUT/DELETE /api/records
- GET/POST/PUT/DELETE /api/robots
- POST /api/detection/image
- POST /api/detection/video
- GET /api/detection/video/tasks/<id>
- POST /api/assistant/chat

## 说明

- 视频检测为异步流程，当前由后台模拟任务执行。
- 图片检测会优先加载训练好的学生模型权重；若不可用则回退到模拟预测结果。
