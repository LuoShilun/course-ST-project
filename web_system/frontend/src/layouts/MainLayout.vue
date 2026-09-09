<template>
  <el-container class="layout-root">
    <el-aside width="258px" class="aside glass-card">
      <div class="brand-block">
        <div class="brand-title">海巡智检</div>
        <div class="brand-sub">水下智能作业平台</div>
      </div>

      <div class="status-card">
        <div class="status-label">当前身份</div>
        <div class="status-value"><el-icon><User /></el-icon> {{ roleText }}</div>
      </div>

      <el-menu :default-active="activePath" router class="menu">
        <el-menu-item index="/home">
          <el-icon><House /></el-icon>
          <span>首页总览</span>
        </el-menu-item>
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>数据研判大屏</span>
        </el-menu-item>
        <el-menu-item index="/map">
          <el-icon><MapLocation /></el-icon>
          <span>智检机器地图</span>
        </el-menu-item>
        <el-menu-item index="/records">
          <el-icon><Document /></el-icon>
          <span>智检记录</span>
        </el-menu-item>
        <el-menu-item index="/detect">
          <el-icon><VideoCamera /></el-icon>
          <span>实时推理工作台</span>
        </el-menu-item>
        <el-menu-item index="/assistant">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 助手</span>
        </el-menu-item>
      </el-menu>

      <div class="aside-actions">
        <el-button type="primary" @click="goAdmin" v-if="auth.isAdmin">
          <el-icon class="el-icon--left"><Setting /></el-icon>进入管理平台
        </el-button>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header glass-card">
        <div class="header-title">
          <h3 class="page-title">
            <el-icon class="icon"><Monitor /></el-icon>
            水下作业调度与态势中心
          </h3>
          <div class="user-meta">{{ auth.user?.display_name }} ({{ roleText }})</div>
        </div>

        <el-space class="header-actions">
          <el-button @click="refreshMe" plain><el-icon class="el-icon--left"><Refresh /></el-icon>状态同步</el-button>
          <el-button type="danger" plain @click="logout"><el-icon class="el-icon--left"><SwitchButton /></el-icon>安全登出</el-button>
        </el-space>
      </el-header>

      <el-main class="main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  House, DataBoard, MapLocation, Document, VideoCamera,
  ChatDotRound, Setting, User, SwitchButton, Refresh, Monitor
} from '@element-plus/icons-vue'

import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activePath = computed(() => route.path)
const roleText = computed(() => (auth.user?.role === 'admin' ? '管理员' : '普通用户'))

const refreshMe = async () => {
  try {
    await auth.fetchMe()
    ElMessage.success('个人信息已刷新')
  } catch {
    ElMessage.error('刷新失败')
  }
}

const logout = () => {
  auth.clearAuth()
  router.replace('/login')
}

const goAdmin = () => {
  router.push('/admin/robots')
}
</script>

<style scoped>
.layout-root {
  height: 100%;
  padding: 14px;
  gap: 14px;
}

.aside {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.brand-block {
  padding: 6px 4px;
}

.brand-title {
  font-weight: 700;
  font-size: 20px;
  letter-spacing: 0.4px;
  color: var(--primary);
  text-shadow: 0 0 10px rgba(15, 142, 199, 0.2);
}

.brand-sub {
  margin-top: 6px;
  color: var(--text-sub);
  font-size: 12px;
}

.status-card {
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  background: var(--bg-elevated);
}

.status-label {
  font-size: 12px;
  color: var(--text-sub);
}

.status-value {
  margin-top: 4px;
  font-weight: 700;
  color: #0e7e58;
}

.menu {
  border: none;
  background: transparent;
  flex: 1;
}

.aside-actions {
  display: grid;
  gap: 8px;
}

.header {
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-base);
  font-weight: 600;
  letter-spacing: 0.5px;
}

.page-title .icon {
  font-size: 24px;
  color: var(--primary);
}

.header-title {
  min-width: 0;
}

.user-meta {
  color: var(--text-sub);
  font-size: 13px;
  margin-top: 4px;
}

.main {
  padding: 0;
}

@media (max-width: 980px) {
  .layout-root {
    padding: 8px;
    gap: 8px;
  }

  .aside {
    width: 210px;
    padding: 10px;
  }

  .page-title {
    font-size: 17px;
  }

  .header {
    padding: 10px 12px;
  }
}
</style>
