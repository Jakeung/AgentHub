<template>
  <div class="audit-page">
    <div class="page-header">
      <h2>审计日志</h2>
      <div class="filters">
        <el-select v-model="filterAction" placeholder="操作类型" clearable style="width: 160px" @change="loadData">
          <el-option value="auth:login" label="用户登录" />
          <el-option value="instance:create" label="创建实例" />
          <el-option value="instance:delete" label="删除实例" />
          <el-option value="instance:start" label="启动实例" />
          <el-option value="instance:stop" label="停止实例" />
          <el-option value="instance:restart" label="重启实例" />
          <el-option value="secret:create" label="创建密钥" />
          <el-option value="secret:delete" label="删除密钥" />
          <el-option value="admin:user:update" label="修改用户" />
          <el-option value="admin:user:reset_password" label="重置密码" />
        </el-select>
        <el-select v-model="filterTarget" placeholder="目标类型" clearable style="width: 120px" @change="loadData">
          <el-option value="user" label="用户" />
          <el-option value="instance" label="实例" />
          <el-option value="secret" label="密钥" />
        </el-select>
        <el-input v-model="keyword" placeholder="搜索详情" clearable style="width: 180px" @clear="loadData" @keyup.enter="loadData" />
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>
    </div>

    <el-table :data="logs" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="操作人" width="100" />
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-tag size="small" :type="actionTagType(row.action)">{{ actionLabel(row.action) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="目标" width="100">
        <template #default="{ row }">
          <span v-if="row.target_type">{{ row.target_type }}#{{ row.target_id }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="详情" min-width="200">
        <template #default="{ row }">
          <span class="detail-text">{{ formatDetail(row.detail) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="ip_address" label="IP" width="120" />
      <el-table-column label="时间" width="150">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
    </el-table>

    <div v-if="total > pageSize" class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminAuditApi, type AuditLog } from '@/api/adminAudit'

const loading = ref(false)
const logs = ref<AuditLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const filterAction = ref('')
const filterTarget = ref('')
const keyword = ref('')

const ACTION_LABELS: Record<string, string> = {
  'auth:login': '用户登录',
  'instance:create': '创建实例',
  'instance:delete': '删除实例',
  'instance:start': '启动实例',
  'instance:stop': '停止实例',
  'instance:restart': '重启实例',
  'secret:create': '创建密钥',
  'secret:delete': '删除密钥',
  'admin:user:update': '修改用户',
  'admin:user:reset_password': '重置密码',
}

function actionLabel(action: string) {
  return ACTION_LABELS[action] || action
}

function actionTagType(action: string): string {
  if (action.includes('delete')) return 'danger'
  if (action.includes('create')) return 'success'
  if (action.includes('login')) return ''
  if (action.includes('admin')) return 'warning'
  return 'info'
}

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

function formatDetail(detail: string) {
  if (!detail || detail === '{}') return '-'
  try {
    const obj = JSON.parse(detail)
    return Object.entries(obj).map(([k, v]) => `${k}: ${v}`).join(', ')
  } catch {
    return detail
  }
}

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize }
    if (filterAction.value) params.action = filterAction.value
    if (filterTarget.value) params.target_type = filterTarget.value
    if (keyword.value) params.keyword = keyword.value
    const res = await adminAuditApi.list(params as any)
    logs.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.audit-page {
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.detail-text {
  font-size: 12px;
  color: var(--text-secondary);
  word-break: break-all;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .filters {
    width: 100%;
  }

  .filters .el-select,
  .filters .el-input {
    flex: 1;
    min-width: 0;
  }

  :deep(.el-table) {
    font-size: 12px;
  }
}
</style>
