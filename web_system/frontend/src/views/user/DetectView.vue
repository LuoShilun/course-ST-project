<template>
  <div class="page-wrap detect-page glass-card">
    <div class="page-header">
      <div class="header-title">
        <el-icon class="title-icon"><Aim /></el-icon>
        <span>智能检测工作台</span>
        <el-tag :type="inferenceEnabled ? 'success' : 'warning'" size="small" class="status-tag">
          {{ inferenceEnabled ? '已连接云端推理引擎' : '本地沙盒模拟模式' }}
        </el-tag>
      </div>
      <div class="header-desc">支持实时流媒体与图像摄取，底层驱动：YOLO全系网络结构与CycleGAN水下增强。</div>
    </div>

    <!-- Main Workspace Layout -->
    <el-row :gutter="20" class="workspace-row">
      <!-- Left: Display & Interaction -->
      <el-col :span="16">
        <el-card shadow="never" class="display-card panel-card">
          <template #header>
            <div class="panel-header">
              <el-icon><Monitor /></el-icon>
              <span>作业控制台 (Workspace)</span>
            </div>
          </template>
          
          <el-tabs v-model="activeTab" class="detect-tabs custom-tabs">
            <el-tab-pane label="静态图像解析" name="image">
              <div class="upload-zone">
                <el-upload drag :auto-upload="false" :show-file-list="true" :limit="1" :on-change="onImageChange" :on-exceed="onExceed">
                  <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                  <div class="el-upload__text">拖拽图片到此处，或 <em>点击上传探底图像</em></div>
                </el-upload>
                <div class="action-row" style="margin-top: 14px; text-align: center;">
                  <el-button type="primary" class="process-btn" :disabled="!selectedImage || !selectedModelKey" :loading="imageSubmitting" @click="submitImage" size="large">
                    <el-icon><VideoPlay /></el-icon> 启动模型推理
                  </el-button>
                </div>
              </div>

              <div v-if="sourceImagePreview || resultImagePreview" class="visual-compare-area">
                <div class="compare-title">
                  <span><el-icon><DataBoard /></el-icon> 结果对比视窗</span>
                  <span v-if="lastModelStatus" :class="['status-badge', lastModelType]">{{ lastModelStatus }}</span>
                </div>
                <div class="compare-grid">
                  <div class="img-box">
                    <div class="img-label">探头原画面 (Raw Source)</div>
                    <el-image v-if="sourceImagePreview" :src="sourceImagePreview" :preview-src-list="[sourceImagePreview, resultImagePreview]" fit="contain" class="preview-img" />
                  </div>
                  <div class="img-box">
                    <div class="img-label highlight">AI解析增强 (Annotated)</div>
                    <el-image v-if="resultImagePreview" :src="resultImagePreview" :preview-src-list="[resultImagePreview, sourceImagePreview]" fit="contain" class="preview-img" />
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane label="视频流离线解析" name="video">
               <div class="upload-zone">
                <el-upload drag :auto-upload="false" :show-file-list="true" :limit="1" :on-change="onVideoChange" :on-exceed="onExceed" accept="video/*">
                  <el-icon class="el-icon--upload"><Film /></el-icon>
                  <div class="el-upload__text">拖拽视频文件到此处，或 <em>点击上传深水巡检录像</em></div>
                </el-upload>
                <div class="action-row" style="margin-top: 14px; text-align: center; display: flex; justify-content: center; gap: 12px;">
                  <el-button type="primary" class="process-btn" :disabled="!selectedVideo || !selectedModelKey" :loading="videoSubmitting" @click="submitVideo" size="large">
                    <el-icon><VideoPlay /></el-icon> 投递计算集群
                  </el-button>
                  <el-button @click="refreshTask" :disabled="!currentTaskId" plain size="large">
                    <el-icon><Refresh /></el-icon> 探针刷新
                  </el-button>
                </div>
              </div>

               <div v-if="taskStatus" class="task-monitor">
                 <div class="monitor-header">
                    <span>序列号：{{ taskStatus.id }}</span>
                    <el-tag :type="taskStatus.status === 'finished' ? 'success' : taskStatus.status === 'failed' ? 'danger' : 'warning'" effect="dark">
                      {{ taskStatusText(taskStatus.status) }}
                    </el-tag>
                 </div>
                 <div class="progress-wrap">
                   <el-progress :percentage="taskStatus.progress || 0" :status="taskStatus.status === 'finished' ? 'success' : ''" :stroke-width="14" striped striped-flow />
                   <span class="progress-text" v-if="taskStatus.status === 'running'">离线视频检测处理中...</span>
                 </div>
                 <div v-if="taskStatus.error_message" class="error-msg"><el-icon><Warning /></el-icon> {{ taskStatus.error_message }}</div>
                 <el-alert
                   v-if="taskStatus.status === 'finished' && taskStatus.result?.output_video_path && taskStatus.result?.output_video_web_playable === false"
                   title="检测后视频编码为 mp4v，浏览器可能无法播放，当前回放已自动降级为原始视频。"
                   type="warning"
                   :closable="false"
                   show-icon
                   style="margin-top: 12px;"
                 />
               </div>

               <div v-if="videoPreviewUrl" class="visual-compare-area video-player-container">
                 <div class="compare-title">
                    <span><el-icon><Film /></el-icon> 推理录像回放 (Playback)</span>
                 </div>
                 <video :src="videoPreviewUrl" controls class="preview-video" style="width: 100%; border-radius: 8px; background: #000; outline: none;"></video>
               </div>
            </el-tab-pane>

            <el-tab-pane label="实时摄像头监控检测" name="realtime">
              <div class="upload-zone">
                <el-alert
                  title="实时流地址由当前用户绑定机器自动注入；如需修改请联系管理员在机器管理中配置 RTSP。"
                  type="info"
                  :closable="false"
                  show-icon
                />
                <div class="action-row" style="margin-top: 14px; text-align: center; display: flex; justify-content: center; gap: 12px;">
                  <el-button
                    type="primary"
                    class="process-btn"
                    :disabled="!realtimeSource || !selectedModelKey || realtimeRunning"
                    :loading="realtimeStarting"
                    @click="startRealtime"
                    size="large"
                  >
                    <el-icon><VideoPlay /></el-icon> 启动远程监控
                  </el-button>
                  <el-button
                    type="danger"
                    plain
                    :disabled="!realtimeSessionId || !realtimeRunning"
                    @click="stopRealtime"
                    size="large"
                  >
                    <el-icon><Warning /></el-icon> 停止监控
                  </el-button>
                  <el-button
                    plain
                    :disabled="!realtimeSource || !selectedModelKey"
                    @click="reconnectRealtime"
                    size="large"
                  >
                    <el-icon><Refresh /></el-icon> 一键重连
                  </el-button>
                </div>
              </div>

              <div v-if="realtimeStatus" class="task-monitor">
                <div class="monitor-header">
                  <span>会话号：{{ realtimeStatus.id }}</span>
                  <el-tag :type="realtimeStatus.status === 'running' ? 'success' : realtimeStatus.status === 'failed' ? 'danger' : 'warning'" effect="dark">
                    {{ taskStatusText(realtimeStatus.status) }}
                  </el-tag>
                </div>
                <div class="progress-wrap">
                  <el-progress :percentage="realtimeProgress" :status="realtimeStatus.status === 'running' ? 'success' : ''" :stroke-width="14" striped striped-flow />
                  <span class="progress-text" v-if="realtimeStatus.status === 'running'">
                    实时检测中... 已处理 {{ realtimeStatus.frames_processed || 0 }} 帧 | 实测 {{ realtimeStatus.observed_fps || 0 }} FPS
                  </span>
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px;">
                  <el-tag type="info">无帧时长: {{ realtimeStatus.no_frame_sec ?? '-' }}s</el-tag>
                  <el-tag type="success">实测FPS: {{ realtimeStatus.observed_fps ?? 0 }}</el-tag>
                  <el-tag :type="(realtimeStatus.frames_processed || 0) > 0 ? 'success' : 'warning'">帧计数: {{ realtimeStatus.frames_processed || 0 }}</el-tag>
                </div>
                <div v-if="realtimeStatus.error_message" class="error-msg"><el-icon><Warning /></el-icon> {{ realtimeStatus.error_message }}</div>
                <el-alert
                  v-if="realtimeStatus.status === 'running' && (realtimeStatus.no_frame_sec || 0) >= 6"
                  title="监控已启动但暂未稳定取帧，请检查 RTSP 推流是否持续、网络是否抖动，或点击“一键重连”。"
                  type="warning"
                  :closable="false"
                  show-icon
                  style="margin-top: 10px;"
                />
              </div>

              <div v-if="realtimeFrameUrl" class="visual-compare-area video-player-container">
                <div class="compare-title">
                  <span><el-icon><Monitor /></el-icon> 远程监控实时画面 (Live Feed)</span>
                </div>
                <img :src="realtimeFrameUrl" class="preview-video" style="width: 100%; border-radius: 8px; background: #000; outline: none; object-fit: contain;" />
              </div>
            </el-tab-pane>

          </el-tabs>
        </el-card>
      </el-col>

      <!-- Right: Config & Timeline -->
      <el-col :span="8">
        <el-card shadow="never" class="config-card panel-card">
          <template #header>
            <div class="panel-header">
              <el-icon><Setting /></el-icon>
              <span>算力核心分配 (Engine Setting)</span>
            </div>
          </template>
          
          <el-form label-position="top">
            <el-form-item label="水域场景适配模型">
              <el-select v-model="selectedModelKey" placeholder="自动分配最佳模型" style="width: 100%" :loading="modelsLoading" class="tech-select">
                <template #prefix><el-icon><Cpu /></el-icon></template>
                <el-option v-for="m in models" :key="m.key" :label="`${m.display_name}`" :value="m.key">
                  <span style="float: left; font-weight: 500;">{{ m.display_name }}</span>
                  <span style="float: right; color: var(--el-text-color-secondary); font-size: 12px">{{ m.engine }}</span>
                </el-option>
              </el-select>
              <div class="form-hint" v-if="currentModelText" style="margin-top: 6px; font-size: 12px; color: var(--el-text-color-secondary);">
                引擎档案: {{ currentModelText }}
              </div>
            </el-form-item>

            <el-form-item label="置信度拦截阈值 (Confidence)">
              <div class="slider-wrap" style="display: flex; align-items: center; gap: 12px; width: 100%;">
                <el-slider v-model="scoreThresh" :min="0.05" :max="0.95" :step="0.01" style="flex: 1;" />
                <el-tag type="info" class="slider-val" effect="plain">{{ (scoreThresh * 100).toFixed(0) }}%</el-tag>
              </div>
              <div class="form-hint" style="font-size: 12px; color: var(--el-text-color-secondary);">
                较高阈值可免疫噪点误报，较低阈值可深挖潜在污染目标。
              </div>
            </el-form-item>
            
            <el-form-item label="后处理扩展栈">
              <el-checkbox-group v-model="enhancementFeatures" class="feature-checkboxes">
                <el-checkbox label="cyclegan" style="display: block;">开启浑水色彩增强 (CycleGAN-TVSBD)</el-checkbox>
                <el-checkbox label="tracking" style="display: block;">启用多目标连续追踪 (ByteTrack)</el-checkbox>
              </el-checkbox-group>
            </el-form-item>

            <el-form-item label="实时流地址（机器配置）">
              <el-input v-model="realtimeSource" disabled placeholder="管理员尚未为当前机器配置 RTSP 地址" />
              <div class="form-hint" style="margin-top: 6px; font-size: 12px; color: var(--el-text-color-secondary);">
                {{ boundRobotName ? `当前绑定机器：${boundRobotName}` : '未获取到绑定机器信息' }}
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" class="results-card panel-card" style="margin-top: 16px;">
          <template #header>
            <div class="panel-header">
              <el-icon><List /></el-icon>
              <span>实时发现清册 (Radar Log)</span>
              <el-tag size="small" type="danger" effect="dark" round style="margin-left: auto;">{{ radarTargetCount }} 目标</el-tag>
            </div>
          </template>

          <div class="timeline-container" style="height: 380px; overflow-y: auto; padding-right: 10px;">
            <el-empty v-if="radarItems.length === 0" description="探针未捕捉到明确污染源..." :image-size="80" />
            <el-timeline v-else>
              <el-timeline-item 
                v-for="(item, index) in radarItems" 
                :key="index" 
                :type="item.isTrash ? 'danger' : 'warning'"
                :hollow="true"
                :timestamp="item.timestamp">
                <div class="log-item" style="background: var(--el-fill-color-light); padding: 8px 12px; border-radius: 6px; border-left: 3px solid var(--el-color-danger);">
                  <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px; display: flex; justify-content: space-between;">
                    <span :class="item.isTrash ? 'trash-text' : 'normal-text'">目标: {{ item.className }}</span>
                    <span v-if="item.source === 'image'" style="font-size: 12px; font-weight: normal; color: var(--el-text-color-secondary);">P: {{ (item.score * 100).toFixed(1) }}%</span>
                    <span v-else style="font-size: 12px; font-weight: normal; color: var(--el-text-color-secondary);">Count: {{ item.count }}</span>
                  </div>
                  <div v-if="item.source === 'image'" style="font-size: 12px; color: var(--el-text-color-regular); font-family: monospace;">COORD: {{ item.bbox }}</div>
                  <div v-else style="font-size: 12px; color: var(--el-text-color-regular); font-family: monospace;">FRAMES: {{ item.frames }}</div>
                  <div style="font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px;">特征: {{ item.isTrash ? '典型海洋废弃物 (High Risk)' : '自然物/生物 (Low Risk)' }}</div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim, Monitor, Cpu, Setting, List, Film, UploadFilled, VideoPlay, DataBoard, Refresh, Warning } from '@element-plus/icons-vue'

