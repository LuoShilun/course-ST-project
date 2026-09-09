<template>
  <div class="page-wrap map-page">
    <section class="glass-card map-toolbar">
      <el-space wrap>
        <el-input v-model="keyword" placeholder="搜索机器人名称或编号" clearable style="width: 280px" />
        <el-button type="primary" @click="searchRobot">搜索</el-button>
        <el-button @click="resetSearch">重置</el-button>
        <el-button v-if="!isAdminMap" @click="locateMe">获取我的位置</el-button>
        <el-tag type="info">默认地址：{{ defaultLocation.name }}</el-tag>
        <el-tag type="success" v-if="primaryRobot">当前机器人：{{ primaryRobot.name }}</el-tag>
      </el-space>
    </section>

    <section class="glass-card map-wrap">
      <div v-if="!amapReady" class="fallback-tip">
        未配置高德地图 Key，当前以表格模式展示机器人位置。
      </div>
      <div ref="mapRef" class="map-view"></div>
    </section>

    <section class="glass-card robot-table">
      <h3 class="section-title">机器人位置列表</h3>
      <el-table :data="filteredRobots" border height="280">
        <el-table-column prop="robot_code" label="机器人编号" width="140" />
        <el-table-column prop="name" label="机器人名称" width="160" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            {{ statusText(scope.row.status) }}
          </template>
        </el-table-column>
        <el-table-column label="坐标">
          <template #default="scope">
            {{ scope.row.latitude || '-' }}, {{ scope.row.longitude || '-' }}
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import AMapLoader from '@amap/amap-jsapi-loader'

import { api } from '../../services/api'
import { useAuthStore } from '../../stores/auth'

const mapRef = ref<HTMLDivElement | null>(null)
const robots = ref<any[]>([])
const myRobot = ref<any | null>(null)
const keyword = ref('')
const amapReady = ref(false)
const route = useRoute()
const auth = useAuthStore()
const defaultLocation = {
  name: '深圳市南山区科技园',
  lng: 114.085,
  lat: 22.547
}

let AMapInstance: any = null
let map: any = null
let markers: any[] = []
let myLocationMarker: any = null

const isAdminMap = computed(() => route.path.startsWith('/admin/'))
const primaryRobot = computed(() => {
  if (isAdminMap.value) return null
  return myRobot.value
})

const filteredRobots = computed(() => {
  const key = keyword.value.trim().toLowerCase()
  if (!key) return robots.value
  return robots.value.filter((r) => `${r.robot_code} ${r.name}`.toLowerCase().includes(key))
})

const clearMarkers = () => {
  markers.forEach((m) => m.setMap(null))
  markers = []
}

const robotPosition = (robot: any, dupIndex = 0): [number, number] | null => {
  if (robot.longitude == null || robot.latitude == null) return null
  const lng = Number(robot.longitude)
  const lat = Number(robot.latitude)
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null
  if (dupIndex <= 0) return [lng, lat]

  const offset = 0.00018
  const angle = dupIndex * 0.9
  return [lng + Math.cos(angle) * offset, lat + Math.sin(angle) * offset]
}

const focusRobot = (robot: any) => {
  if (!map) return
  const pos = robotPosition(robot)
  if (!pos) return
  map.setCenter(pos)
  map.setZoom(13)
}

const renderMarkers = () => {
  if (!map || !AMapInstance) return
  clearMarkers()

  const duplicateCounter = new Map<string, number>()

  filteredRobots.value.forEach((robot) => {
    const key = `${robot.longitude},${robot.latitude}`
    const dupIndex = duplicateCounter.get(key) || 0
    duplicateCounter.set(key, dupIndex + 1)

    const pos = robotPosition(robot, dupIndex)
    if (!pos) return

    const marker = new AMapInstance.Marker({
      position: pos,
      title: `${robot.robot_code} ${robot.name}`,
      label: {
        content: `<div class="robot-marker-label">${robot.name} (${robot.robot_code})</div>`,
        direction: 'top'
      }
    })
    marker.setMap(map)
    markers.push(marker)
  })
}

