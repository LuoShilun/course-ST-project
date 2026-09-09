<template>
  <div class="page-wrap records-page glass-card">
    <div class="toolbar">
      <el-space wrap>
        <el-select v-model="filters.source_type" placeholder="来源类型" clearable style="width: 150px">
          <el-option value="image" label="图片" />
          <el-option value="video" label="视频" />
        </el-select>
        <el-select v-model="filters.is_trash" placeholder="垃圾标记" clearable style="width: 150px">
          <el-option value="1" label="垃圾" />
          <el-option value="0" label="非垃圾" />
        </el-select>
        <el-button type="primary" @click="loadRecords">查询</el-button>
        <el-button @click="openCreate">新增记录</el-button>
      </el-space>
    </div>

    <el-table :data="records" border height="520" :row-class-name="rowClassName">
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="detected_type" label="识别类型" width="130" />
      <el-table-column prop="robot_code" label="机器人编号" width="130" />
      <el-table-column label="来源" width="110">
        <template #default="scope">
          {{ scope.row.source_type === 'image' ? '图片' : scope.row.source_type === 'video' ? '视频' : scope.row.source_type }}
        </template>
      </el-table-column>
      <el-table-column prop="confidence" label="置信度" width="120" />
      <el-table-column prop="detected_at" label="识别时间" min-width="180" />
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="openEdit(scope.row)">编辑</el-button>
          <el-button link type="danger" @click="remove(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        :current-page="pagination.page"
        :page-size="pagination.page_size"
        :total="pagination.total"
        layout="total, prev, pager, next, sizes"
        @update:current-page="onCurrentPageChange"
        @update:page-size="onPageSizeChange"
      />
    </div>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增记录' : '编辑记录'" width="520px">
      <el-form :model="dialog.form" label-width="120px">
        <el-form-item label="识别类型"><el-input v-model="dialog.form.detected_type" /></el-form-item>
        <el-form-item label="来源类型">
          <el-select v-model="dialog.form.source_type" style="width: 100%">
            <el-option value="image" label="图片" />
            <el-option value="video" label="视频" />
          </el-select>
        </el-form-item>
        <el-form-item label="置信度"><el-input-number v-model="dialog.form.confidence" :min="0" :max="1" :step="0.01" /></el-form-item>
        <el-form-item label="是否垃圾"><el-switch v-model="dialog.form.is_trash" /></el-form-item>
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

const records = ref<any[]>([])

const filters = reactive({
  source_type: '',
  is_trash: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const dialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  recordId: 0,
  form: {
    detected_type: '',
    source_type: 'image',
    confidence: 0.8,
    is_trash: true
  }
})

const loadRecords = async () => {
  const { data } = await api.get('/records', {
    params: {
      page: pagination.page,
      page_size: pagination.page_size,
      source_type: filters.source_type || undefined,
      is_trash: filters.is_trash || undefined
    }
  })
  records.value = data.data.items || []
  pagination.total = data.data.total || 0
}

const onCurrentPageChange = (page: number) => {
  pagination.page = page
  loadRecords()
}

const onPageSizeChange = (size: number) => {
  pagination.page_size = size
  pagination.page = 1
  loadRecords()
}

const rowClassName = ({ row }: any) => (row.is_trash ? 'trash-row' : '')

const openCreate = () => {
  dialog.mode = 'create'
  dialog.recordId = 0
  dialog.form.detected_type = ''
  dialog.form.source_type = 'image'
  dialog.form.confidence = 0.8
  dialog.form.is_trash = true
  dialog.visible = true
}

const openEdit = (row: any) => {
  dialog.mode = 'edit'
  dialog.recordId = row.id
  dialog.form.detected_type = row.detected_type
  dialog.form.source_type = row.source_type
  dialog.form.confidence = Number(row.confidence || 0)
  dialog.form.is_trash = Boolean(row.is_trash)
  dialog.visible = true
}

const submitDialog = async () => {
  const payload = {
    detected_type: dialog.form.detected_type,
    source_type: dialog.form.source_type,
    confidence: dialog.form.confidence,
    is_trash: dialog.form.is_trash
  }

  if (dialog.mode === 'create') {
    await api.post('/records', payload)
    ElMessage.success('记录已创建')
  } else {
    await api.put(`/records/${dialog.recordId}`, payload)
    ElMessage.success('记录已更新')
  }

  dialog.visible = false
  await loadRecords()
}

const remove = async (id: number) => {
  await ElMessageBox.confirm('确定删除这条记录吗？', '提示', { type: 'warning' })
  await api.delete(`/records/${id}`)
  ElMessage.success('删除成功')
  await loadRecords()
}

onMounted(loadRecords)
</script>

<style scoped>
.records-page {
  padding: 14px;
}

.toolbar {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: linear-gradient(145deg, #ffffff, #f4f9ff);
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>

<style>
.el-table .trash-row {
  --el-table-tr-bg-color: #fff6ef;
}
</style>