import { api } from '../../services/api'
import { useAuthStore } from '../../stores/auth'

type ModelOption = {
  key: string
  display_name: string
  file_name: string
  engine: string
  size_mb: number
}

const activeTab = ref('image')
const models = ref<ModelOption[]>([])
const selectedModelKey = ref('')
const modelsLoading = ref(false)
const inferenceEnabled = ref(false)
const enhancementFeatures = ref(['cyclegan', 'tracking'])
const realtimeSource = ref('0')
const boundRobotName = ref('')
const realtimeSessionId = ref('')
const realtimeStatus = ref<any>(null)
const realtimeStarting = ref(false)
const realtimeRunning = ref(false)
const realtimeFrameUrl = ref('')
const realtimeTargetFps = 20
let realtimeFrameFetching = false
let pendingRealtimeFrameUrl = ''
let realtimeFrameTimer: ReturnType<typeof setInterval> | null = null
let realtimeStatusTimer: ReturnType<typeof setInterval> | null = null

const selectedImage = ref<File | null>(null)
const selectedVideo = ref<File | null>(null)
const scoreThresh = ref(0.25)
const imageDetections = ref<any[]>([])

const parsedImageDetections = computed(() => {
  return imageDetections.value.map((d: any, index: number) => ({
    timestamp: new Date().toLocaleTimeString(),
    source: 'image',
    className: d.class_name,
    score: d.score,
    count: 1,
    frames: '-',
    isTrash: d.is_trash,
    bbox: d.bbox.map((v: number) => v.toFixed(0)).join(', ')
  }))
})

