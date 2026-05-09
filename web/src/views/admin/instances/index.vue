<template>
  <div class="admin-instances">
    <div class="page-header">
      <h2>实例管理</h2>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索实例名 / 容器名"
        clearable
        style="width: 220px"
        @clear="loadData"
        @keyup.enter="loadData"
      />
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px" @change="loadData">
        <el-option value="running" label="运行中" />
        <el-option value="stopped" label="已停止" />
        <el-option value="error" label="异常" />
      </el-select>
      <el-button type="primary" @click="loadData">查询</el-button>
    </div>

    <!-- Table -->
    <el-table :data="instances" v-loading="loading" border stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="实例名称" min-width="120" />
      <el-table-column prop="owner_username" label="所属用户" width="100" />
      <el-table-column prop="container_name" label="容器名" min-width="160" />
      <el-table-column prop="port" label="端口" width="70" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="资源" width="130">
        <template #default="{ row }">
          {{ row.cpu_limit }}C / {{ row.memory_limit_mb }}MB
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="140">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'stopped' || row.status === 'error'"
            type="success" size="small" text
            @click="handleStart(row)"
          >启动</el-button>
          <el-button
            v-if="row.status === 'running'"
            type="warning" size="small" text
            @click="handleStop(row)"
          >停止</el-button>
          <el-button
            v-if="row.status === 'running'"
            size="small" text
            @click="handleRestart(row)"
          >重启</el-button>
          <el-button size="small" text @click="viewLogs(row)">日志</el-button>
          <el-button type="danger" size="small" text @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </div>

    <!-- Logs Dialog -->
    <el-dialog v-model="showLogs" :title="`日志 - ${logsTitle}`" width="700px" destroy-on-close>
      <pre class="logs-content" v-loading="logsLoading">{{ logsContent || '暂无日志' }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminInstanceApi } from '@/api/adminInstance'

interface AdminInstance {
  id: number
  name: string
  owner_username: string
  owner_user_id: number
  container_name: string
  port: number
  status: string
  health_status: string
  cpu_limit: number
  memory_limit_mb: number
  created_at: string
}

const loading = ref(false)
const instances = ref<AdminInstance[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const keyword = ref('')
const statusFilter = ref('')

// Logs
const showLogs = ref(false)
const logsTitle = ref('')
const logsContent = ref('')
const logsLoading = ref(false)

function statusTagType(status: string) {
  const map: Record<string, string> = { running: 'success', stopped: 'info', error: 'danger', creating: 'warning' }
  return map[status] || 'info'
}

function statusLabel(status: string) {
  const map: Record<string, string> = { running: '运行中', stopped: '已停止', error: '异常', creating: '创建中' }
  return map[status] || status
}

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 16)
}

async function loadData() {
  loading.value = true
  try {
    const res = await adminInstanceApi.list({
      keyword: keyword.value || undefined,
      status: statusFilter.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    instances.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function handleStart(row: AdminInstance) {
  await adminInstanceApi.start(row.id)
  ElMessage.success('启动指令已发送')
  loadData()
}

async function handleStop(row: AdminInstance) {
  await adminInstanceApi.stop(row.id)
  ElMessage.success('停止指令已发送')
  loadData()
}

async function handleRestart(row: AdminInstance) {
  await adminInstanceApi.restart(row.id)
  ElMessage.success('重启指令已发送')
  loadData()
}

async function handleDelete(row: AdminInstance) {
  await ElMessageBox.confirm(
    `确认强制删除实例 "${row.name}" (用户: ${row.owner_username})？此操作不可恢复。`,
    '管理员删除确认',
    { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
  )
  await adminInstanceApi.delete(row.id)
  ElMessage.success('删除成功')
  loadData()
}

async function viewLogs(row: AdminInstance) {
  logsTitle.value = row.name
  logsContent.value = ''
  showLogs.value = true
  logsLoading.value = true
  try {
    const res = await adminInstanceApi.logs(row.id)
    logsContent.value = Array.isArray(res.data.logs) ? res.data.logs.join('\n') : res.data.logs
  } catch {
    logsContent.value = '获取日志失败'
  } finally {
    logsLoading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.admin-instances {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.logs-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: var(--radius);
  font-size: 12px;
  line-height: 1.6;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

@media (max-width: 768px) {
  .filter-bar {
    flex-direction: column;
  }

  :deep(.el-table) {
    font-size: 12px;
  }
}
</style>
