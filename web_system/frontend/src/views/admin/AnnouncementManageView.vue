<template>
  <div class="page-wrap admin-page glass-card">
    <div class="toolbar">
      <el-space wrap>
        <el-button @click="openCreate">新增公告</el-button>
        <el-button type="primary" @click="loadAnnouncements">刷新</el-button>
      </el-space>
    </div>

    <el-table :data="rows" border height="560">
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="title" label="标题" width="220" />
      <el-table-column prop="content" label="内容" min-width="300" />
      <el-table-column label="置顶" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.pinned ? 'warning' : 'info'">{{ scope.row.pinned ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="openEdit(scope.row)">编辑</el-button>
          <el-button link type="danger" @click="remove(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增公告' : '编辑公告'" width="640px">
      <el-form :model="dialog.form" label-width="110px">
        <el-form-item label="标题"><el-input v-model="dialog.form.title" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="dialog.form.content" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="置顶"><el-switch v-model="dialog.form.pinned" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitDialog">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { api } from '../../services/api'

const rows = ref<any[]>([])

const dialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  id: 0,
  form: {
    title: '',
    content: '',
    pinned: false
  }
})

const loadAnnouncements = async () => {
  const { data } = await api.get('/announcements')
  rows.value = data.data || []
}

const openCreate = () => {
  dialog.mode = 'create'
  dialog.id = 0
  dialog.form.title = ''
  dialog.form.content = ''
  dialog.form.pinned = false
  dialog.visible = true
}

const openEdit = (row: any) => {
  dialog.mode = 'edit'
  dialog.id = row.id
  dialog.form.title = row.title
  dialog.form.content = row.content
  dialog.form.pinned = Boolean(row.pinned)
  dialog.visible = true
}

const submitDialog = async () => {
  const payload = {
    title: dialog.form.title,
    content: dialog.form.content,
    pinned: dialog.form.pinned
  }
  if (dialog.mode === 'create') {
    await api.post('/announcements', payload)
    ElMessage.success('公告已创建')
  } else {
    await api.put(`/announcements/${dialog.id}`, payload)
    ElMessage.success('公告已更新')
  }
  dialog.visible = false
  await loadAnnouncements()
}

const remove = async (id: number) => {
  await ElMessageBox.confirm('确定删除该公告吗？', '提示', { type: 'warning' })
  await api.delete(`/announcements/${id}`)
  ElMessage.success('删除成功')
  await loadAnnouncements()
}

onMounted(loadAnnouncements)
</script>

<style scoped>
.admin-page {
  padding: 14px;
}

.toolbar {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: linear-gradient(145deg, #ffffff, #f4f9ff);
}

:deep(.el-dialog__body) {
  background: #fafdff;
}
</style>