const parsedVideoDetections = computed(() => {
  const result = taskStatus.value?.result || {}
  const classCounts = result.class_counts || {}
  const framesProcessed = Number(result.frames_processed || 0)
  const now = new Date().toLocaleTimeString()
  return Object.entries(classCounts)
    .map(([name, count]: [string, any]) => ({
      timestamp: now,
      source: 'video',
      className: String(name),
      score: 0,
      count: Number(count || 0),
      frames: framesProcessed,
      isTrash: String(name).toLowerCase().includes('trash') || String(name).includes('垃圾'),
      bbox: '-',
    }))
    .sort((a, b) => b.count - a.count)
})

const parsedRealtimeDetections = computed(() => {
  const status = realtimeStatus.value || {}
  const classCounts = status.current_class_counts || status.total_class_counts || {}
  const framesProcessed = Number(status.frames_processed || 0)
  const now = new Date().toLocaleTimeString()
  return Object.entries(classCounts)
    .map(([name, count]: [string, any]) => ({
      timestamp: now,
      source: 'video',
      className: String(name),
      score: 0,
      count: Number(count || 0),
      frames: framesProcessed,
      isTrash: String(name).toLowerCase().includes('trash') || String(name).includes('垃圾'),
      bbox: '-',
    }))
    .sort((a, b) => b.count - a.count)
})

