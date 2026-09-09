<template>
  <div class="page-wrap admin-page glass-card">
    <div class="toolbar">
      <el-space wrap>
        <el-button @click="openCreate">新增用户</el-button>
        <el-button type="primary" @click="loadUsers">刷新</el-button>
      </el-space>
    </div>

    <el-table :data="users" border height="560">
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="username" label="用户名" width="150" />
      <el-table-column prop="display_name" label="显示名称" width="160" />
      <el-table-column label="角色" width="120">
        <template #default="scope">{{ scope.row.role === 'admin' ? '管理员' : '普通用户' }}</template>
      </el-table-column>
      <el-table-column label="启用" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="robot_count" label="绑定机器人" width="120" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="openEdit(scope.row)">编辑</el-button>
          <el-button link type="danger" @click="remove(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增用户' : '编辑用户'" width="520px">
      <el-form :model="dialog.form" label-width="120px">
        <el-form-item label="用户名"><el-input v-model="dialog.form.username" :disabled="dialog.mode === 'edit'" /></el-form-item>
        <el-form-item label="显示名称"><el-input v-model="dialog.form.display_name" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="dialog.form.role" style="width: 100%">
            <el-option value="user" label="普通用户" />
            <el-option value="admin" label="管理员" />
          </el-select>
        </el-form-item>
        <el-form-item label="密码"><el-input v-model="dialog.form.password" placeholder="编辑时可留空不修改" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="dialog.form.is_active" /></el-form-item>
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

const users = ref<any[]>([])

const dialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  userId: 0,
  form: {
    username: '',
    display_name: '',
    role: 'user',
    password: '',
    is_active: true
  }
})

const loadUsers = async () => {
  const { data } = await api.get('/users')
  users.value = data.data.items || []
}

const openCreate = () => {
  dialog.mode = 'create'
  dialog.userId = 0
  dialog.form.username = ''
  dialog.form.display_name = ''
  dialog.form.role = 'user'
  dialog.form.password = ''
  dialog.form.is_active = true
  dialog.visible = true
}

const openEdit = (row: any) => {
  dialog.mode = 'edit'
  dialog.userId = row.id
  dialog.form.username = row.username
  dialog.form.display_name = row.display_name
  dialog.form.role = row.role
  dialog.form.password = ''
  dialog.form.is_active = Boolean(row.is_active)
  dialog.visible = true
}

const submitDialog = async () => {
  const payload = {
    username: dialog.form.username,
    display_name: dialog.form.display_name,
    role: dialog.form.role,
    password: dialog.form.password,
    is_active: dialog.form.is_active
  }

  if (dialog.mode === 'create') {
    await api.post('/users', payload)
    ElMessage.success('用户已创建')
  } else {
    await api.put(`/users/${dialog.userId}`, payload)
    ElMessage.success('用户已更新')
  }
  dialog.visible = false
  await loadUsers()
}

const remove = async (id: number) => {
  await ElMessageBox.confirm('确定删除该用户吗？', '提示', { type: 'warning' })
  await api.delete(`/users/${id}`)
  ElMessage.success('删除成功')
  await loadUsers()
}

onMounted(loadUsers)
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
