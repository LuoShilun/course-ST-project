# 前端说明（Vue 3 + Vite）

## 1) 安装依赖

```powershell
Set-Location e:\MyProjectWorkSpace\underwater_project\web_system\frontend
npm install
```

## 2) 配置环境变量

新建 .env.local 并填写：

```env
VITE_API_BASE_URL=/api
VITE_AMAP_KEY=your-amap-key
```

地图页面 Key 获取顺序：
1. `index.html` 中的 HTML meta `amap-key`
2. 浏览器 localStorage 中的 `amap_key`

## 3) 启动开发服务器

```powershell
npm run dev
```

默认访问地址：http://localhost:5173

## 构建

```powershell
npm run build
```

## 页面路由

用户端：
- /home
- /dashboard
- /map
- /records
- /detect
- /assistant

管理端：
- /admin/robots
- /admin/users
- /admin/announcements