const radarItems = computed(() => {
  if (activeTab.value === 'video') {
    return parsedVideoDetections.value
  }
  if (activeTab.value === 'realtime') {
    return parsedRealtimeDetections.value
  }
  return parsedImageDetections.value
})

const radarTargetCount = computed(() => {
  if (activeTab.value === 'video') {
    return parsedVideoDetections.value.reduce((sum, item) => sum + item.count, 0)
  }
  if (activeTab.value === 'realtime') {
    return parsedRealtimeDetections.value.reduce((sum, item) => sum + item.count, 0)
  }
  return parsedImageDetections.value.length
})
const lastImagePath = ref('')
const sourceImagePreview = ref('')
const resultImagePreview = ref('')
const lastModelStatus = ref('')
const lastModelType = ref<'info' | 'warning' | 'success'>('info')
const imageSubmitting = ref(false)
const videoSubmitting = ref(false)

const currentTaskId = ref('')
const taskStatus = ref<any>(null)
const videoPreviewUrl = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null
const auth = useAuthStore()

const realtimeProgress = computed(() => {
  if (!realtimeStatus.value) return 0
  if (realtimeStatus.value.status === 'queued') return 20
  if (realtimeStatus.value.status === 'running') return 100
  if (realtimeStatus.value.status === 'stopped') return 100
  if (realtimeStatus.value.status === 'failed') return 100
  return 20
})

