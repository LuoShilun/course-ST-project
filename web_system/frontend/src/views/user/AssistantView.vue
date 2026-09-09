<template>
  <div class="page-wrap assistant-page glass-card">
    <aside class="session-pane">
      <div class="session-head">
        <h3 class="cyber-title"><el-icon><ChatDotRound /></el-icon> 知识会话</h3>
        <el-button type="primary" plain size="small" @click="newSession" class="action-btn">
          <el-icon><Plus /></el-icon> 新建
        </el-button>
      </div>
      <el-scrollbar class="session-list">
        <transition-group name="list-fade">
          <div
            v-for="item in sessions"
            :key="item.id"
            class="session-item"
            :class="{ active: item.id === activeSessionId }"
            @click="pickSession(item.id)"
          >
            <div class="session-main">
              <el-icon class="session-icon" :class="{ 'glow': item.id === activeSessionId }"><ChatLineSquare /></el-icon>
              <div class="session-info">
                <span class="session-title">{{ item.title || '新对话' }}</span>
                <span class="session-time" v-if="item.created_at">{{ formatTime(item.created_at) }}</span>
              </div>
            </div>
            <el-button
              class="session-delete"
              type="danger"
              text
              size="small"
              @click.stop="removeSession(item.id)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </transition-group>
      </el-scrollbar>
    </aside>

    <section class="chat-pane">
      <div class="chat-header blur-bg">
        <div class="header-left">
          <h3 class="cyber-title">海巡智检 AI 助手 (RAG Edition)</h3>
          <span class="status-dot"></span>
          <span class="status-text">在线</span>
        </div>
        <el-tag type="success" effect="dark" size="small" class="pulse-tag">
          <el-icon><Cpu /></el-icon> Qwen RAG
        </el-tag>
      </div>

      <el-scrollbar class="messages" ref="scrollRef">
        <div class="welcome-msg slide-up" v-if="messages.length === 0">
           <div class="welcome-avatar">
             <el-icon class="welcome-icon pulse-glow"><Ship /></el-icon>
           </div>
           <h2>您好，我是水下作业智能助手！</h2>
           <p class="welcome-subtitle">您可以向我提问关于《设备维修手册》、《水质检验规范》等私有知识库的内容。</p>
           
           <div class="suggestions-grid">
             <div class="suggestion-card" @click="question='水下 ROV 连接断开如何排障？'">
               <el-icon class="suggestion-icon"><Warning /></el-icon>
               <div class="text">水下 ROV 连接断开如何排障？</div>
             </div>
             <div class="suggestion-card" @click="question='解释一下网箱污染物的识别原理'">
               <el-icon class="suggestion-icon"><Microphone /></el-icon>
               <div class="text">解释一下网箱污染物的识别原理</div>
             </div>
             <div class="suggestion-card" @click="question='如果水下能见度极低，视频模型还能工作吗？'">
               <el-icon class="suggestion-icon"><VideoCamera /></el-icon>
               <div class="text">能见度低时，视频模型还能工作吗？</div>
             </div>
           </div>
        </div>

        <div class="msg-container">
          <div v-for="msg in messages" :key="msg.id" class="msg-wrapper pop-in" :class="msg.role">
            <div class="avatar">
              <el-avatar :icon="msg.role==='user' ? UserFilled : Service" :class="msg.role" />
            </div>
            <div class="msg-content">
              <div class="role-name">{{ msg.role === 'user' ? '操作员' : 'OceanGuard AI' }}</div>
              
              <!-- Markdown Render for Assistant, Plain Text for User -->
              <div class="bubble" :class="msg.role">
                <template v-if="msg.role === 'assistant'">
                  <div class="md-content" v-html="renderMarkdown(msg.content)"></div>
                </template>
                <template v-else>
                  {{ msg.content }}
                </template>
              </div>
              
              <div v-if="msg.sources && msg.sources.length" class="citations">
                <div class="citation-title"><el-icon><Document /></el-icon> 挖掘自以下本地知识块：</div>
                <div class="source-list">
                  <el-tooltip
                    v-for="(s, i) in msg.sources"
                    :key="i"
                    :content="s.text || '暂无详细文本记录'"
                    placement="top"
                    effect="dark"
                    :show-after="300"
                  >
                    <div class="source-tag">
                      <el-icon><Link /></el-icon>
                      <span class="source-name">{{ s.source || s }}</span>
                    </div>
                  </el-tooltip>
                </div>
              </div>
            </div>
          </div>

          <div v-if="sending && streamingAssistantId === null" class="msg-wrapper assistant pop-in">
            <div class="avatar">
              <el-avatar :icon="Service" class="assistant glow-avatar" />
            </div>
            <div class="msg-content">
              <div class="role-name">OceanGuard AI</div>
              <div class="bubble assistant typing-bubble">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-text">正在检索深海知识库网络...</span>
              </div>
            </div>
          </div>
        </div>
      </el-scrollbar>

      <div class="input-area blur-bg">
        <div class="input-panel">
          <el-input
            v-model="question"
            class="assistant-input"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            :maxlength="2000"
            show-word-limit
            placeholder="输入您的问题，如：请根据当前知识库给出排障 SOP..."
            @keydown.enter.prevent="handleEnter"
          />
          <div class="input-actions">
            <el-tooltip content="清空输入框" placement="top">
              <el-button class="icon-btn" text type="info" @click="clearInput" :disabled="!question" circle>
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-tooltip>
            <div class="action-right">
              <el-button
                type="primary"
                class="send-btn"
                :loading="sending"
                @click="send"
                :disabled="!question.trim() || sending"
                circle
              >
                <el-icon v-if="!sending"><Position /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  ChatDotRound, Plus, ChatLineSquare, UserFilled, Service, Document, 
  Link, Ship, Position, Delete, Cpu, Warning, Microphone, VideoCamera 
} from '@element-plus/icons-vue'
import { api } from '../../services/api'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const sessions = ref<any[]>([])
const messages = ref<any[]>([])
const activeSessionId = ref('')
const question = ref('')
const sending = ref(false)
const streamingAssistantId = ref<number | null>(null)
const scrollRef = ref<any>(null)

