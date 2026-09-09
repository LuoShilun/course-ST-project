<template>
  <div class="page-wrap dashboard-grid">
    <header class="dashboard-header glass-card">
      <div class="header-left">
        <h1 class="sys-title"><el-icon><Odometer /></el-icon> 海巡智检 - 全局态势指控中心</h1>
        <span class="sys-subtitle">OCEANGUARD AI GLOBAL COMMAND CENTER</span>
      </div>
      <div class="header-right">
        <el-tag effect="dark" type="success" class="status-tag" round>
          <div class="pulse"></div> 算力引擎运行正常
        </el-tag>
        <span class="sys-time">{{ currentTime }}</span>
      </div>
    </header>

    <section class="overview-row">
      <div class="data-card glass-card">
        <div class="card-icon cyan"><el-icon><Aim /></el-icon></div>
        <div class="card-info">
          <div class="card-label">今日智能侦测总量 (Daily Detections)</div>
          <div class="card-value cyan-text">{{ data.today_total || 0 }} <span class="unit">次</span></div>
        </div>
      </div>
      <div class="data-card glass-card">
        <div class="card-icon danger"><el-icon><Warning /></el-icon></div>
        <div class="card-info">
          <div class="card-label">高危污染物种类 (Trash Classes)</div>
          <div class="card-value danger-text">{{ (data.class_counts || []).length }} <span class="unit">种</span></div>
        </div>
      </div>
      <div class="data-card glass-card">
        <div class="card-icon primary"><el-icon><Cpu /></el-icon></div>
        <div class="card-info">
          <div class="card-label">活动水下终端 (Active ROVs)</div>
          <div class="card-value primary-text">{{ (data.robot_radar || []).length }} <span class="unit">台</span></div>
        </div>
      </div>
      <div class="data-card glass-card">
        <div class="card-icon success"><el-icon><DocumentChecked /></el-icon></div>
        <div class="card-info">
          <div class="card-label">归档审计记录数 (Archived Records)</div>
          <div class="card-value success-text">{{ (data.records || []).length }} <span class="unit">条</span></div>
        </div>
      </div>
    </section>

    <main class="core-area">
      <div class="left-column">
        <section class="glass-card panel trend">
          <div class="panel-header">                                                                  
            <h3 class="section-title"><el-icon><TrendCharts /></el-icon> 近一周智检趋势图</h3>
          </div>
          <div ref="trendRef" class="chart"></div>
        </section>

        <div class="bottom-row">
          <section class="glass-card panel pie">
            <div class="panel-header">
              <h3 class="section-title"><el-icon><PieChart /></el-icon> 识别物成分剖析</h3>
            </div>
            <div ref="pieRef" class="chart"></div>
          </section>

          <section class="glass-card panel radar">
            <div class="panel-header">
              <h3 class="section-title"><el-icon><DataLine /></el-icon> 终端健康度与算力负荷</h3>
            </div>
            <div ref="radarRef" class="chart"></div>
          </section>
        </div>
      </div>

      <div class="right-column">
        <section class="glass-card panel table-panel">
          <div class="panel-header">
            <h3 class="section-title"><el-icon><List /></el-icon> 实时交汇清单</h3>
          </div>
          <el-table :data="data.records || []" height="660" class="custom-dark-table">
            <el-table-column prop="robot_code" label="溯源终端编号" min-width="120">
              <template #default="scope">
                <span class="tech-text">{{ scope.row.robot_code  }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="detected_type" label="目标物种" width="120">
              <template #default="scope">
                <el-tag size="small" :type="scope.row.is_trash ? 'danger' : 'info'" effect="plain" class="cyber-tag">
                  {{ scope.row.detected_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="原位判分" width="80" align="center">
              <template #default="scope">
                <el-tag :type="scope.row.is_trash ? 'danger' : 'success'" effect="dark" class="cyber-tag">
                  {{ scope.row.is_trash ? '高危' : '安全' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import dayjs from 'dayjs'
import {
  Aim,
  Warning,
  Cpu,
  DocumentChecked,
  TrendCharts,
  PieChart,
  DataLine,
  List,
  Odometer
} from '@element-plus/icons-vue'

import { api } from '../../services/api'

const data = ref<any>({
  class_counts: [],
  trend: [],
  robot_radar: [],
  records: []
})

const currentTime = ref(dayjs().format('YYYY-MM-DD HH:mm:ss'))
let timeTimer: any = null

const trendRef = ref<HTMLDivElement | null>(null)
const pieRef = ref<HTMLDivElement | null>(null)
const radarRef = ref<HTMLDivElement | null>(null)

let trendChart: any = null
let pieChart: any = null
let radarChart: any = null

const renderTrend = () => {
  if (!trendRef.value) return
  trendChart?.dispose()
  trendChart = echarts.init(trendRef.value, 'dark')
  trendChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' } }     
    },
    legend: { data: ['总侦测数', '高危污染源'], textStyle: { color: '#a3b8cc' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },        
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.value.trend.map((x: any) => x.date),
      axisLine: { lineStyle: { color: '#4a6582' } },
      axisLabel: { color: '#a3b8cc' }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(74, 101, 130, 0.2)', type: 'dashed' } },
      axisLabel: { color: '#a3b8cc' }
    },
    series: [
      {
        type: 'line',
        name: '总侦测数',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 0 },
        areaStyle: {
          opacity: 0.8,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 221, 255)' },
            { offset: 1, color: 'rgba(0, 149, 255, 0.1)' }
          ])
        },
        itemStyle: { color: '#00ddff' },
        data: data.value.trend.map((x: any) => x.total)
      },
      {
        type: 'line',
        name: '高危污染源',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 0 },
        areaStyle: {
          opacity: 0.8,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255, 77, 79)' },
            { offset: 1, color: 'rgba(255, 77, 79, 0.1)' }
          ])
        },
        itemStyle: { color: '#ff4d4f' },
        data: data.value.trend.map((x: any) => x.trash)
      }
    ]
  })
}