const imageRecords = ref<any[]>([])
const videoRecords = ref<any[]>([])

const onImageChange = (file: any) => {
  selectedImage.value = file.raw
}

const onVideoChange = (file: any) => {
  selectedVideo.value = file.raw
}

const onExceed = () => {
  ElMessage.warning('单次只允许选择 1 个文件')
}

const currentModelText = computed(() => {
  const found = models.value.find((m) => m.key === selectedModelKey.value)
  if (!found) return '未选择'
  return `${found.display_name} | ${found.engine} | ${found.size_mb} MB`
})

const loadModels = async () => {
  modelsLoading.value = true
  try {
    const { data } = await api.get('/detection/models')
    models.value = data.data.models || []
    selectedModelKey.value = data.data.default_model_key || models.value[0]?.key || ''
    inferenceEnabled.value = Boolean(data.data.inference_enabled)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '加载模型列表失败')
  } finally {
    modelsLoading.value = false
  }
}

const taskStatusText = (status?: string) => {
  if (status === 'queued') return '排队中'
  if (status === 'running') return '运行中'
  if (status === 'stopped') return '已停止'
  if (status === 'finished') return '已完成'
  if (status === 'failed') return '失败'
  return status || '-'
}

const submitImage = async () => {
  if (!selectedImage.value || !selectedModelKey.value) {
    ElMessage.warning('请先选择模型与图片')
    return
  }
  imageSubmitting.value = true
  const formData = new FormData()
  formData.append('file', selectedImage.value)
  formData.append('model_key', selectedModelKey.value)
  formData.append('score_thresh', String(scoreThresh.value))
  formData.append('use_cyclegan', String(enhancementFeatures.value.includes('cyclegan')))
  try {
    const { data } = await api.post('/detection/image', formData)
    imageDetections.value = data.data.detections || []
    lastImagePath.value = data.data.image_path || ''
    sourceImagePreview.value = data.data.source_image || ''
    resultImagePreview.value = data.data.annotated_image || ''
    const modelStatus = data.data.model_status || '-'
    const modelError = data.data.model_error
    if (modelStatus === 'loaded') {
      lastModelStatus.value = `模型推理成功，状态：${modelStatus}`
      lastModelType.value = 'success'
    } else if (modelError) {
      lastModelStatus.value = `已自动回退：${modelError}`
      lastModelType.value = 'warning'
    } else {
      lastModelStatus.value = `当前模式：${modelStatus}`
      lastModelType.value = 'info'
    }
    const cycleganRequested = enhancementFeatures.value.includes('cyclegan')
    const cycleganApplied = Boolean(data.data.cyclegan_applied)
    const cycleganError = data.data.cyclegan_error
    if (cycleganRequested && !cycleganApplied && cycleganError) {
      ElMessage.warning(`色彩增强未生效，已回退原图：${cycleganError}`)
    }
    ElMessage.success('图片检测完成')
    await loadImageRecords()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '图片检测失败')
  } finally {
    imageSubmitting.value = false
  }
}

