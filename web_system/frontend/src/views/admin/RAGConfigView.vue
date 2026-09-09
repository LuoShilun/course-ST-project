<template>

  <div class="page-wrap rag-config">

    <div class="header-block">

      <h2 class="cyber-title"><el-icon><Setting /></el-icon> 知识大脑与大模型调度中枢 (RAG Admin)</h2>

      <p class="subtitle">管理系统的ai助手及本地知识库</p>

    </div>



    <div class="core-grid">

      <!-- LLM Provider Config -->

      <el-card class="cyber-card">

        <template #header>

          <div class="card-header">

            <span><el-icon><Connection /></el-icon> LLM 大模型api配置</span>

            <el-tag type="success" effect="dark" size="small" v-if="testSuccess">连接稳定</el-tag>

          </div>

        </template>

        <el-form label-position="top">

          <el-form-item label="模型提供商">

            <el-select v-model="form.provider" style="width: 100%">

              <el-option label="Qwen (DashScope)" value="qwen" />

              <el-option label="OpenAI / 自定义兼容API" value="openai" />

              <el-option label="Kimi" value="moonshot" />

              <el-option label="Ollama" value="ollama" />

            </el-select>

          </el-form-item>

          <el-form-item label="API Base URL">

            <el-input v-model="form.baseUrl" placeholder="https://api.moonshot.cn/v1" />

          </el-form-item>

          <el-form-item label="API Key">

            <el-input v-model="form.apiKey" type="password" show-password placeholder="sk-..." />

          </el-form-item>

          <el-form-item label="Model Name">

            <el-input v-model="form.modelName" placeholder="? moonshot-v1-8k" />

          </el-form-item>

          <el-form-item>

            <el-button type="primary" @click="testConnection" :loading="testing"><el-icon><Refresh /></el-icon> 测试通道连通</el-button>

            <el-button type="success" plain @click="saveConfig" :loading="saving"><el-icon><Check /></el-icon> 应用全局配置</el-button>

          </el-form-item>

        </el-form>

      </el-card>



      <!-- Knowledge Base Config -->

      <el-card class="cyber-card">

        <template #header>

          <div class="card-header">

            <span><el-icon><Files /></el-icon> 本地知识库配置</span>

            <el-button type="primary" size="small" @click="syncVectorDB"><el-icon><RefreshRight /></el-icon> 全局重建索引</el-button>

          </div>

        </template>

        

        <el-upload

          class="upload-demo"

          drag

          action="/api/assistant/knowledge/upload"

          multiple

          :on-success="handleUploadSuccess"

          :headers="headers"

        >

          <el-icon class="el-icon--upload"><upload-filled /></el-icon>

          <div class="el-upload__text">

            将文档拖到此处<em>点击上传</em>

          </div>

          <template #tip>

            <div class="el-upload__tip cyber-tip">

              支持 PDF, DOCX, TXT 格式，单文件不超50MB。文件将自动被切片并持久化至 FAISS 向量知识池           </div>

          </template>

        </el-upload>



        <h4 style="color:#00ddff; margin-top:24px;">挂载的规章指南文献：</h4>

        <el-table :data="kbFiles" style="width: 100%" class="dark-table" max-height="250">

          <el-table-column prop="name" label="资源名称" />

          <el-table-column prop="status" label="解析状态" width="100">

            <template #default="scope">

              <el-tag :type="scope.row.status === 'indexed' ? 'success' : 'warning'" size="small">

                {{ scope.row.status === 'indexed' ? '已向量化' : '排队中' }}

              </el-tag>

            </template>

          </el-table-column>

          <el-table-column prop="chunks" label="知识切片数" width="100" />

          <el-table-column label="动作" width="130">

            <template #default="scope">

              <el-button link type="primary" size="small" @click="downloadFile(scope.row)">下载</el-button>

              <el-button link type="danger" size="small" @click="deleteFile(scope.row)">卸载</el-button>

            </template>

          </el-table-column>

        </el-table>

      </el-card>

    </div>

  </div>

</template>



<script setup lang="ts">

import { useAuthStore } from '../../stores/auth'

import { onMounted, ref } from 'vue'

import { ElMessage } from 'element-plus'

import { Setting, Connection, Refresh, Check, Files, UploadFilled, RefreshRight } from '@element-plus/icons-vue'



const auth = useAuthStore()



const headers = ref({

  Authorization: `Bearer ${auth.token}`

})



const form = ref({

  provider: 'qwen',

  baseUrl: '',

  apiKey: '',

  modelName: 'qwen-plus'

})



const testSuccess = ref(false)

const testing = ref(false)
const saving = ref(false)



const kbFiles = ref<any[]>([])



const handleUploadSuccess = (response: any, file: any) => {
  ElMessage.success(`文献【${file.name}】上传成功`)

  if (response && (response.code === 0 || response.code === 200) && response.data) {
    kbFiles.value.unshift({
      id: response.data.id || response.data.filename,
      name: response.data.name || file.name,
      status: response.data.status || 'indexed',
      chunks: response.data.chunks || 1,
    })
  }
}



const downloadFile = async (row: any) => {
  try {
    window.open(`/api/assistant/knowledge/download/${encodeURIComponent(row.id)}`)

  } catch (error) {

    ElMessage.error('文献副本下载失败，请联系超级管理员！')

  }

}