const renderPie = () => {
  if (!pieRef.value) return
  pieChart?.dispose()
  pieChart = echarts.init(pieRef.value, 'dark')
  pieChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    legend: { top: '5%', left: 'center', textStyle: { color: '#a3b8cc' } },
    series: [
      {
        name: '占比',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#111827',
          borderWidth: 2
        },
        label: { show: false, position: 'center' },
        emphasis: {
          label: { show: true, fontSize: 20, fontWeight: 'bold' }
        },
        labelLine: { show: false },
        color: ['#00ddff', '#ff4d4f', '#faad14', '#52c41a', '#722ed1'],
        data: data.value.pie || []
      }
    ]
  })
}

const renderRadar = () => {
  if (!radarRef.value) return
  radarChart?.dispose()
  radarChart = echarts.init(radarRef.value, 'dark')

  const radarData = data.value.robot_radar || []
  radarChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {},
    radar: {
      shape: 'circle',
      axisName: { color: '#a3b8cc' },
      axisLine: { lineStyle: { color: 'rgba(74, 101, 130, 0.3)' } },
      splitLine: { lineStyle: { color: 'rgba(74, 101, 130, 0.3)' } },
      splitArea: { show: false },
      indicator: radarData.map((item: any) => ({ name: item.robot_code || item.name, max: 101 }))
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: radarData.map((item: any) => item.value),
            name: '算力负荷(%)',
            areaStyle: { color: 'rgba(0, 221, 255, 0.3)' },
            lineStyle: { width: 2, color: '#00ddff' },
            itemStyle: { color: '#00ddff' }
          }
        ]
      }
    ]
  })
}

const renderCharts = () => {
  renderTrend()
  renderPie()
  renderRadar()
}

const loadData = async () => {
  const { data: resp } = await api.get('/dashboard/bigscreen')
  data.value = resp.data || {}
  await nextTick()
  renderCharts()
}

onMounted(() => {
  timeTimer = setInterval(() => {
    currentTime.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
  }, 1000)

  loadData()
  window.addEventListener('resize', () => {
    trendChart?.resize()
    pieChart?.resize()
    radarChart?.resize()
  })
})

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer)
})
</script>
<style scoped>
.page-wrap {
  background: radial-gradient(circle at center, #0d1624 0%, #060b11 100%);
  color: #e5e7eb;
  padding: 24px;
  min-height: calc(100vh - 84px);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  margin-bottom: 4px;
  background: rgba(10, 20, 40, 0.5);
  border: 1px solid rgba(0, 221, 255, 0.2);
  border-left: 4px solid #00ddff;
  border-radius: 8px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
}

.header-left .el-icon {
  margin-right: 8px;
  color: #00ddff;
}

.sys-title {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #00ddff, #409fff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.sys-subtitle {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #648ba3;
  letter-spacing: 2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(82, 196, 26, 0.15) !important;
  border: 1px solid #52c41a !important;
  padding: 0px 12px;
  height: 28px;
  font-size: 12px;
}

.pulse {
  width: 8px;
   height: 8px;
   background-color: #52c41a;
   border-radius: 50%;
   animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(82, 196, 26, 0.7);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(82, 196, 26, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(82, 196, 26, 0);
  }
}

.sys-time {
  font-family: 'Digital-7', monospace;
  font-size: 18px;
  color: #00ddff;
  background: rgba(0, 40, 80, 0.5);
  padding: 6px 16px;
  border-radius: 20px;
  border: 1px solid rgba(0, 221, 255, 0.3);
}

.overview-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 4px;
}