const submitVideo = async () => {
  if (!selectedVideo.value || !selectedModelKey.value) {
    ElMessage.warning('请先选择模型与视频')
    return
  }
  videoSubmitting.value = true
  const formData = new FormData()
  formData.append('file', selectedVideo.value)
  formData.append('model_key', selectedModelKey.value)
  formData.append('score_thresh', String(scoreThresh.value))
  formData.append('use_cyclegan', String(enhancementFeatures.value.includes('cyclegan')))
  formData.append('use_tracking', String(enhancementFeatures.value.includes('tracking')))
  try {
    const { data } = await api.post('/detection/video', formData)
    taskStatus.value = data.data
    currentTaskId.value = data.data.id
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    pollTimer = setInterval(() => {
      refreshTask()
    }, 1000)
    if (videoPreviewUrl.value) {
      URL.revokeObjectURL(videoPreviewUrl.value)
      videoPreviewUrl.value = ''
    }
    ElMessage.success('视频任务已提交')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '视频任务提交失败')
  } finally {
    videoSubmitting.value = false
  }
}

const refreshTask = async () => {
  if (!currentTaskId.value) return
  try {
    const { data } = await api.get(`/detection/video/tasks/${currentTaskId.value}`)
    taskStatus.value = data.data
    if (data.data.status === 'failed' || data.data.status === 'finished') {
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
    }
    if (data.data.status === 'finished') {
      await loadVideoPreview(currentTaskId.value)
      await loadVideoRecords()
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '刷新任务状态失败')
  }
}

const loadVideoPreview = async (taskId: string) => {
  const resp = await api.get(`/detection/video/tasks/${taskId}/preview`, { responseType: 'blob' })
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value)
  }
  videoPreviewUrl.value = URL.createObjectURL(resp.data)
}

const pollRealtimeFrame = async () => {
  if (!realtimeSessionId.value || !realtimeRunning.value) return
  if (realtimeFrameFetching) return
  realtimeFrameFetching = true
  try {
    const resp = await api.get(`/detection/realtime/sessions/${realtimeSessionId.value}/frame`, { responseType: 'blob' })
    if (!resp.data || (resp.data as Blob).size === 0) return
    const nextUrl = URL.createObjectURL(resp.data)
    const img = new Image()
    img.onload = () => {
      const prev = realtimeFrameUrl.value
      realtimeFrameUrl.value = nextUrl
      if (prev) {
        URL.revokeObjectURL(prev)
      }
      if (pendingRealtimeFrameUrl && pendingRealtimeFrameUrl !== nextUrl) {
        URL.revokeObjectURL(pendingRealtimeFrameUrl)
      }
      pendingRealtimeFrameUrl = ''
    }
    img.onerror = () => {
      URL.revokeObjectURL(nextUrl)
      if (pendingRealtimeFrameUrl && pendingRealtimeFrameUrl !== nextUrl) {
        URL.revokeObjectURL(pendingRealtimeFrameUrl)
      }
      pendingRealtimeFrameUrl = ''
    }
    pendingRealtimeFrameUrl = nextUrl
    img.src = nextUrl
  } catch (error: any) {
    if (error?.response?.status !== 204) {
      // Avoid noisy toasts during transient network jitter.
    }
  } finally {
    realtimeFrameFetching = false
  }
}

