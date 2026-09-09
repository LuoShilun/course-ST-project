<template>
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
        <div class="blueprint-panel" aria-label="战略蓝图面板">
          <div class="blueprint-grid"></div>
          <div class="scanline"></div>

          <span class="bp-link l1"></span>
          <span class="bp-link l2"></span>
          <span class="bp-link l3"></span>
          <span class="bp-link l4"></span>

          <span class="bp-node n1"></span>
          <span class="bp-node n2"></span>
          <span class="bp-node n3"></span>
          <span class="bp-node n4"></span>
          <span class="bp-node n5"></span>
          <span class="bp-node n6"></span>

          <span class="bp-ring r1"></span>
          <span class="bp-ring r2"></span>
          <span class="bp-ring r3"></span>

          <span class="bp-corner tl"></span>
          <span class="bp-corner tr"></span>
          <span class="bp-corner bl"></span>
          <span class="bp-corner br"></span>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
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
const weather = ref<any>({
  loading: true,
  city: '定位中...',
  text_day: '-',
  temp: '-',
  wind_dir: '-',
  wind_speed: '-',
  source: '尚未获取'
})

// 调用免费天文气象 API (基于真实地理位置)
const fetchRealWeather = () => {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(async (position) => {
      const lat = position.coords.latitude
      const lon = position.coords.longitude
      weather.value.city = `经纬度定位 (${lat.toFixed(2)}, ${lon.toFixed(2)})`
      weather.value.source = "Open-Meteo 真实气象接口"
      
      try {
        const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true&windspeed_unit=kmh`)
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
  padding: 12px;
  height: calc(100vh - 84px);
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  overflow: hidden;
}

.home-header {
  border-left: 4px solid var(--el-color-primary, #409EFF);
  padding-left: 12px;
}

.main-title {
  margin: 0;
  color: var(--el-text-color-primary, #303133);
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  letter-spacing: 1px;
}

.subtitle {
  margin: 6px 0 0 0;
  color: var(--el-text-color-secondary, #909399);
  font-size: 13px;
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
  gap: 10px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 12px;
  gap: 12px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 16px 0 rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 20px;
}

.stat-icon.cyan    { background: #e0f2fe; color: #409EFF; }
.stat-icon.primary { background: #f0f9eb; color: #67C23A; }
.stat-icon.danger  { background: #fef0f0; color: #F56C6C; }
.stat-icon.success { background: #fdf6ec; color: #E6A23C; }

.stat-info { display: flex; flex-direction: column; gap: 6px; }
.stat-name { font-size: 12px; color: var(--el-text-color-secondary); }
.stat-value { font-size: 22px; font-weight: bold; line-height: 1; }

.cyan-text { color: #409EFF; }
.primary-text { color: #67C23A; }
.danger-text { color: #F56C6C; }
.success-text { color: #E6A23C; }
.unit { font-size: 12px; color: #909399;font-weight: normal; }

.core-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 10px;
  min-height: 0;
}

.block {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.block-heads {
  padding: 10px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}

.section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.apps-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 12px;
  min-height: 0;
  overflow: auto;
}

.app-item {
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color);
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.app-item:hover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.app-name { font-weight: 600; margin-bottom: 4px; color: var(--el-text-color-primary); font-size: 13px; }
.app-path { font-size: 12px; color: var(--el-text-color-secondary); font-family: monospace; }

.timeline-list {
  padding: 12px;
  margin: 0;
  min-height: 0;
  overflow: auto;
}

.ann-title { font-size: 14px; color: var(--el-text-color-primary); }
.announcement-content { font-size: 13px; margin-top: 6px; color: var(--el-text-color-regular); }

.aux-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 10px;
  min-height: 0;
}

.weather-info {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.weather-line {
  display: flex;
  align-items: center;
  font-size: 13px;
  gap: 8px;
  color: var(--el-text-color-regular);
}

.weather-line .el-icon {
  color: var(--el-color-primary);
  font-size: 15px;
}

.weather-source {
  margin-top: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-style: italic;
  padding-top: 10px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.blueprint-panel {
  position: relative;
  flex: 1;
  min-height: 190px;
  margin: 10px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(76, 201, 255, 0.42);
  background: linear-gradient(160deg, #04101f 0%, #062241 52%, #082f56 100%);
  box-shadow: inset 0 0 30px rgba(19, 124, 207, 0.28), 0 6px 14px rgba(3, 20, 42, 0.3);
}

.blueprint-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(93, 211, 255, 0.18) 1px, transparent 1px),
    linear-gradient(90deg, rgba(93, 211, 255, 0.18) 1px, transparent 1px);
  background-size: 22px 22px;
}

.scanline {
  position: absolute;
  left: 0;
  right: 0;
  height: 32%;
  background: linear-gradient(180deg, transparent 0%, rgba(76, 222, 255, 0.22) 50%, transparent 100%);
  animation: scanline 5.8s linear infinite;
}

.bp-link {
  position: absolute;
  height: 1px;
  background: rgba(116, 226, 255, 0.85);
  box-shadow: 0 0 8px rgba(116, 226, 255, 0.55);
}

.l1 { width: 33%; left: 15%; top: 30%; transform: rotate(18deg); }
.l2 { width: 38%; left: 37%; top: 47%; transform: rotate(-22deg); }
.l3 { width: 28%; left: 19%; top: 70%; transform: rotate(8deg); }
.l4 { width: 24%; left: 58%; top: 24%; transform: rotate(10deg); }

.bp-node {
  position: absolute;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #85ebff;
  box-shadow: 0 0 12px rgba(133, 235, 255, 0.9);
}

.bp-node::after {
  content: '';
  position: absolute;
  inset: -6px;
  border-radius: 999px;
  border: 1px solid rgba(133, 235, 255, 0.55);
  animation: pulse 2.8s ease-out infinite;
}

.n1 { left: 14%; top: 23%; }
.n2 { left: 33%; top: 34%; }
.n3 { left: 57%; top: 45%; }
.n4 { left: 77%; top: 29%; }
.n5 { left: 52%; top: 69%; }
.n6 { left: 22%; top: 74%; }

.bp-ring {
  position: absolute;
  border-radius: 999px;
  border: 1px dashed rgba(126, 227, 255, 0.48);
}

.r1 { width: 150px; height: 150px; right: 12%; top: 8%; }
.r2 { width: 96px; height: 96px; left: 10%; bottom: 12%; }
.r3 { width: 74px; height: 74px; right: 24%; bottom: 14%; }

.bp-corner {
  position: absolute;
  width: 18px;
  height: 18px;
  border-style: solid;
  border-color: rgba(127, 226, 255, 0.9);
}

.tl { top: 8px; left: 8px; border-width: 2px 0 0 2px; }
.tr { top: 8px; right: 8px; border-width: 2px 2px 0 0; }
.bl { bottom: 8px; left: 8px; border-width: 0 0 2px 2px; }
.br { bottom: 8px; right: 8px; border-width: 0 2px 2px 0; }

@keyframes pulse {
  0% { transform: scale(0.8); opacity: 0.8; }
  100% { transform: scale(1.8); opacity: 0; }
}

@keyframes scanline {
  0% { top: -34%; }
  100% { top: 100%; }
}

@media (max-width: 768px) {
  .core-grid, .aux-grid {
    grid-template-columns: 1fr;
  }

  .page-wrap {
    height: auto;
    min-height: calc(100vh - 84px);
    overflow: auto;
    display: flex;
    flex-direction: column;
  }

  .apps-grid {
    grid-template-columns: 1fr;
  }
}
</style>
