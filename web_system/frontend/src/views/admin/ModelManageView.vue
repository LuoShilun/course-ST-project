<template>
  <div class="models-page">
    <div class="page-header">
      <div>
        <h2>检测模型配置</h2>
        <p class="subtitle">管理系统内置的目标检测模型（支持 .pt, .pth, .onnx），配置文件级默认模型权重</p>
      </div>
      <el-upload
        class="upload-demo"
        action="/api/detection/models/upload"
        :headers="uploadHeaders"
        accept=".pt,.pth,.onnx"
        :show-file-list="false"
        :before-upload="beforeUpload"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
      >
        <el-button type="primary" :icon="Upload">上传新模型权重</el-button>
      </el-upload>
    </div>

    <el-card class="box-card glass-card">
      <el-table
        :data="models"
        style="width: 100%"
        v-loading="loading"
        row-key="key"
        :stripe="true"
      >
        <el-table-column prop="file_name" label="模型文件名" min-width="250">
          <template #default="{ row }">
            <div class="file-name-cell">
              <el-icon><Document /></el-icon>
              <span class="file-name">{{ row.display_name || row.file_name || row.key }}</span>
              <el-tag v-if="row.key === defaultModelKey" type="success" size="small" effect="dark" class="default-tag">
                当前默认使用
              </el-tag>
              <el-tag v-if="row.loadable === false" type="warning" size="small" effect="plain" class="default-tag">
                仅展示
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="engine" label="推理引擎" width="120">
          <template #default="{ row }">
            <el-tag :type="getEngineTagType(row.engine)">
              {{ row.engine.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.key !== defaultModelKey && row.key !== 'mock-default' && row.loadable !== false"
              type="primary"
              link
              size="small"
              @click="setDefault(row.key)"
            >
              设为默认
            </el-button>
            <span v-else-if="row.key === defaultModelKey" class="action-text-muted">已设为默认</span>
            <span v-else-if="row.loadable === false" class="action-text-muted">不可设为默认</span>

            <el-popconfirm
              v-if="row.key !== defaultModelKey && row.engine !== 'mock'"
              title="确定要删除此模型文件吗？"
              @confirm="deleteModel(row.key)"
            >
              <template #reference>
                <el-button type="danger" link size="small" class="ml-2">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Document } from '@element-plus/icons-vue'
import { api } from '../../services/api'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const models = ref<any[]>([])
const defaultModelKey = ref('')

const normalizeModelRow = (raw: any) => {
  const key = String(raw?.key ?? raw?.file_name ?? raw?.name ?? '')
  const fileName = String(raw?.file_name ?? raw?.name ?? raw?.key ?? key)
  const displayName = String((raw?.display_name ?? raw?.name ?? fileName) || key)
  return {
    ...raw,
    key,
    file_name: fileName,
    display_name: displayName,
  }
}

const uploadHeaders = {
  Authorization: `Bearer ${auth.token}`
}

const fetchModels = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/detection/models')
    const rawModels = Array.isArray(data.data.models) ? data.data.models : []
    models.value = rawModels.map((m: any) => normalizeModelRow(m)).filter((m: any) => !!m.key)
    defaultModelKey.value = data.data.default_model_key
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '无法加载模型列表')
  } finally {
    loading.value = false
  }
}

const beforeUpload = (file: File) => {
  const allowedExts = ['.pt', '.pth', '.onnx']
  const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
  if (!allowedExts.includes(fileExt)) {
    ElMessage.error('只允许上传 .pt, .pth, .onnx 格式的文件')
    return false
  }
  loading.value = true
  return true
}

const handleUploadSuccess = async (response: any) => {
  loading.value = false
  if (response?.code !== 0) {
    ElMessage.error(response.message || '模型上传失败')
  } else {
    ElMessage.success(response?.message || '模型上传成功')
    await fetchModels()
  }
}

const handleUploadError = (err: any) => {
  loading.value = false
  let msg = err?.response?.data?.message || '上传请求失败'
  try {
    const res = JSON.parse(err.message)
    if (res && res.message) msg = res.message
  } catch (_e) {
    // Ignore JSON error
  }
  ElMessage.error(msg)
}

const setDefault = async (key: string) => {
  try {
    loading.value = true
    await api.post('/detection/models/default', { model_key: key })
    ElMessage.success('默认模型设置成功')
    await fetchModels()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '设置失败')
  } finally {
    loading.value = false
  }
}

const deleteModel = async (key: string) => {
  try {
    loading.value = true
    await api.post('/detection/models/delete', { model_key: key })
    ElMessage.success('模型删除成功')
    await fetchModels()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '删除失败')
  } finally {
    loading.value = false
  }
}

const getEngineTagType = (engine: string) => {
  switch (engine) {
    case 'yolo': return 'primary'
    case 'faster-rcnn': return 'warning'
    case 'onnx': return 'success'
    case 'torch': return 'info'
    case 'mock': return 'info'
    default: return 'info'
  }
}

onMounted(() => {
  fetchModels()
})
</script>

<style scoped>
.models-page {
  padding: 10px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: var(--text-main);
}
.subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--text-sub);
}
.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.file-name {
  font-weight: 500;
  color: var(--text-main);
}
.default-tag {
  margin-left: 6px;
}
.action-text-muted {
  font-size: 13px;
  color: var(--text-sub);
}
.ml-2 {
  margin-left: 8px;
}
</style>
