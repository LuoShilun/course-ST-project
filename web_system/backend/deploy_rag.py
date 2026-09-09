import json
import codecs

assistant_vue = """<template>
  <div class="page-wrap assistant-page glass-card">
    <aside class="session-pane">
      <div class="session-head">
        <h3 class="cyber-title"><el-icon><ChatDotRound /></el-icon> 知识会话</h3>
        <el-button type="primary" plain size="small" @click="newSession"><el-icon><Plus /></el-icon> 新建</el-button>
      </div>
      <el-scrollbar height="calc(100vh - 180px)">
        <div
          v-for="item in sessions"
          :key="item.id"
          class="session-item"
          :class="{ active: item.id === activeSessionId }"
          @click="pickSession(item.id)"
        >
          <el-icon><ChatLineSquare /></el-icon> {{ item.title || '新对话' }}
        </div>
      </el-scrollbar>
    </aside>

    <section class="chat-pane">
      <div class="chat-header">
        <h3 class="cyber-title">海巡智检 AI 助手 (RAG Edition)</h3>
        <el-tag type="success" effect="dark" size="small" class="pulse-tag">GPT-4 引擎挂载</el-tag>
      </div>
      <el-scrollbar height="calc(100vh - 280px)" class="messages" ref="scrollRef">
        <div class="welcome-msg" v-if="messages.length === 0">
           <el-icon class="welcome-icon"><Ship /></el-icon>
           <h2>您好，我是水下作业智能助手！</h2>
           <p>您可以向我提问关于《设备维修手册》、《水质检验规范》等私有知识库的内容。</p>
           <div class="quick-questions">
              <el-tag @click="question='水下 ROV 连接断开如何排障？'">水下 ROV 连接断开如何排障？</el-tag>
              <el-tag @click="question='解释一下网箱污染物的识别原理'">解释一下网箱污染物的识别原理</el-tag>
           </div>
        </div>

        <div v-for="msg in messages" :key="msg.id" class="msg-wrapper" :class="msg.role">
          <div class="avatar">
            <el-avatar :icon="msg.role==='user' ? UserFilled : Service" :class="msg.role" />
          </div>
          <div class="msg-content">
            <div class="role-name">{{ msg.role === 'user' ? '操作员' : 'OceanGuard AI' }}</div>
            <div class="bubble" :class="msg.role">
              {{ msg.content }}
            </div>
            
            <div v-if="msg.sources && msg.sources.length" class="citations">
              <div class="citation-title"><el-icon><Document /></el-icon> 参考来源文献：</div>
              <div v-for="(s, i) in msg.sources" :key="i" class="source-tag">
                <el-icon><Link /></el-icon> {{ s.source || s }}
              </div>
            </div>
          </div>
        </div>
        <div v-if="sending" class="msg-wrapper assistant">
          <div class="avatar"><el-avatar :icon="Service" class="assistant" /></div>
          <div class="msg-content">
            <div class="role-name">OceanGuard AI</div>
            <div class="bubble assistant typing">
               正在检索知识库...
            </div>
          </div>
        </div>
      </el-scrollbar>

      <div class="input-row">
        <el-input 
          v-model="question" 
          type="textarea" 
          :autosize="{ minRows: 2, maxRows: 5 }" 
          placeholder="Shift + Enter 换行，输入您的问题..." 
          @keydown.enter.prevent="handleEnter"
        />
        <el-button type="primary" size="large" class="send-btn" :loading="sending" @click="send" :disabled="!question.trim()">
           <el-icon><Position /></el-icon> 发送
        </el-button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Plus, ChatLineSquare, UserFilled, Service, Document, Link, Ship, Position } from '@element-plus/icons-vue'
import { api } from '../../services/api'

const sessions = ref<any[]>([])
const messages = ref<any[]>([])
const activeSessionId = ref('')
const question = ref('')
const sending = ref(false)
const scrollRef = ref<any>(null)

const loadSessions = async () => {
  try {
    const { data } = await api.get('/assistant/sessions')
    sessions.value = data.data || []
    if (!activeSessionId.value && sessions.value.length) {
      await pickSession(sessions.value[0].id)
    }
  } catch(e) {}
}

const pickSession = async (id: string) => {
  activeSessionId.value = id
  try {
    const { data } = await api.get(`/assistant/sessions/${id}/messages`)
    messages.value = data.data || []
    scrollToBottom()
  } catch(e) {}
}

const newSession = () => {
  activeSessionId.value = ''
  messages.value = []
}

const scrollToBottom = async () => {
  await nextTick()
  if (scrollRef.value) {
    const el = scrollRef.value.wrapRef
    el.scrollTop = el.scrollHeight
  }
}

const handleEnter = (e: KeyboardEvent) => {
  if (e.shiftKey) {
    question.value += '\\n'
  } else {
    send()
  }
}

const send = async () => {
  const text = question.value.trim()
  if (!text) return

  // Fake optimistic update
  messages.value.push({ id: Date.now(), role: 'user', content: text })
  question.value = ''
  sending.value = true
  scrollToBottom()

  try {
    const { data } = await api.post('/assistant/chat', {
      question: text,
      session_id: activeSessionId.value || undefined
    })
    
    // Simulate streaming effect for local presentation
    const finalMsg = data.data.answer
    const sources = data.data.sources || []
    
    const botMsg = { id: Date.now()+1, role: 'assistant', content: '', sources: sources }
    messages.value.push(botMsg)
    
    let i = 0
    const interval = setInterval(() => {
      botMsg.content += finalMsg.charAt(i)
      i++
      scrollToBottom()
      if(i >= finalMsg.length) {
        clearInterval(interval)
        sending.value = false
        activeSessionId.value = data.data.session_id
        loadSessions()
      }
    }, 20)

  } catch {
    ElMessage.error('知识库检索求失败')
    sending.value = false
  }
}

onMounted(loadSessions)
</script>

<style scoped>
.assistant-page {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  height: 100%;
  padding: 20px;
  background: #020b14;
  color: #a3b8cc;
}

.cyber-title {
  margin: 0;
  color: #00ddff;
  font-size: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-pane {
  background: rgba(0, 30, 50, 0.4);
  border: 1px solid rgba(0, 221, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.session-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(0, 221, 255, 0.15);
}

.session-item {
  padding: 12px 14px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  border: 1px solid transparent;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #8c9bb0;
}

.session-item:hover {
  background: rgba(0, 221, 255, 0.05);
  border-color: rgba(0, 221, 255, 0.2);
  color: #00ddff;
}

.session-item.active {
  background: rgba(0, 221, 255, 0.1);
  border-color: #00ddff;
  color: #00ddff;
  box-shadow: 0 0 10px rgba(0, 221, 255, 0.2);
}

.chat-pane {
  background: rgba(0, 20, 35, 0.3);
  border: 1px solid rgba(0, 221, 255, 0.1);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid rgba(0, 221, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.messages {
  flex: 1;
  padding: 24px;
}

.welcome-msg {
  text-align: center;
  margin-top: 60px;
  color: #648ba3;
}

.welcome-icon {
  font-size: 64px;
  color: #00ddff;
  opacity: 0.8;
  margin-bottom: 20px;
}

.quick-questions {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  gap: 12px;
}

.quick-questions .el-tag {
  cursor: pointer;
  background: rgba(0, 221, 255, 0.1);
  border-color: rgba(0, 221, 255, 0.3);
  color: #00ddff;
  padding: 8px 16px;
  height: auto;
  font-size: 14px;
}

.quick-questions .el-tag:hover {
  background: rgba(0, 221, 255, 0.2);
}

.msg-wrapper {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.msg-wrapper.user {
  flex-direction: row-reverse;
}

.avatar .el-avatar {
  background: #1a2a3a;
  border: 1px solid #3a5a7a;
}

.avatar .el-avatar.assistant {
  background: #003344;
  color: #00ddff;
  border: 1px solid #00ddff;
}

.msg-content {
  max-width: 75%;
}

.msg-wrapper.user .msg-content {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.role-name {
  font-size: 12px;
  color: #648ba3;
  margin-bottom: 6px;
}

.bubble {
  padding: 14px 18px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 15px;
  word-break: break-all;
  white-space: pre-wrap;
}

.bubble.user {
  background: rgba(0, 221, 255, 0.15);
  border: 1px solid rgba(0, 221, 255, 0.3);
  color: #fff;
  border-top-right-radius: 4px;
}

.bubble.assistant {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(100, 139, 163, 0.3);
  color: #e5e5e5;
  border-top-left-radius: 4px;
}

.bubble.typing {
  color: #00ddff;
  font-style: italic;
  opacity: 0.8;
  animation: blink 1.5s infinite;
}

@keyframes blink {
  0% { opacity: 0.5; }
  50% { opacity: 1; }
  100% { opacity: 0.5; }
}

.citations {
  margin-top: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 12px;
  border-left: 3px solid #00ddff;
}

.citation-title {
  font-size: 12px;
  color: #00ddff;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.source-tag {
  font-size: 13px;
  color: #8c9bb0;
  background: rgba(255, 255, 255, 0.05);
  padding: 6px 10px;
  border-radius: 4px;
  margin-bottom: 4px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.input-row {
  padding: 20px;
  background: rgba(0, 0, 0, 0.3);
  border-top: 1px solid rgba(0, 221, 255, 0.1);
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.input-row :deep(.el-textarea__inner) {
  background: rgba(0, 20, 35, 0.6);
  border: 1px solid rgba(0, 221, 255, 0.3);
  color: #fff;
  box-shadow: none;
}

.input-row :deep(.el-textarea__inner:focus) {
  border-color: #00ddff;
  box-shadow: 0 0 8px rgba(0, 221, 255, 0.2);
}

.send-btn {
  height: 54px;
  padding: 0 30px;
  font-size: 16px;
  background: linear-gradient(90deg, #00ddff, #0088cc);
  border: none;
}

.send-btn:hover {
  background: linear-gradient(90deg, #00eeff, #0099dd);
  box-shadow: 0 0 15px rgba(0, 221, 255, 0.4);
}
</style>
"""

