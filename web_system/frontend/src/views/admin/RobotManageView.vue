<template>
  <div class="page-wrap admin-page glass-card">
    <div class="toolbar">
      <el-space wrap>
        <el-input v-model="keyword" placeholder="搜索机器人" clearable style="width: 260px" />
        <el-button type="primary" @click="loadRobots">搜索</el-button>
        <el-button @click="openCreate">新增机器人</el-button>
      </el-space>
    </div>

    <el-table :data="robots" border height="560">
      <el-table-column prop="robot_code" label="机器人编号" width="130" />
      <el-table-column prop="name" label="机器人名称" width="160" />
      <el-table-column label="绑定用户" width="180">
        <template #default="scope">
          <span v-if="scope.row.bound_user_id">{{ scope.row.bound_user_display_name }} ({{ scope.row.bound_username }})</span>
          <el-tag v-else type="info">未绑定</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="容量使用" width="180">
        <template #default="scope">{{ scope.row.capacity_used }} / {{ scope.row.capacity_total }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="scope">{{ statusText(scope.row.status) }}</template>
      </el-table-column>
      <el-table-column label="在线" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.is_online ? 'success' : 'info'">{{ scope.row.is_online ? '在线' : '离线' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="latitude" label="纬度" width="120" />
      <el-table-column prop="longitude" label="经度" width="120" />
      <el-table-column prop="rtsp_url" label="RTSP地址" min-width="260" show-overflow-tooltip />
      <el-table-column label="操作" width="320">
        <template #default="scope">
          <el-button link type="warning" @click="openBind(scope.row)">绑定用户</el-button>
          <el-button link type="info" :disabled="!scope.row.bound_user_id" @click="unbind(scope.row)">解绑</el-button>
          <el-button link type="primary" @click="openEdit(scope.row)">编辑</el-button>
          <el-button link type="danger" @click="remove(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增机器人' : '编辑机器人'" width="560px">
      <el-form :model="dialog.form" label-width="130px">
        <el-form-item label="机器人编号"><el-input v-model="dialog.form.robot_code" :disabled="dialog.mode === 'edit'" /></el-form-item>
        <el-form-item label="机器人名称"><el-input v-model="dialog.form.name" /></el-form-item>
        <el-form-item label="总容量"><el-input-number v-model="dialog.form.capacity_total" :min="1" /></el-form-item>
        <el-form-item label="已用容量"><el-input-number v-model="dialog.form.capacity_used" :min="0" /></el-form-item>
        <el-form-item label="状态"><el-input v-model="dialog.form.status" /></el-form-item>
        <el-form-item label="RTSP地址"><el-input v-model="dialog.form.rtsp_url" placeholder="rtsp://localhost:8554/live/cam01" /></el-form-item>
        <el-form-item label="纬度"><el-input-number v-model="dialog.form.latitude" :precision="6" :step="0.0001" /></el-form-item>
        <el-form-item label="经度"><el-input-number v-model="dialog.form.longitude" :precision="6" :step="0.0001" /></el-form-item>
        <el-form-item label="在线"><el-switch v-model="dialog.form.is_online" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitDialog">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="bindDialog.visible" title="绑定用户" width="460px">
      <el-form label-width="110px">
        <el-form-item label="机器人">
          <el-input :value="bindDialog.robotName" disabled />
        </el-form-item>
        <el-form-item label="用户">
          <el-select v-model="bindDialog.userId" style="width: 100%" filterable placeholder="请选择用户">
            <el-option
              v-for="u in bindableUsers"
              :key="u.id"
              :value="u.id"
              :label="`${u.display_name} (${u.username})`"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitBind">确定绑定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { api } from '../../services/api'

const robots = ref<any[]>([])
const users = ref<any[]>([])
const keyword = ref('')

const dialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  robotId: 0,
  form: {
    robot_code: '',
    name: '',
    capacity_total: 100,
    capacity_used: 0,
    status: 'available',
    rtsp_url: '',
    latitude: 22.547,
    longitude: 114.085,
    is_online: true
  }
})

