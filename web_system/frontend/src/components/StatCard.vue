<template>
  <div class="stat-card glass-card">
    <div class="header">
      <span class="title">{{ title }}</span>
      <el-tag size="small" effect="dark" type="info">{{ badge }}</el-tag>
    </div>
    <div class="value mono">{{ value }}</div>
    <div class="extra">{{ extra }}</div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'StatCard',
  props: {
    title: {
      type: String,
      required: true
    },
    value: {
      type: [String, Number],
      required: true
    },
    extra: {
      type: String,
      default: ''
    },
    badge: {
      type: String,
      default: ''
    }
  }
})
</script>

<style scoped>
.stat-card {
  padding: 14px;
  min-height: 116px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
}

.stat-card::after {
  content: '';
  position: absolute;
  right: -24px;
  top: -24px;
  width: 110px;
  height: 110px;
  background: radial-gradient(circle, rgba(15, 142, 199, 0.2) 0%, rgba(15, 142, 199, 0) 70%);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.title {
  font-size: 13px;
  color: var(--text-sub);
}

.value {
  font-size: 28px;
  font-weight: 700;
  color: #1f577f;
  text-shadow: 0 0 8px rgba(15, 142, 199, 0.12);
}

.extra {
  font-size: 12px;
  color: var(--text-sub);
}
</style>