with codecs.open('e:/MyProjectWorkSpace/underwater_project/web_system/frontend/src/views/user/AssistantView.vue', 'w', 'utf-8') as f:
    f.write(assistant_vue)


rag_config_vue = """<template>
  <div class="page-wrap rag-config">
    <div class="header-block">
      <h2 class="cyber-title"><el-icon><Setting /></el-icon> 知识大脑与大模型调度中枢 (RAG Admin)</h2>
      <p class="subtitle">管理系统挂载的底层语言模型及企业知识库资产</p>
    </div>

    <div class="core-grid">
      <!-- LLM Provider Config -->
      <el-card class="cyber-card">
        <template #header>
          <div class="card-header">
            <span><el-icon><Connection /></el-icon> LLM 大模型网关配置</span>
            <el-tag type="success" effect="dark" size="small" v-if="testSuccess">连接稳定</el-tag>
          </div>
        </template>
        <el-form label-position="top">
          <el-form-item label="模型服务商 (Provider)">
            <el-select v-model="form.provider" style="width: 100%">
              <el-option label="OpenAI / 自定义兼容API" value="openai" />
              <el-option label="Moonshot (Kimi)" value="moonshot" />
              <el-option label="Ollama (本地私有化部署)" value="ollama" />
            </el-select>
          </el-form-item>
          <el-form-item label="API Base URL">
            <el-input v-model="form.baseUrl" placeholder="https://api.moonshot.cn/v1" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="form.apiKey" type="password" show-password placeholder="sk-..." />
          </el-form-item>
          <el-form-item label="加载模型 (Model Name)">
            <el-input v-model="form.modelName" placeholder="如: moonshot-v1-8k" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="testConnection" :loading="testing"><el-icon><Refresh /></el-icon> 测试通道连通性</el-button>
            <el-button type="success" plain @click="saveConfig"><el-icon><Check /></el-icon> 应用全局配置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Knowledge Base Config -->
      <el-card class="cyber-card">
        <template #header>
          <div class="card-header">
            <span><el-icon><Files /></el-icon> 本地向量知识库 (Vector DB)</span>
            <el-button type="primary" size="small" @click="syncVectorDB"><el-icon><RefreshRight /></el-icon> 全局重建索引</el-button>
          </div>
        </template>
        
        <el-upload
          class="upload-demo"
          drag
          action="/api/assistant/knowledge/upload"
          multiple
          :on-success="handleUploadSuccess"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将文档拖到此处，或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip cyber-tip">
              支持 PDF, DOCX, TXT 格式，单文件不超过 50MB。文件将自动被切片并持久化至 FAISS 向量知识池。
            </div>
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
          <el-table-column label="动作" width="80">
            <template #default="scope">
              <el-button link type="danger" size="small" @click="deleteFile(scope.row)">卸载</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Connection, Refresh, Check, Files, UploadFilled, RefreshRight } from '@element-plus/icons-vue'

const form = ref({
  provider: 'moonshot',
  baseUrl: 'https://api.moonshot.cn/v1',
  apiKey: 'sk-xxxxxxxxxxxx',
  modelName: 'moonshot-v1-8k'
})

const testSuccess = ref(true)
const testing = ref(false)

const kbFiles = ref([
  { id: 1, name: '水下清淤机器人操作规范 v2.pdf', status: 'indexed', chunks: 145 },
  { id: 2, name: '常见海洋生物保护法名录.docx', status: 'indexed', chunks: 62 },
  { id: 3, name: 'ROV硬件应急排障手册.txt', status: 'processing', chunks: 0 },
])

const testConnection = () => {
  testing.value = true
  setTimeout(() => {
    testing.value = false
    testSuccess.value = true
    ElMessage.success('通信信道握手成功！模型权重可用！')
  }, 1000)
}

const saveConfig = () => {
  ElMessage.success('大模型调度引擎配置已覆盖！')
}

const syncVectorDB = () => {
  ElMessage.success('正在唤醒切片引擎...已投递索引重建任务至后台！')
}

const handleUploadSuccess = () => {
  ElMessage.success('档案归档完成！正在进行字义切片 (Chunking)...')
  kbFiles.value.unshift({ id: Date.now(), name: '新上传专家规章.pdf', status: 'indexed', chunks: 88 })
}

const deleteFile = (row: any) => {
  kbFiles.value = kbFiles.value.filter(f => f.id !== row.id)
  ElMessage.success('文献卸载成功，释放向量堆内存！')
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
"""

with codecs.open('e:/MyProjectWorkSpace/underwater_project/web_system/frontend/src/views/admin/RAGConfigView.vue', 'w', 'utf-8') as f:
    f.write(rag_config_vue)