const loadMap = async () => {
  const envKey = String(import.meta.env.VITE_AMAP_KEY || '').trim()
  const meta = document.querySelector('meta[name="amap-key"]') as HTMLMetaElement | null
  const metaKey = String(meta?.content || '').trim()
  const localKey = String(localStorage.getItem('amap_key') || '').trim()
  const key = localKey || metaKey || envKey
  if (!key || !mapRef.value) {
    amapReady.value = false
    return
  }

  try {
    AMapInstance = await AMapLoader.load({
      key,
      version: '2.0'
    })

    const centerLng = Number(primaryRobot.value?.longitude ?? defaultLocation.lng)
    const centerLat = Number(primaryRobot.value?.latitude ?? defaultLocation.lat)

    map = new AMapInstance.Map(mapRef.value, {
      zoom: 11,
      center: [centerLng, centerLat]
    })
    amapReady.value = true
    renderMarkers()
  } catch (error) {
    amapReady.value = false
    ElMessage.warning('高德地图初始化失败，已切换到表格模式')
  }
}

const loadRobots = async () => {
  const { data } = await api.get('/robots/map')
  robots.value = data.data || []

  if (!isAdminMap.value) {
    const meId = Number(auth.user?.id || 0)
    myRobot.value = robots.value.find((r) => Number(r.bound_user_id) === meId) || null

    if (!myRobot.value) {
      try {
        const { data: mineResp } = await api.get('/robots')
        const mine = (mineResp.data || [])[0]
        myRobot.value = mine || null
      } catch {
        myRobot.value = null
      }
    }
  }

  renderMarkers()
}

const searchRobot = () => {
  renderMarkers()
  const target = filteredRobots.value.find((r) => robotPosition(r))
  if (!target) {
    ElMessage.warning('未找到可定位的机器人坐标')
    return
  }
  focusRobot(target)
}

const resetSearch = () => {
  keyword.value = ''
  renderMarkers()
  if (map && markers.length > 0) {
    map.setFitView(markers)
  }
}

const statusText = (status: string) => {
  if (status === 'available') return '可用'
  if (status === 'unavailable') return '不可用'
  return status || '-'
}

const locateMe = () => {
  if (isAdminMap.value) {
    ElMessage.info('管理端地图不支持“获取我的位置”')
    return
  }

  if (!navigator.geolocation) {
    ElMessage.info('当前环境不支持地理定位')
    return
  }

  const robotId = myRobot.value?.id
  if (!robotId) {
    ElMessage.warning('当前账号未绑定机器人，无法更新机器人位置')
    return
  }

  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const lng = pos.coords.longitude
      const lat = pos.coords.latitude
      try {
        await api.post(`/robots/${robotId}/heartbeat`, {
          latitude: lat,
          longitude: lng,
          is_online: true,
          status: myRobot.value?.status || 'available'
        })
      } catch (error: any) {
        const status = Number(error?.response?.status || 0)
        if (status === 403) {
          ElMessage.error('无权更新该机器人位置，请联系管理员确认绑定关系')
          return
        }
        const msg = String(error?.response?.data?.message || '更新机器人位置失败')
        ElMessage.error(msg)
        return
      }

      await loadRobots()

      if (map) {
        map.setCenter([lng, lat])
      }
      if (AMapInstance) {
        if (myLocationMarker) {
          myLocationMarker.setMap(null)
        }
        myLocationMarker = new AMapInstance.Marker({
          position: [lng, lat],
          title: '我的位置',
          label: {
            content: '<div class="robot-marker-label self">我的位置</div>',
            direction: 'bottom'
          }
        })
        myLocationMarker.setMap(map)
      }

      ElMessage.success(`定位成功，已更新机器人位置：${lat.toFixed(6)}, ${lng.toFixed(6)}`)
    },
    (err) => {
      ElMessage.error(`定位失败：${err.message || '未知错误'}`)
    }
  )
}

onMounted(async () => {
  await loadRobots()
  await loadMap()
})
</script>

<style scoped>
.map-page {
  display: grid;
  grid-template-rows: auto minmax(360px, 1fr) auto;
  gap: 14px;
  height: calc(100vh - 120px);
}

.map-toolbar,
.robot-table {
  padding: 14px;
}

.map-wrap {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--border-soft);
}

.map-view {
  width: 100%;
  height: 100%;
  min-height: 360px;
  border-radius: 12px;
}

.fallback-tip {
  position: absolute;
  z-index: 10;
  top: 12px;
  left: 12px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(96, 141, 180, 0.22);
  font-size: 12px;
}

:deep(.robot-marker-label) {
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(18, 103, 148, 0.92);
  color: #fff;
  font-size: 12px;
  line-height: 1.2;
  white-space: nowrap;
}

:deep(.robot-marker-label.self) {
  background: rgba(230, 126, 34, 0.92);
}
</style>
