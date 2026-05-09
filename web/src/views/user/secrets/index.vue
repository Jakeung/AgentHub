<template>
  <div class="secrets-page">
    <div class="page-header">
      <h2>密钥管理</h2>
      <el-button type="primary" @click="showDialog('create')">
        <el-icon><Plus /></el-icon>
        添加密钥
      </el-button>
    </div>

    <el-table :data="secrets" v-loading="loading" border stripe>
      <el-table-column prop="name" label="名称" min-width="150" />
      <el-table-column prop="provider" label="提供商" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ row.provider }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="密钥" width="140">
        <template #default="{ row }">
          <code>****{{ row.key_suffix }}</code>
        </template>
      </el-table-column>
      <el-table-column label="最后使用" width="150">
        <template #default="{ row }">
          {{ row.last_used_at ? formatTime(row.last_used_at) : '未使用' }}
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="150">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text @click="showDialog('edit', row)">编辑</el-button>
          <el-button type="danger" size="small" text @click="handleDelete(row)">删除</el-button>
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

    <!-- Create / Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? '添加密钥' : '编辑密钥'" width="460px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：DeepSeek 生产密钥" maxlength="100" />
        </el-form-item>
        <el-form-item label="提供商" prop="provider">
          <el-select v-model="form.provider" placeholder="选择提供商" style="width: 100%">
            <el-option value="deepseek" label="DeepSeek" />
            <el-option value="openai" label="OpenAI" />
            <el-option value="anthropic" label="Anthropic" />
            <el-option value="custom" label="自定义" />
          </el-select>
        </el-form-item>
        <el-form-item label="API Key" :prop="dialogMode === 'create' ? 'api_key' : undefined">
          <el-input
            v-model="form.api_key"
            :placeholder="dialogMode === 'edit' ? '留空则不修改' : '输入 API Key'"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { secretApi, type Secret } from '@/api/secret'

const loading = ref(false)
const secrets = ref<Secret[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

// Dialog
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref()
const form = reactive({
  name: '',
  provider: 'deepseek',
  api_key: '',
})
const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择提供商', trigger: 'change' }],
  api_key: [{ required: true, message: '请输入 API Key', trigger: 'blur' }],
}

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 16)
}

async function loadData() {
  loading.value = true
  try {
    const res = await secretApi.list({ page: page.value, page_size: pageSize })
    secrets.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function showDialog(mode: 'create' | 'edit', row?: Secret) {
  dialogMode.value = mode
  if (mode === 'edit' && row) {
    editingId.value = row.id
    form.name = row.name
    form.provider = row.provider
    form.api_key = ''
  } else {
    editingId.value = null
    form.name = ''
    form.provider = 'deepseek'
    form.api_key = ''
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (dialogMode.value === 'create') {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return
  }

  saving.value = true
  try {
    if (dialogMode.value === 'create') {
      await secretApi.create({
        name: form.name,
        provider: form.provider,
        api_key: form.api_key,
      })
      ElMessage.success('密钥添加成功')
    } else {
      const data: Record<string, string> = { name: form.name, provider: form.provider }
      if (form.api_key) data.api_key = form.api_key
      await secretApi.update(editingId.value!, data)
      ElMessage.success('密钥更新成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: Secret) {
  await ElMessageBox.confirm(`确认删除密钥 "${row.name}"？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确认删除',
  })
  await secretApi.delete(row.id)
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.secrets-page {
  max-width: 960px;
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

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  :deep(.el-table) {
    font-size: 12px;
  }
}
</style>
