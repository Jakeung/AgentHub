<template>
  <div class="invitations-page">
    <div class="page-header">
      <h2>邀请码管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        生成邀请码
      </el-button>
    </div>

    <div class="filter-bar">
      <el-radio-group v-model="statusFilter" @change="loadData">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="true">启用</el-radio-button>
        <el-radio-button label="false">停用</el-radio-button>
      </el-radio-group>
    </div>

    <el-table :data="items" v-loading="loading" border stripe style="width: 100%">
      <el-table-column label="邀请码" min-width="160">
        <template #default="{ row }">
          <div class="code-cell">
            <code>{{ row.code }}</code>
            <el-button type="primary" link size="small" @click="copyCode(row.code)">复制</el-button>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="max_uses" label="最大次数" width="100" align="center" />
      <el-table-column prop="used_count" label="已使用" width="80" align="center" />
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag v-if="!row.is_active" type="info" size="small">停用</el-tag>
          <el-tag v-else-if="row.used_count >= row.max_uses" type="warning" size="small">已满</el-tag>
          <el-tag v-else-if="row.expires_at && new Date(row.expires_at) < new Date()" type="danger" size="small">过期</el-tag>
          <el-tag v-else type="success" size="small">可用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="过期时间" width="160">
        <template #default="{ row }">
          {{ row.expires_at ? formatTime(row.expires_at) : '永不过期' }}
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="160">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <el-button
            v-if="row.is_active"
            type="warning"
            size="small"
            plain
            @click="toggleActive(row, false)"
          >停用</el-button>
          <el-button
            v-else
            type="success"
            size="small"
            plain
            @click="toggleActive(row, true)"
          >启用</el-button>
          <el-button
            type="danger"
            size="small"
            plain
            @click="handleDelete(row)"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="total > pageSize" class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadData"
      />
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreateDialog" title="生成邀请码" width="440px" destroy-on-close>
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="生成数量">
          <el-input-number v-model="createForm.count" :min="1" :max="50" />
        </el-form-item>
        <el-form-item label="可用次数">
          <el-input-number v-model="createForm.max_uses" :min="1" :max="10000" />
        </el-form-item>
        <el-form-item label="过期时间">
          <el-date-picker
            v-model="createForm.expires_at"
            type="datetime"
            placeholder="留空表示永不过期"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">生成</el-button>
      </template>
    </el-dialog>

    <!-- Result Dialog -->
    <el-dialog v-model="showResultDialog" title="生成成功" width="440px">
      <p style="margin-bottom: 12px">已生成 {{ generatedCodes.length }} 个邀请码：</p>
      <div class="codes-list">
        <div v-for="code in generatedCodes" :key="code" class="code-item">
          <code>{{ code }}</code>
          <el-button type="primary" link size="small" @click="copyCode(code)">复制</el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="copyAllCodes">复制全部</el-button>
        <el-button type="primary" @click="showResultDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { invitationApi, type InvitationCode } from '@/api/invitation'

const loading = ref(false)
const items = ref<InvitationCode[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const statusFilter = ref('')

const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = reactive({ count: 1, max_uses: 1, expires_at: null as Date | null })

const showResultDialog = ref(false)
const generatedCodes = ref<string[]>([])

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 16)
}

async function loadData() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize }
    if (statusFilter.value !== '') params.is_active = statusFilter.value === 'true'
    const res = await invitationApi.list(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  creating.value = true
  try {
    const data: any = {
      count: createForm.count,
      max_uses: createForm.max_uses,
    }
    if (createForm.expires_at) {
      data.expires_at = new Date(createForm.expires_at).toISOString()
    }
    const res = await invitationApi.create(data)
    if (res.code === 0) {
      generatedCodes.value = res.data.codes
      showCreateDialog.value = false
      showResultDialog.value = true
      loadData()
    } else {
      ElMessage.error(res.message || '生成失败')
    }
  } finally {
    creating.value = false
  }
}

async function toggleActive(row: InvitationCode, active: boolean) {
  await invitationApi.update(row.id, { is_active: active })
  ElMessage.success(active ? '已启用' : '已停用')
  loadData()
}

async function handleDelete(row: InvitationCode) {
  await ElMessageBox.confirm(`确认删除邀请码 "${row.code}" 吗？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  })
  await invitationApi.delete(row.id)
  ElMessage.success('删除成功')
  loadData()
}

function fallbackCopy(text: string) {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  document.execCommand('copy')
  document.body.removeChild(ta)
}

function copyCode(code: string) {
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(code).catch(() => fallbackCopy(code))
  } else {
    fallbackCopy(code)
  }
  ElMessage.success('已复制到剪贴板')
}

function copyAllCodes() {
  const text = generatedCodes.value.join('\n')
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).catch(() => fallbackCopy(text))
  } else {
    fallbackCopy(text)
  }
  ElMessage.success('已复制全部邀请码')
}

onMounted(loadData)
</script>

<style scoped>
.invitations-page {
  max-width: 1000px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.filter-bar {
  margin-bottom: 16px;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.code-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.code-cell code {
  font-family: monospace;
  font-size: 13px;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.codes-list {
  max-height: 300px;
  overflow-y: auto;
}

.code-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
}

.code-item code {
  font-family: monospace;
  font-size: 14px;
}
</style>