const pollRealtimeStatus = async () => {
  if (!realtimeSessionId.value) return
  try {
    const { data } = await api.get(`/detection/realtime/sessions/${realtimeSessionId.value}`)
    realtimeStatus.value = data.data
    const st = String(data.data?.status || '')
    if (st === 'running' || st === 'queued') {
      realtimeRunning.value = true
      return
    }
    if (st === 'failed' || st === 'stopped') {
      realtimeRunning.value = false
      stopRealtimePolling()
    }
  } catch {
    realtimeRunning.value = false
    stopRealtimePolling()
  }
}

const startRealtimePolling = () => {
  stopRealtimePolling()
  pollRealtimeStatus()
  pollRealtimeFrame()
  const frameInterval = 60
  realtimeFrameTimer = setInterval(() => {
    pollRealtimeFrame()
  }, frameInterval)
  realtimeStatusTimer = setInterval(() => {
    pollRealtimeStatus()
  }, 500)
}

const stopRealtimePolling = () => {
  if (realtimeFrameTimer) {
    clearInterval(realtimeFrameTimer)
    realtimeFrameTimer = null
  }
  if (realtimeStatusTimer) {
    clearInterval(realtimeStatusTimer)
    realtimeStatusTimer = null
  }
  realtimeFrameFetching = false
}

const startRealtime = async () => {
  if (!realtimeSource.value || !selectedModelKey.value) {
    ElMessage.warning('请先填写监控源并选择模型')
    return
  }
  realtimeStarting.value = true
  try {
    const { data } = await api.post('/detection/realtime/start', {
      source: realtimeSource.value,
      model_key: selectedModelKey.value,
      score_thresh: scoreThresh.value,
      use_cyclegan: enhancementFeatures.value.includes('cyclegan'),
      use_tracking: enhancementFeatures.value.includes('tracking'),
      realtime_fps: realtimeTargetFps,
    })
    realtimeStatus.value = data.data
    realtimeSessionId.value = data.data.id
    realtimeRunning.value = true
    startRealtimePolling()
    ElMessage.success('实时监控已启动')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '实时监控启动失败')
  } finally {
    realtimeStarting.value = false
  }
}

const stopRealtime = async () => {
  if (!realtimeSessionId.value) return
  try {
    await api.post(`/detection/realtime/sessions/${realtimeSessionId.value}/stop`)
    realtimeRunning.value = false
    await pollRealtimeStatus()
    ElMessage.success('实时监控已停止')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '停止实时监控失败')
  } finally {
    stopRealtimePolling()
  }
}

const reconnectRealtime = async () => {
  if (realtimeRunning.value && realtimeSessionId.value) {
    try {
      await api.post(`/detection/realtime/sessions/${realtimeSessionId.value}/stop`)
    } catch {
      // ignore stop errors during reconnect
    }
  }
  realtimeSessionId.value = ''
  realtimeStatus.value = null
  realtimeRunning.value = false
  if (realtimeFrameUrl.value) {
    URL.revokeObjectURL(realtimeFrameUrl.value)
    realtimeFrameUrl.value = ''
  }
  if (pendingRealtimeFrameUrl) {
    URL.revokeObjectURL(pendingRealtimeFrameUrl)
    pendingRealtimeFrameUrl = ''
  }
  stopRealtimePolling()
  await startRealtime()
}

const loadImageRecords = async () => {
  try {
    const { data } = await api.get('/detection/image/records')
    imageRecords.value = data.data || []
  } catch {
    imageRecords.value = []
  }
}

const loadVideoRecords = async () => {
  try {
    const { data } = await api.get('/detection/video/records')
    videoRecords.value = data.data || []
  } catch {
    videoRecords.value = []
  }
}

const loadRealtimeSourceFromRobot = async () => {
  try {
    const { data } = await api.get('/robots')
    const rows = Array.isArray(data.data) ? data.data : []
    const first = rows[0] || null
    realtimeSource.value = String(first?.rtsp_url || '').trim()
    const code = String(first?.robot_code || '').trim()
    const name = String(first?.name || '').trim()
    boundRobotName.value = code && name ? `${code} / ${name}` : (name || code || '')
  } catch {
    realtimeSource.value = ''
    boundRobotName.value = ''
  }
}

onMounted(async () => {
  if (!auth.user) {
    await auth.fetchMe()
  }
  await loadModels()
  await loadRealtimeSourceFromRobot()
  await loadImageRecords()
  await loadVideoRecords()
})