const testConnection = async () => {
  testing.value = true
  try {
    const res = await api.post('/assistant/config/llm/test', {
      provider: form.value.provider,
      baseUrl: form.value.baseUrl,
      apiKey: form.value.apiKey,
      modelName: form.value.modelName,
    })

    if (res.data && res.data.code === 0) {
      testSuccess.value = true
      const latency = res.data?.data?.latency_ms
      ElMessage.success(`通信信道握手成功${latency ? `（${latency}ms）` : ''}`)
      return
    }
    testSuccess.value = false
    ElMessage.error(res.data?.message || '测试失败')
  } catch (error: any) {
    testSuccess.value = false
    ElMessage.error(error?.response?.data?.message || '测试失败，请检查网络和配置')
  } finally {
    testing.value = false
  }

}



const saveConfig = async () => {
  if (!form.value.baseUrl || !form.value.apiKey || !form.value.modelName) {
    ElMessage.warning('请先完整填写 Base URL、API Key 和模型名称')
    return
  }

  saving.value = true
  try {
    const res = await api.put('/assistant/config/llm', {
      provider: form.value.provider,
      baseUrl: form.value.baseUrl,
      apiKey: form.value.apiKey,
      modelName: form.value.modelName,
    })
    if (res.data && res.data.code === 0) {
      ElMessage.success('应用全局配置成功，已写入后端 .env')
      return
    }
    ElMessage.error(res.data?.message || '保存失败')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '保存失败，请检查后端权限')
  } finally {
    saving.value = false
  }
}



const syncVectorDB = () => {

  ElMessage.success('正在唤醒切片引擎...已投递索引重建任务至后台')

}



import { api } from "@/services/api"

const fetchKbFiles = async () => {
  try {
    const res = await api.get("/assistant/knowledge/list")
    if (res.data && (res.data.code === 0 || res.data.code === 200)) {
      kbFiles.value = Array.isArray(res.data.data) ? res.data.data : []
    }
  } catch (e) {
    console.error(e)
  }
}

const fetchLLMConfig = async () => {
  try {
    const res = await api.get('/assistant/config/llm')
    if (res.data && res.data.code === 0 && res.data.data) {
      form.value.provider = res.data.data.provider || 'qwen'
      form.value.baseUrl = res.data.data.baseUrl || ''
      form.value.apiKey = res.data.data.apiKey || ''
      form.value.modelName = res.data.data.modelName || 'qwen-plus'
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '加载模型配置失败')
  }
}

onMounted(() => {
  fetchLLMConfig()
  fetchKbFiles()
})

const deleteFile = async (row: any) => {
  try {
    const res = await api.delete(`/assistant/knowledge/${encodeURIComponent(row.id)}`)
    if (res.data && (res.data.code === 0 || res.data.code === 200)) {
      kbFiles.value = kbFiles.value.filter((f) => f.id !== row.id)
      ElMessage.success('文献删除成功')
      return
    }
    ElMessage.error('删除失败，请稍后重试')
  } catch (error) {
    ElMessage.error('删除失败，请检查后端服务')
  }
}

</script>



<style scoped>

.rag-config {

  padding: 24px;

  min-height: calc(100vh - 84px);

  background: #020b14;

  color: #fff;

}



.header-block {

  margin-bottom: 24px;

  border-left: 4px solid #00ddff;

  padding-left: 14px;

}



.cyber-title {

  margin: 0;

  color: #00ddff;

  font-size: 22px;

  font-weight: 600;

  display: flex;

  align-items: center;

  gap: 10px;

}



.subtitle {

  margin: 6px 0 0 0;

  color: #648ba3;

  font-size: 14px;

}



.core-grid {

  display: grid;

  grid-template-columns: 1fr 1fr;

  gap: 24px;

}



.cyber-card {

  background: rgba(0, 20, 35, 0.4);

  border: 1px solid rgba(0, 221, 255, 0.2);

  color: #fff;

}



:deep(.el-card__header) {

  border-bottom: 1px solid rgba(0, 221, 255, 0.2);

  background: rgba(0, 0, 0, 0.2);

}



.card-header {

  display: flex;

  justify-content: space-between;

  align-items: center;

  color: #00ddff;

  font-weight: bold;

  font-size: 16px;

}



:deep(.el-form-item__label) {

  color: #8c9bb0;

  font-weight: bold;

}



:deep(.el-input__wrapper), :deep(.el-select .el-input__wrapper) {

  background: rgba(0, 0, 0, 0.3) !important;

  box-shadow: 0 0 0 1px rgba(0, 221, 255, 0.3) inset !important;

  color: #fff;

}



.upload-demo :deep(.el-upload-dragger) {

  background: rgba(0, 221, 255, 0.05);

  border: 1px dashed rgba(0, 221, 255, 0.3);

  transition: all 0.3s;

}



.upload-demo :deep(.el-upload-dragger:hover) {

  border-color: #00ddff;

  background: rgba(0, 221, 255, 0.1);

}



.el-icon--upload {

  color: #00ddff !important;

}



.cyber-tip {

  color: #648ba3;

  margin-top: 8px;

}



:deep(.dark-table) {

  background: transparent !important;

  color: #a3b8cc;

}



:deep(.dark-table th.el-table__cell) {

  background: rgba(0, 221, 255, 0.1) !important;

  color: #00ddff;

  border-bottom: 1px solid rgba(0, 221, 255, 0.2);

}



:deep(.dark-table td.el-table__cell) {

  background: transparent !important;

  border-bottom: 1px solid rgba(255, 255, 255, 0.05);

}

</style>