.data-card {
  display: flex;
  align-items: center;
  padding: 22px;
  gap: 20px;
  transition: all 0.3s ease;
 }

.data-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 221, 255, 0.15);
  border-color: #00ddff;
 }

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 30px;
  transition: transform 0.3s ease;
}

.data-card:hover .card-icon {
  transform: scale(1.1);
}

.card-icon.cyan {
  background: rgba(0, 221, 255, 0.05);
  color: #00ddff;
  border: 1px solid rgba(0, 221, 255, 0.3);
}
.card-icon.primary {
  background: rgba(64, 153, 255, 0.05);
  color: #409eff;
  border: 1px solid rgba(64, 153, 255, 0.3);
}
.card-icon.danger {
  background: rgba(245, 108, 108, 0.05);
  color: #f56c6c;
  border: 1px solid rgba(245, 108, 108, 0.3);
}
.card-icon.success {
  background: rgba(103, 192, 67, 0.05);
  color: #67c043;
  border: 1px solid rgba(103, 192, 67, 0.3);
}

.card-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-label {
  font-size: 14px;
  color: #648ba3;
  font-weight: 500;
}

.card-value {
  font-size: 32px;
  font-weight: 800;
  font-family: 'Arial', sans-serif;

  line-height: 1;
}
.card-value.cyan-text { color: #00ddff; text-shadow: 0 0 10px rgba(0, 221, 255, 0.3);}
.card-value.danger-text { color: #f56c6c; text-shadow: 0 0 10px rgba(245, 108, 108, 0.3);}
.card-value.primary-text { color: #409eff; }
.card-value.success-text { color: #67c043; }

.chpunda-unit,
.unit {
  font-size: 14px;
  color: #8c9bb0;
  font-weight: normal;
  margin-left: 2px;
}

.core-area {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  flex: 1;
}

.glass-card {
  background: rgba(2, 11, 20, 0.6) !important;
  backdrop-filter: blur(24px);
  border: 1px solid rgba(88, 152, 255, 0.15);
  border-radius: 12px;
  overflow: hidden;
}

.panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.left-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.trend {
  min-height: 320px;
}

.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  flex: 1;
}

.pie, .radar {
  min-height: 280px;
}

.right-column {
  height: 100%;
}

.table-panel {
  height: 100%;
}

.panel-header {
  padding: 18px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(0, 20, 35, 0.4);
}

.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #e9eb5b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title .el-icon {
  color: #00ddff;
  font-size: 18px;
}

.chart {
  flex: 1;
  width: 100%;
  min-height: 300px;
  padding: 10px;
}

.custom-dark-table {
  background: transparent !important;
  --el-table-bg-color: transparent !important;
  --el-table-tr-bg-color: transparent !important;
 }

:deep(.custom-dark-table th.el-table__cell) {
  background-color: rgba(0, 221, 255, 0.05) !important;
  color: #00ddff;
  font-weight: 600;
  border-bottom: 1px solid rgba(0, 221, 255, 0.2);
}

:deep(.custom-dark-table td.el-table__cell) {
  background-color: transparent !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

:deep(.el-table__inner-wrapper::before) {
  display: none;
}

:deep(.custom-dark-table .el-table__body tr:hover > td.el-table__cell) {
  background-color: rgba(0, 221, 255, 0.15) !important;
}

.tech-text {
  font-family: 'Ubuntu Mono', monospace;
  color: #648ba3;
  letter-spacing: 1px;
}
.time-text {
  font-family: 'Ubuntu Mono', monospace;
  color: #8c9bb0;
  font-size: 12px;
}

.cyber-tag {
  border-radius: 4px;
  font-weight: 600;
}
</style>