onBeforeUnmount(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value)
  }
  stopRealtimePolling()
  if (realtimeFrameUrl.value) {
    URL.revokeObjectURL(realtimeFrameUrl.value)
  }
  if (pendingRealtimeFrameUrl) {
    URL.revokeObjectURL(pendingRealtimeFrameUrl)
  }
})
</script>

<style scoped>
.detect-page {
  padding: 20px;
  background: #f8fbff;
  min-height: 100%;
}

.page-header {
  margin-bottom: 24px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 700;
  color: #1a3a5e;
  letter-spacing: 0.5px;
}

.title-icon {
  color: #0f8ec7;
  font-size: 28px;
}

.header-desc {
  margin-top: 8px;
  color: #64819d;
  font-size: 13px;
}

.status-tag {
  font-weight: 600;
  letter-spacing: 0.5px;
}

.panel-card {
  border-radius: 12px;
  border: 1px solid rgba(15, 142, 199, 0.15);
  box-shadow: 0 8px 24px rgba(15, 142, 199, 0.05);
  background: #ffffff;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #2b5f8b;
}

.custom-tabs :deep(.el-tabs__item) {
  font-weight: 600;
  font-size: 15px;
}
.custom-tabs :deep(.el-tabs__active-bar) {
  background-color: #0f8ec7;
}
.custom-tabs :deep(.el-tabs__item.is-active) {
  color: #0f8ec7;
}

.upload-zone {
  padding: 10px 0;
}
.upload-zone :deep(.el-upload-dragger) {
  background: #f5f9fd;
  border: 2px dashed #b9d7ef;
  border-radius: 12px;
  transition: all 0.3s;
}
.upload-zone :deep(.el-upload-dragger:hover) {
  border-color: #0f8ec7;
  background: #f0f7fe;
}

.process-btn {
  border-radius: 8px;
  font-weight: 600;
  letter-spacing: 1px;
  padding: 0 30px;
  background: linear-gradient(135deg, #0f8ec7, #13699c);
  border: none;
}
.process-btn:hover {
  background: linear-gradient(135deg, #13699c, #0d5683);
}

.visual-compare-area {
  margin-top: 24px;
  border-top: 1px dashed #e1ecf6;
  padding-top: 20px;
}

.compare-title {
  font-weight: 600;
  color: #1a3a5e;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-badge {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 20px;
  background: #f4f4f5;
  color: #909399;
}
.status-badge.success {
  background: #e1f3d8;
  color: #67c23a;
}
.status-badge.warning {
  background: #faecd8;
  color: #e6a23c;
}

.compare-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.img-box {
  background: #f9fbfd;
  border: 1px solid #e9f0f6;
  border-radius: 8px;
  padding: 12px;
  position: relative;
}

.img-label {
  position: absolute;
  top: 16px;
  left: 16px;
  background: rgba(0,0,0,0.6);
  color: #fff;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  z-index: 10;
  backdrop-filter: blur(4px);
}
.img-label.highlight {
  background: rgba(15, 142, 199, 0.85);
  font-weight: 600;
}

.preview-img {
  width: 100%;
  height: 360px;
  object-fit: contain;
  border-radius: 6px;
}

.task-monitor {
  margin-top: 24px;
  padding: 20px;
  background: #fdfefe;
  border: 1px solid #e1ecf6;
  border-radius: 12px;
}
.monitor-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
  font-weight: 600;
  color: #385b7d;
}
.progress-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.progress-text {
  font-size: 12px;
  color: #0f8ec7;
  font-weight: 600;
  text-align: right;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}

.tech-select :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d6e5f3 inset;
  background: #fafcff;
}

.feature-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-container::-webkit-scrollbar {
  width: 6px;
}
.timeline-container::-webkit-scrollbar-thumb {
  background: #c3d9eb;
  border-radius: 3px;
}

.log-item {
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
  transition: transform 0.2s;
}
.log-item:hover {
  transform: translateX(2px);
}
.trash-text {
  color: #f56c6c;
}
.normal-text {
  color: #e6a23c;
}

</style>
