<template>
  <el-container class="layout-root">
    <el-aside width="258px" class="aside glass-card">
      <div class="brand-block">
        <div class="brand-title">海巡智检 Admin</div>
        <div class="brand-sub">平台配置与运维管理</div>
      </div>

      <el-menu :default-active="activePath" router class="menu">
        <el-menu-item index="/admin/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>数据研判大屏</span>
        </el-menu-item>
        <el-menu-item index="/admin/map">
          <el-icon><MapLocation /></el-icon>
          <span>智检机器地图</span>
        </el-menu-item>
        <el-menu-item index="/admin/robots">
          <el-icon><Cpu /></el-icon>
          <span>机器终端与孪生</span>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <span>账号与RBAC权限</span>
        </el-menu-item>
        <el-menu-item index="/admin/models">
          <el-icon><Setting /></el-icon>
          <span>检测模型配置</span>
        </el-menu-item>
        <el-menu-item index="/admin/rag-config">
          <el-icon><Cpu /></el-icon>
          <span>RAG大模型语料调度</span>
        </el-menu-item>
        <el-menu-item index="/admin/announcements">
          <el-icon><Microphone /></el-icon>
          <span>系统运营公告</span>
        </el-menu-item>
      </el-menu>

      <div class="aside-actions">
        <el-button @click="goUser" plain>返回用户端</el-button>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header glass-card">
        <div>
          <h3 class="page-title">海巡智检 (OceanGuard) 管理中心</h3>
          <div class="page-subtitle">构建水下智能装备全生命周期治理体系</div>
        </div>
        <el-space>
          <span class="admin-name">{{ auth.user?.display_name }}</span>
          <el-button type="danger" plain @click="logout">退出登录</el-button>
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
import { useAuthStore } from '../stores/auth'
import { Cpu, User, Setting, Microphone, DataBoard, MapLocation } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activePath = computed(() => route.path)

const goUser = () => {
  router.push('/home')
}

const logout = () => {
  auth.clearAuth()
  router.replace('/login')
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

.brand-title {
  font-weight: 700;
  font-size: 20px;
  letter-spacing: 0.4px;
  color: #0f8ec7;
}

.brand-sub {
  margin-top: 6px;
  color: var(--text-sub);
  font-size: 12px;
}

.menu {
  border: none;
  background: transparent;
  flex: 1;
}

.aside-actions {
  display: grid;
}

.header {
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
}

.page-title {
  margin: 0;
  font-size: 20px;
}

.page-subtitle {
  margin-top: 4px;
  color: var(--text-sub);
  font-size: 13px;
}

.admin-name {
  color: #2b5f8b;
  font-weight: 600;
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

  .header {
    padding: 10px 12px;
  }

  .page-title {
    font-size: 17px;
  }
}
</style>
