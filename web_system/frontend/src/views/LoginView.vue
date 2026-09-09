<template>
  <div class="login-page">
    <div class="bg-grid"></div>
    <div class="bg-orb orb-a"></div>
    <div class="bg-orb orb-b"></div>
    <div class="bg-orb orb-c"></div>

    <section class="login-shell">
      <div class="brand-panel glass-card">
        <div class="panel-badge">OceanGuard AI Edition</div>
        <h1>海巡智检<br/>水下智能作业平台</h1>
        <p class="panel-desc">致力于提供面向水下环境的智能化监测、垃圾异常检测以及水下作业全方位辅助的系统平台。</p>

        <div class="feature-list">
          <div class="feature-item"><el-icon><Monitor /></el-icon> 实时视频流智能推理</div>
          <div class="feature-item"><el-icon><DataBoard /></el-icon> 数字孪生三维资产管控</div>
          <div class="feature-item"><el-icon><Setting /></el-icon> RBAC企业级角色权限系统</div>
        </div>
      </div>

      <el-card class="login-card glass-card">
        <h2>登录系统</h2>
        <p class="login-subtitle">为保障数据安全，请使用企业域账号或管理账号登录</p>

        <el-form :model="form" label-position="top" @submit.prevent class="login-form">
          <el-form-item label="用户名">
            <el-input v-model="form.username" size="large" placeholder="请输入用户名" :prefix-icon="User" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" size="large" show-password placeholder="请输入密码" :prefix-icon="Lock" @keyup.enter="submit" />
          </el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="submit" class="login-btn">
            安全登录
          </el-button>
        </el-form>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Monitor, DataBoard, Setting } from '@element-plus/icons-vue'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const submit = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const user = await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    if (user.role === 'admin') {
      router.replace('/admin/robots')
    } else {
      router.replace('/home')
    }
  } catch (error: any) {
    const msg = error?.response?.data?.message || '登录失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow: hidden;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(123, 168, 210, 0.18) 1px, transparent 1px),
    linear-gradient(90deg, rgba(123, 168, 210, 0.18) 1px, transparent 1px);
  background-size: 28px 28px;
  opacity: 0.6;
}

.login-shell {
  position: relative;
  z-index: 2;
  width: min(1040px, 100%);
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 14px;
}

.brand-panel {
  padding: 28px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 440px;
}

.panel-badge {
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.16);
  color: #0f6f50;
  font-size: 12px;
  font-weight: 600;
}

h1 {
  margin: 14px 0 10px;
  font-size: 34px;
  line-height: 1.2;
  letter-spacing: 0.4px;
}

.panel-desc {
  margin: 0;
  color: var(--text-sub);
  line-height: 1.8;
}

.feature-list {
  margin-top: 36px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feature-item {
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(4px);
  font-size: 14px;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateX(4px);
  border-color: var(--primary);
}

.login-card {
  width: 100%;
  z-index: 2;
  border-radius: 20px;
  padding: 16px;
  align-self: center;
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.04);
}

h2 {
  margin: 0;
  font-size: 26px;
  color: var(--primary);
  letter-spacing: 0.5px;
}

.login-subtitle {
  margin: 8px 0 24px;
  color: var(--text-sub);
  font-size: 13px;
}

.login-form .el-form-item {
  margin-bottom: 22px;
}

.login-btn {
  width: 100%;
  margin-top: 12px;
  font-size: 16px;
  height: 48px;
  border-radius: 8px;
  font-weight: 500;
  letter-spacing: 1px;
}

.bg-orb {
  position: absolute;
  width: 340px;
  height: 340px;
  border-radius: 50%;
  filter: blur(30px);
  opacity: 0.28;
  animation: float 7s ease-in-out infinite;
}

.orb-a {
  background: linear-gradient(120deg, #63c2ff, #7ce8c7);
  left: -80px;
  top: -90px;
}

.orb-b {
  background: linear-gradient(120deg, #78d8ff, #b1c5ff);
  right: -100px;
  bottom: -120px;
  animation-delay: 1.2s;
}

.orb-c {
  background: linear-gradient(120deg, #7cb4ff, #74d5a8);
  left: 30%;
  bottom: -170px;
  animation-delay: 2.1s;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-14px);
  }
}

@media (max-width: 980px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .brand-panel {
    min-height: 0;
    padding: 18px;
  }

  h1 {
    font-size: 26px;
  }
}
</style>