const bindDialog = reactive({
  visible: false,
  robotId: 0,
  robotName: '',
  userId: undefined as number | undefined,
  currentUserId: 0
})

const loadRobots = async () => {
  const { data } = await api.get('/robots', { params: { keyword: keyword.value || undefined } })
  robots.value = data.data || []
}

const loadUsers = async () => {
  const { data } = await api.get('/users', { params: { page: 1, page_size: 200 } })
  users.value = (data.data.items || []).filter((u: any) => u.role === 'user')
}

const bindableUsers = computed(() => {
  return users.value.filter((u: any) => u.robot_count === 0 || u.id === bindDialog.currentUserId)
})

const statusText = (status: string) => {
  if (status === 'available') return '可用'
  if (status === 'unavailable') return '不可用'
  return status || '-'
}

const openCreate = () => {
  dialog.mode = 'create'
  dialog.robotId = 0
  dialog.form.robot_code = ''
  dialog.form.name = ''
  dialog.form.capacity_total = 100
  dialog.form.capacity_used = 0
  dialog.form.status = 'available'
  dialog.form.rtsp_url = ''
  dialog.form.latitude = 22.547
  dialog.form.longitude = 114.085
  dialog.form.is_online = true
  dialog.visible = true
}

const openEdit = (row: any) => {
  dialog.mode = 'edit'
  dialog.robotId = row.id
  dialog.form.robot_code = row.robot_code
  dialog.form.name = row.name
  dialog.form.capacity_total = Number(row.capacity_total || 100)
  dialog.form.capacity_used = Number(row.capacity_used || 0)
  dialog.form.status = row.status || 'available'
  dialog.form.rtsp_url = row.rtsp_url || ''
  dialog.form.latitude = Number(row.latitude || 0)
  dialog.form.longitude = Number(row.longitude || 0)
  dialog.form.is_online = Boolean(row.is_online)
  dialog.visible = true
}

const submitDialog = async () => {
  const payload = {
    robot_code: dialog.form.robot_code,
    name: dialog.form.name,
    capacity_total: dialog.form.capacity_total,
    capacity_used: dialog.form.capacity_used,
    status: dialog.form.status,
    rtsp_url: dialog.form.rtsp_url,
    latitude: dialog.form.latitude,
    longitude: dialog.form.longitude,
    is_online: dialog.form.is_online
  }

  if (dialog.mode === 'create') {
    await api.post('/robots', payload)
    ElMessage.success('机器人已创建')
  } else {
    await api.put(`/robots/${dialog.robotId}`, payload)
    ElMessage.success('机器人已更新')
  }

  dialog.visible = false
  await loadRobots()
}

const openBind = (row: any) => {
  bindDialog.visible = true
  bindDialog.robotId = row.id
  bindDialog.robotName = `${row.robot_code} / ${row.name}`
  bindDialog.currentUserId = Number(row.bound_user_id || 0)
  bindDialog.userId = row.bound_user_id ? Number(row.bound_user_id) : undefined
}

const submitBind = async () => {
  if (!bindDialog.userId) {
    ElMessage.warning('请选择要绑定的用户')
    return
  }
  await api.post(`/robots/${bindDialog.robotId}/bind`, { user_id: bindDialog.userId })
  ElMessage.success('绑定成功')
  bindDialog.visible = false
  await loadUsers()
  await loadRobots()
}

const unbind = async (row: any) => {
  if (!row.bound_user_id) return
  await ElMessageBox.confirm('确定解绑该机器人与当前用户吗？', '提示', { type: 'warning' })
  await api.delete(`/robots/${row.id}/bind/${row.bound_user_id}`)
  ElMessage.success('解绑成功')
  await loadUsers()
  await loadRobots()
}

const remove = async (id: number) => {
  await ElMessageBox.confirm('确定删除该机器人吗？', '提示', { type: 'warning' })
  await api.delete(`/robots/${id}`)
  ElMessage.success('删除成功')
  await loadRobots()
}

onMounted(async () => {
  await loadUsers()
  await loadRobots()
})
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