const renderMarkdown = (text: string) => {
  if (!text) return ''
  const rawHtml = marked.parse(text, { async: false }) as string
  return DOMPurify.sanitize(rawHtml)
}

const formatTime = (timeStr: string) => {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`
}

const loadSessions = async () => {
  try {
    const { data } = await api.get('/assistant/sessions')
    sessions.value = data.data || []
    if (!activeSessionId.value && sessions.value.length) {
      await pickSession(sessions.value[0].id)
    }
  } catch (e) {
    ElMessage.error('加载会话失败，请重新登录后重试')
  }
}

const pickSession = async (id: string) => {
  activeSessionId.value = id
  try {
    const { data } = await api.get(`/assistant/sessions/${id}/messages`)
    messages.value = data.data || []
    scrollToBottom()
  } catch (e) {
    ElMessage.error('加载会话消息失败')
  }
}

const newSession = () => {
  activeSessionId.value = ''
  messages.value = []
  question.value = ''
}

const clearInput = () => {
  question.value = ''
}

const removeSession = async (id: string) => {
  try {
    await ElMessageBox.confirm('删除该会话记录后将无法找回，是否继续？', '粉碎会话', {
      confirmButtonText: '确认粉碎',
      cancelButtonText: '取消',
      type: 'warning',
      customClass: 'cyber-confirm'
    })

    const { data } = await api.delete(`/assistant/sessions/${id}`)
    if (!data || data.code !== 0) {
      throw new Error(data?.message || '删除失败')
    }

    ElMessage.success('会话网络物理隔离完成。')

    if (activeSessionId.value === id) {
      activeSessionId.value = ''
      messages.value = []
    }

    await loadSessions()
    if (!sessions.value.length) {
      newSession()
    }
  } catch (e: any) {
    if (e === 'cancel' || e === 'close') {
      return
    }
    ElMessage.error(e?.message || '断开会话失败')
  }
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
    question.value += '\n'
  } else {
    send()
  }
}

const send = async () => {
  const text = question.value.trim()
  if (!text) return

  const userMsgId = Date.now()
  const assistantMsgId = userMsgId + 1
  messages.value.push({ id: userMsgId, role: 'user', content: text })
  messages.value.push({ id: assistantMsgId, role: 'assistant', content: '', sources: [] })
  question.value = ''
  sending.value = true
  streamingAssistantId.value = assistantMsgId
  scrollToBottom()

  try {
    const base = String(api.defaults.baseURL || '/api').replace(/\/$/, '')
    const token = localStorage.getItem('uw_token') || ''
    const resp = await fetch(`${base}/assistant/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({
        question: text,
        session_id: activeSessionId.value || undefined
      })
    })

    if (!resp.ok) {
      let msg = '请求解析引擎失败'
      try {
        const errJson = await resp.json()
        msg = String(errJson?.message || msg)
      } catch {
        // ignore parse failure
      }
      throw new Error(msg)
    }

    if (!resp.body) {
      throw new Error('流式连接不可用，请稍后重试')
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let finalSources: any[] = []
    let finalSessionId = activeSessionId.value

    const processEvent = (eventText: string) => {
      const lines = eventText
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.startsWith('data:'))
      if (!lines.length) return

      const payloadRaw = lines.map((line) => line.slice(5).trim()).join('')
      if (!payloadRaw) return

      let evt: any = null
      try {
        evt = JSON.parse(payloadRaw)
      } catch {
        return
      }

      if (evt.type === 'start') {
        if (evt.session_id) {
          finalSessionId = String(evt.session_id)
          activeSessionId.value = finalSessionId
        }
        return
      }

      const idx = messages.value.findIndex((m) => m.id === assistantMsgId)
      if (idx < 0) return

      if (evt.type === 'delta') {
        messages.value[idx].content = `${messages.value[idx].content || ''}${String(evt.content || '')}`
        scrollToBottom()
        return
      }

      if (evt.type === 'done') {
        messages.value[idx].content = String(evt.answer || messages.value[idx].content || '')
        finalSources = Array.isArray(evt.sources) ? evt.sources : []
        messages.value[idx].sources = finalSources
        if (evt.session_id) {
          finalSessionId = String(evt.session_id)
          activeSessionId.value = finalSessionId
        }
      }
    }

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let splitIndex = buffer.indexOf('\n\n')
      while (splitIndex >= 0) {
        const eventText = buffer.slice(0, splitIndex)
        buffer = buffer.slice(splitIndex + 2)
        processEvent(eventText)
        splitIndex = buffer.indexOf('\n\n')
      }
    }
    if (buffer.trim()) {
      processEvent(buffer)
    }

    sending.value = false
    streamingAssistantId.value = null
    if (finalSessionId) {
      activeSessionId.value = finalSessionId
    }
    await loadSessions()
    scrollToBottom()

  } catch (e: any) {
    messages.value = messages.value.filter((m) => m.id !== assistantMsgId)
    ElMessage.error(e?.message || '神经节点网络错误或知识库宕机')
    sending.value = false
    streamingAssistantId.value = null
  }
}

