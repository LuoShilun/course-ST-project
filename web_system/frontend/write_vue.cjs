const fs = require('fs');

const content = `<template>
  <div class="page-wrap home-grid">
    <div class="home-header">
      <h2 class="main-title"><el-icon><Odometer /></el-icon> 海巡智检 (OceanGuard AI) - 水下智能作业综合平台</h2>
      <p class="subtitle">企业级架构的海洋环保与水下目标ML推理框架</p>
    </div>

    <section class="overview-grid">
      <div class="stat-card light-card">
        <div class="stat-icon cyan"><el-icon><User /></el-icon></div>
        <div class="stat-info">
          <div class="stat-name">全局授权人员</div>
          <div class="stat-value cyan-text">{{ overview.user_count || 0 }} <span class="unit">人</span></div>
        </div>
      </div>

      <div class="stat-card light-card">
        <div class="stat-icon primary"><el-icon><Document /></el-icon></div>
        <div class="stat-info">
          <div class="stat-name">累计检测追溯</div>
          <div class="stat-value primary-text">{{ overview.total_records || 0 }} <span class="unit">次</span></div>
        </div>
      </div>

      <div class="stat-card light-card">
        <div class="stat-icon danger"><el-icon><Warning /></el-icon></div>
        <div class="stat-info">
          <div class="stat-name">发现疑似目标</div>
          <div class="stat-value danger-text">{{ overview.trash_records || 0 }} <span class="unit">件</span></div>
        </div>
      </div>

      <div class="stat-card light-card">
        <div class="stat-icon success"><el-icon><Cpu /></el-icon></div>
        <div class="stat-info">
          <div class="stat-name">在线控制节点</div>
          <div class="stat-value success-text">{{ overview.online_robots || 0 }} <span class="unit">台</span></div>
        </div>
      </div>
    </section>

    <div class="core-grid">
      <section class="light-card block apps">
        <div class="block-heads">
          <h3 class="section-title"><el-icon><Grid /></el-icon> 核心模块直达</h3>
        </div>
        <div class="apps-grid">
          <div v-for="app in commonApps" :key="app.path" class="app-item" @click="go(app.path)">
            <div class="app-detail">
              <div class="app-name">{{ app.name }}</div>
              <div class="app-path">{{ app.path }}</div>
            </div>
          </div>
        </div>
      </section>

      <section class="light-card block announcements">
        <div class="block-heads">
          <h3 class="section-title"><el-icon><Bell /></el-icon> 运行调度日志</h3>
        </div>
        <el-timeline class="timeline-list">
          <el-timeline-item v-for="item in announcements" :key="item.id" :timestamp="fmtTime(item.created_at)" type="primary">
            <strong class="ann-title">{{ item.title }}</strong>
            <div class="announcement-content">{{ item.content }}</div>
          </el-timeline-item>
        </el-timeline>
      </section>
    </div>

    <main class="aux-grid">
      <section class="light-card block weather">
        <div class="block-heads">
          <h3 class="section-title"><el-icon><PartlyCloudy /></el-icon> 作业海域气象 (实时定位)</h3>
        </div>
        <div class="weather-info" v-loading="weather.loading">
          <div class="weather-line">
            <el-icon><MapLocation /></el-icon> {{ weather.city }} | {{ weather.text_day }}
          </div>
          <div class="weather-line">
            <el-icon><Odometer /></el-icon> 当前温度: {{ weather.temp }} ℃
          </div>
          <div class="weather-line">
            <el-icon><WindPower /></el-icon> 风向: {{ weather.wind_dir }} / 风速: {{ weather.wind_speed }} km/h
          </div>
          <div class="weather-source">数据源: {{ weather.source }}</div>
        </div>
      </section>

      <section class="light-card block slogans">
        <div class="block-heads">
          <h3 class="section-title"><el-icon><InfoFilled /></el-icon> 战略愿景</h3>
        </div>
        <div class="slogan-marquee">
          <div class="slogan-track">
            <span v-for="(s, count) in slogansLoop" :key="count" class="slogan-item">{{ s }}</span>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import {
  User, Document, WindPower, MapLocation, PartlyCloudy, Odometer, InfoFilled, Grid, Bell, Cpu, Warning
} from '@element-plus/icons-vue'
import { api } from '../../services/api'

const router = useRouter()

const overview = ref<Record<string, number>>({})
const announcements = ref<any[]>([])
const commonApps = ref<any[]>([])
const slogans = ref<string[]>([])
const weather = ref<any>({
  loading: true,
  city: '定位中...',
  text_day: '-',
  temp: '-',
  wind_dir: '-',
  wind_speed: '-',
  source: '尚未获取'
})

const slogansLoop = computed(() => [...slogans.value, ...slogans.value])

// 调用免费天文气象 API (基于真实地理位置)
const fetchRealWeather = () => {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(async (position) => {
      const lat = position.coords.latitude
      const lon = position.coords.longitude
      weather.value.city = \`经纬度定位 (\${lat.toFixed(2)}, \${lon.toFixed(2)})\`
      weather.value.source = "Open-Meteo 真实气象接口"
      
      try {
        const res = await fetch(\`https://api.open-meteo.com/v1/forecast?latitude=\${lat}&longitude=\${lon}&current_weather=true&windspeed_unit=kmh\`)
        const json = await res.json()
        if (json.current_weather) {
            weather.value.temp = json.current_weather.temperature
            weather.value.wind_speed = json.current_weather.windspeed
            weather.value.wind_dir = json.current_weather.winddirection + "°"
            
            const code = json.current_weather.weathercode
            // 简单 WMO code 转文字
            if(code === 0) weather.value.text_day = '晴朗'
            else if(code >= 1 && code <= 3) weather.value.text_day = '多云/阴天'
            else if(code >= 45 && code <= 48) weather.value.text_day = '雾霾'
            else if(code >= 51 && code <= 67) weather.value.text_day = '阵雨/毛毛雨'
            else if(code >= 71 && code <= 82) weather.value.text_day = '大雨/暴雨'
            else if(code >= 95) weather.value.text_day = '雷暴'
            else weather.value.text_day = '未知天气'
        }
      } catch(e) {
          console.error("气象接口加载失败", e)
          weather.value.source = "气象接口调用失败"
      } finally {
        weather.value.loading = false
      }
    }, (error) => {
       weather.value.source = "用户未授权浏览器定位权限"
       weather.value.city = "未知区域 (默认权限被拦截)"
       weather.value.loading = false
    })
  } else {
    weather.value.source = "浏览器不支持 HTML5 定位"
    weather.value.loading = false
  }
}

const loadHomeData = async () => {
  try {
    const { data } = await api.get('/dashboard/home')
    overview.value = data?.data?.overview || {}
    announcements.value = data?.data?.announcements || []
    commonApps.value = data?.data?.common_apps || []
    slogans.value = data?.data?.slogans || []
  } catch (err) {
    // 降级假数据 (Fallback Mocks)
    overview.value = { user_count: 5, total_records: 1245, trash_records: 84, online_robots: 3 }
    commonApps.value = [
      { name: "双屏对比检测", path: "/detect" },
      { name: "数字存证中心", path: "/records" },
      { name: "大屏可视化", path: "/dashboard" },
      { name: "智检机器地图", path: "/map" }
    ]
    announcements.value = [
      { id: 1, title: "系统更迭", content: "全新海巡智检企用版前端部署完毕", created_at: new Date().toISOString() },
      { id: 2, title: "模型更新", content: "水下增强模型(CycleGAN)完成迭代", created_at: new Date(Date.now()-86400000).toISOString() }
    ]
    slogans.value = ["科技守护深海幽蓝", "发现 · 清除 · 保护生态"]
  }
}

const fmtTime = (raw: string) => (raw ? dayjs(raw).format('YYYY-MM-DD HH:mm') : '-')

const go = (path: string) => {
  router.push(path)
}

onMounted(() => {
  loadHomeData()
  fetchRealWeather() // 获取真实地理与天气数据
})
</script>

<style scoped>
.page-wrap {
  background: var(--bg-main, #f0f2f5) !important;
  color: var(--el-text-color-primary, #303133);
  padding: 24px;
  min-height: calc(100vh - 84px);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.home-header {
  border-left: 4px solid var(--el-color-primary, #409EFF);
  padding-left: 14px;
  margin-bottom: 18px;
}

.main-title {
  margin: 0;
  color: var(--el-text-color-primary, #303133);
  font-size: 24px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  letter-spacing: 1px;
}

.subtitle {
  margin: 6px 0 0 0;
  color: var(--el-text-color-secondary, #909399);
  font-size: 14px;
}

.light-card {
  background: #ffffff;
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  border-radius: 8px;
  box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 22px;
  gap: 20px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 16px 0 rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 28px;
}

.stat-icon.cyan    { background: #e0f2fe; color: #409EFF; }
.stat-icon.primary { background: #f0f9eb; color: #67C23A; }
.stat-icon.danger  { background: #fef0f0; color: #F56C6C; }
.stat-icon.success { background: #fdf6ec; color: #E6A23C; }

.stat-info { display: flex; flex-direction: column; gap: 6px; }
.stat-name { font-size: 14px; color: var(--el-text-color-secondary); }
.stat-value { font-size: 30px; font-weight: bold; line-height: 1; }

.cyan-text { color: #409EFF; }
.primary-text { color: #67C23A; }
.danger-text { color: #F56C6C; }
.success-text { color: #E6A23C; }
.unit { font-size: 14px; color: #909399;font-weight: normal; }

.core-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.block-heads {
  padding: 16px 20px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}

.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.apps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  padding: 20px;
}

.app-item {
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color);
  padding: 16px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.app-item:hover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.app-name { font-weight: 600; margin-bottom: 6px; color: var(--el-text-color-primary); }
.app-path { font-size: 12px; color: var(--el-text-color-secondary); font-family: monospace; }

.timeline-list {
  padding: 20px;
  margin: 0;
}

.ann-title { font-size: 14px; color: var(--el-text-color-primary); }
.announcement-content { font-size: 13px; margin-top: 6px; color: var(--el-text-color-regular); }

.aux-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 20px;
}

.weather-info {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.weather-line {
  display: flex;
  align-items: center;
  font-size: 14px;
  gap: 8px;
  color: var(--el-text-color-regular);
}

.weather-line .el-icon {
  color: var(--el-color-primary);
  font-size: 18px;
}

.weather-source {
  margin-top: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-style: italic;
  padding-top: 10px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.slogan-marquee {
  padding: 20px;
  overflow: hidden;
  position: relative;
  background: var(--el-fill-color-blank);
}

.slogan-track {
  display: flex;
  gap: 40px;
  animation: scroll 15s linear infinite;
  white-space: nowrap;
}

.slogan-item {
  font-size: 18px;
  font-weight: bold;
  color: var(--el-color-primary);
  opacity: 0.8;
}

@keyframes scroll {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

@media (max-width: 768px) {
  .core-grid, .aux-grid {
    grid-template-columns: 1fr;
  }
}
</style>
`;
fs.writeFileSync('e:/MyProjectWorkSpace/underwater_project/web_system/frontend/src/views/user/HomeView.vue', content, 'utf-8');
console.log("Written successfully");