onMounted(loadSessions)
</script>

<style scoped>
.assistant-page {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  height: 100%;
  padding: 24px;
  background: #020b14;
  color: #a3b8cc;
  overflow: hidden;
}

/* Typography & Titles */
.cyber-title {
  margin: 0;
  color: #00ddff;
  font-size: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-shadow: 0 0 10px rgba(0, 221, 255, 0.4);
}

/* Panels */
.session-pane {
  background: rgba(0, 25, 45, 0.5);
  border: 1px solid rgba(0, 221, 255, 0.15);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  box-shadow: inset 0 0 30px rgba(0, 50, 80, 0.3);
  backdrop-filter: blur(10px);
}

.chat-pane {
  background: rgba(0, 15, 25, 0.6);
  border: 1px solid rgba(0, 221, 255, 0.15);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  position: relative;
}

.blur-bg {
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

/* Session List Styles */
.session-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(0, 221, 255, 0.15);
}

.action-btn {
  background: rgba(0, 221, 255, 0.1);
  border-color: rgba(0, 221, 255, 0.3);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.action-btn:hover {
  background: rgba(0, 221, 255, 0.2);
  border-color: #00ddff;
  box-shadow: 0 0 15px rgba(0, 221, 255, 0.4);
}

.session-list {
  padding-right: 8px; /* Room for scrollbar */
  flex: 1;
  min-height: 0;
}

.session-item {
  padding: 16px;
  border-radius: 12px;
  cursor: pointer;
  margin-bottom: 12px;
  background: rgba(0, 20, 40, 0.4);
  border: 1px solid rgba(0, 221, 255, 0.05);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #8c9bb0;
}

.session-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.session-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.session-icon {
  font-size: 20px;
  opacity: 0.6;
  transition: all 0.3s;
}

.session-icon.glow {
  opacity: 1;
  color: #00ddff;
  filter: drop-shadow(0 0 8px #00ddff);
}

.session-title {
  font-size: 14px;
  color: #c0d1e2;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-time {
  font-size: 11px;
  color: #5a748a;
  margin-top: 4px;
}

.session-delete {
  opacity: 0;
  transform: scale(0.8);
  transition: all 0.2s;
  padding: 4px;
}

.session-item:hover {
  background: rgba(0, 221, 255, 0.08);
  border-color: rgba(0, 221, 255, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.session-item:hover .session-delete,
.session-item.active .session-delete {
  opacity: 1;
  transform: scale(1);
}

.session-item.active {
  background: linear-gradient(135deg, rgba(0, 221, 255, 0.15) 0%, rgba(0, 136, 204, 0.05) 100%);
  border-color: rgba(0, 221, 255, 0.4);
  box-shadow: 0 0 20px rgba(0, 221, 255, 0.15);
}

.session-item.active .session-title {
  color: #00ddff;
}

/* List Transitions */
.list-fade-enter-active,
.list-fade-leave-active {
  transition: all 0.4s ease;
}
.list-fade-enter-from,
.list-fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* Chat Header */
.chat-header {
  padding: 18px 28px;
  border-bottom: 1px solid rgba(0, 221, 255, 0.15);
  background: rgba(0, 10, 20, 0.7);
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  background-color: #00ddff;
  border-radius: 50%;
  box-shadow: 0 0 10px #00ddff;
  animation: pulse 2s infinite;
}

.status-text {
  font-size: 12px;
  color: #00ddff;
  opacity: 0.8;
}

/* Messages Area */
.messages {
  flex: 1;
  padding: 0;
  scroll-behavior: smooth;
  min-height: 0;
}

.msg-container {
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 32px;
  min-height: 100%;
}

/* Welcome Area */
.welcome-msg {
  text-align: center;
  margin-top: 8vh;
  padding: 0 20px;
}

.welcome-avatar {
  width: 100px;
  height: 100px;
  margin: 0 auto 24px;
  background: rgba(0, 221, 255, 0.05);
  border: 1px solid rgba(0, 221, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 0 30px rgba(0, 221, 255, 0.1);
}

.welcome-icon {
  font-size: 50px;
  color: #00ddff;
}

.welcome-msg h2 {
  font-size: 24px;
  color: #fff;
  margin-bottom: 12px;
  font-weight: 500;
  letter-spacing: 1px;
}

.welcome-subtitle {
  color: #7a94a9;
  font-size: 15px;
  max-width: 600px;
  margin: 0 auto 40px;
  line-height: 1.6;
}

.suggestions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  max-width: 900px;
  margin: 0 auto;
}

.suggestion-card {
  background: rgba(0, 30, 50, 0.4);
  border: 1px solid rgba(0, 221, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}

.suggestion-card:hover {
  background: rgba(0, 221, 255, 0.08);
  border-color: #00ddff;
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 221, 255, 0.15);
}

.suggestion-icon {
  font-size: 24px;
  color: #00ddff;
  padding: 12px;
  background: rgba(0, 221, 255, 0.1);
  border-radius: 50%;
}

.suggestion-card .text {
  font-size: 14px;
  color: #c0d1e2;
  line-height: 1.5;
}

/* Chat Bubbles */
.msg-wrapper {
  display: flex;
  gap: 20px;
  max-width: 90%;
}

.msg-wrapper.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar .el-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
}

.avatar .el-avatar.user {
  background: linear-gradient(135deg, #1a2a3a 0%, #0d1620 100%);
  border: 1px solid #3a5a7a;
  color: #fff;
}

.avatar .el-avatar.assistant {
  background: linear-gradient(135deg, #004466 0%, #001a22 100%);
  border: 1px solid #00ddff;
  color: #00ddff;
}

.glow-avatar {
  box-shadow: 0 0 15px rgba(0, 221, 255, 0.4) !important;
}

.msg-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: calc(100% - 64px);
}

.msg-wrapper.user .msg-content {
  align-items: flex-end;
}

.role-name {
  font-size: 13px;
  color: #5a748a;
  padding: 0 4px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.bubble {
  padding: 16px 20px;
  border-radius: 16px;
  line-height: 1.6;
  font-size: 15px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.bubble.user {
  background: linear-gradient(135deg, rgba(0, 180, 220, 0.15), rgba(0, 100, 150, 0.2));
  border: 1px solid rgba(0, 221, 255, 0.3);
  color: #fff;
  border-top-right-radius: 4px;
}

.bubble.assistant {
  background: rgba(0, 15, 25, 0.7);
  border: 1px solid rgba(100, 139, 163, 0.2);
  color: #d1e0ec;
  border-top-left-radius: 4px;
}

/* Markdown Rendering Overrides inside bubble */
.md-content :deep(p) {
  margin: 0 0 12px 0;
}
.md-content :deep(p:last-child) {
  margin-bottom: 0;
}
.md-content :deep(pre) {
  background: #010810;
  border: 1px solid rgba(0, 221, 255, 0.1);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}
.md-content :deep(code) {
  font-family: 'Consolas', monospace;
  background: rgba(0, 221, 255, 0.1);
  color: #00ddff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}
.md-content :deep(pre code) {
  background: none;
  padding: 0;
  color: #c0d1e2;
}
.md-content :deep(ul), .md-content :deep(ol) {
  padding-left: 20px;
  margin: 10px 0;
}
.md-content :deep(li) {
  margin-bottom: 6px;
}

/* Citations */
.citations {
  margin-top: 14px;
  background: rgba(0, 20, 35, 0.5);
  border-radius: 12px;
  padding: 14px;
  border-left: 3px solid #00ddff;
  border: 1px solid rgba(0, 221, 255, 0.08);
}

.citation-title {
  font-size: 13px;
  color: #00ddff;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.source-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.source-tag {
  font-size: 12px;
  color: #8c9bb0;
  background: rgba(20, 40, 60, 0.5);
  border: 1px solid rgba(140, 155, 176, 0.2);
  padding: 6px 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: help;
  transition: all 0.2s;
}

.source-tag:hover {
  background: rgba(0, 221, 255, 0.1);
  border-color: rgba(0, 221, 255, 0.3);
  color: #00ddff;
}

.source-name {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Typing Animation */
.typing-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
}

.typing-dot {
  width: 6px;
  height: 6px;
  background-color: #00ddff;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-dot:nth-child(1) { animation-delay: -0.32s; }
.typing-dot:nth-child(2) { animation-delay: -0.16s; }

.typing-text {
  margin-left: 8px;
  color: #7a94a9;
  font-size: 14px;
  letter-spacing: 0.5px;
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* Input Area */
.input-area {
  padding: 24px;
  background: rgba(0, 10, 20, 0.85);
  border-top: 1px solid rgba(0, 221, 255, 0.15);
  position: relative;
  z-index: 10;
}

.input-panel {
  max-width: 1000px;
  margin: 0 auto;
  position: relative;
}

.assistant-input :deep(.el-textarea__inner) {
  background: rgba(255, 255, 255, 0.95); /* Bright input background */
  border: 1px solid rgba(0, 221, 255, 0.4); /* Stronger neon border */
  color: #000000; /* Black text color */
  border-radius: 16px;
  line-height: 1.6;
  padding: 16px 20px 48px;
  box-shadow: inset 0 2px 10px rgba(0,0,0,0.05);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  font-size: 15px;
  letter-spacing: 0.5px;
}

.assistant-input :deep(.el-textarea__inner)::placeholder {
  color: #99aab5; /* Softer placeholder color for white background */
  opacity: 0.8;
}

.assistant-input :deep(.el-textarea__inner:focus) {
  border-color: #00ddff;
  box-shadow: 0 0 12px rgba(0, 221, 255, 0.4), inset 0 2px 10px rgba(0,0,0,0.1);
  background: #ffffff;
}

.assistant-input :deep(.el-input__count) {
  background: transparent;
  bottom: 24px;
  right: 70px;
  color: #5a748a;
}

.input-actions {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  pointer-events: none; /* Let clicks pass to textarea where empty */
}

.icon-btn, .action-right {
  pointer-events: auto; /* Re-enable clicks for buttons */
}

.action-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-btn.is-disabled {
  background: transparent;
}

.input-hint {
  font-size: 12px;
  color: #4a647a;
}

.send-btn {
  width: 44px;
  height: 44px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, #00ddff, #0088cc);
  border: none;
  box-shadow: 0 4px 15px rgba(0, 221, 255, 0.2);
  transition: all 0.3s;
}

.send-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #00eeff, #0099dd);
  box-shadow: 0 6px 20px rgba(0, 221, 255, 0.4);
  transform: translateY(-2px);
}

.send-btn:disabled {
  background: rgba(0, 100, 150, 0.3);
  color: #5a748a;
  box-shadow: none;
}

/* Utility Animations */
.pop-in {
  animation: popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
  opacity: 0;
  transform: scale(0.95);
}

@keyframes popIn {
  from { opacity: 0; transform: scale(0.95) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.slide-up {
  animation: slideUp 0.6s ease-out forwards;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.pulse-glow {
  animation: pulseGlow 3s infinite;
}

@keyframes pulseGlow {
  0% { filter: drop-shadow(0 0 5px rgba(0,221,255,0.4)); }
  50% { filter: drop-shadow(0 0 20px rgba(0,221,255,0.8)); }
  100% { filter: drop-shadow(0 0 5px rgba(0,221,255,0.4)); }
}

/* Responsive */
@media (max-width: 1024px) {
  .assistant-page {
    grid-template-columns: 280px 1fr;
    padding: 16px;
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .assistant-page {
    grid-template-columns: 1fr;
    padding: 12px;
    overflow: auto;
  }

  .session-pane {
    max-height: 30vh;
  }

  .input-panel {
    max-width: 100%;
  }

  .assistant-input :deep(.el-input__count) {
    display: none;
  }

  .input-hint {
    display: none;
  }

  .msg-wrapper {
    max-width: 100%;
  }

  .avatar .el-avatar {
    width: 36px;
    height: 36px;
  }
}
</style>