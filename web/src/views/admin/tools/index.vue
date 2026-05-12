<template>
  <div class="admin-tools">
    <div class="page-header">
      <h2>工具管理</h2>
      <el-button type="primary" @click="showCreateDialog">+ 注册新工具</el-button>
    </div>

    <el-table :data="tools" v-loading="loading" border stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="标识符" width="120" />
      <el-table-column prop="display_name" label="显示名称" width="120" />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column prop="category" label="分类" width="90" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="需要 Key" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.requires_api_key" type="warning" size="small">是</el-tag>
          <span v-else class="text-muted">否</span>
        </template>
      </el-table-column>
      <el-table-column prop="sort_order" label="排序" width="70" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text @click="editTool(row)">编辑</el-button>
          <el-button
            size="small" text
            :type="row.is_active ? 'warning' : 'success'"
            @click="toggleActive(row)"
          >{{ row.is_active ? '停用' : '启用' }}</el-button>
          <el-button type="danger" size="small" text @click="deleteTool(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑工具' : '注册新工具'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="标识符" :disabled="isEditing">
          <el-input v-model="form.name" :disabled="isEditing" placeholder="如 web, terminal" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="form.display_name" placeholder="如 网络搜索" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="form.category" placeholder="search / code / file" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="如 search, terminal" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="需要 API Key">
          <el-switch v-model="form.requires_api_key" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveTool">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminToolsApi } from '../../../api/adminTools'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const saving = ref(false)
const tools = ref<any[]>([])
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)

const form = ref({
  name: '',
  display_name: '',
  description: '',
  category: '',
  icon: '',
  sort_order: 0,
  requires_api_key: false,
  is_active: true,
})

async function loadData() {
  loading.value = true
  try {
    const res = await adminToolsApi.list({ page: 1, page_size: 100 })
    tools.value = res.data?.items || []
  } finally {
    loading.value = false
  }
}

function showCreateDialog() {
  isEditing.value = false
  editingId.value = null
  form.value = { name: '', display_name: '', description: '', category: '', icon: '', sort_order: 0, requires_api_key: false, is_active: true }
  dialogVisible.value = true
}

function editTool(row: any) {
  isEditing.value = true
  editingId.value = row.id
  form.value = {
    name: row.name,
    display_name: row.display_name,
    description: row.description || '',
    category: row.category || '',
    icon: row.icon || '',
    sort_order: row.sort_order || 0,
    requires_api_key: row.requires_api_key || false,
    is_active: row.is_active,
  }
  dialogVisible.value = true
}

async function saveTool() {
  saving.value = true
  try {
    if (isEditing.value && editingId.value) {
      const { name, ...data } = form.value
      await adminToolsApi.update(editingId.value, data)
      ElMessage.success('更新成功')
    } else {
      await adminToolsApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadData()
  } finally {
    saving.value = false
  }
}

async function toggleActive(row: any) {
  await adminToolsApi.update(row.id, { is_active: !row.is_active })
  ElMessage.success(row.is_active ? '已停用' : '已启用')
  await loadData()
}

async function deleteTool(row: any) {
  await ElMessageBox.confirm(`确定删除工具 "${row.display_name}"？`, '确认删除', { type: 'warning' })
  await adminToolsApi.delete(row.id)
  ElMessage.success('已删除')
  await loadData()
}

onMounted(loadData)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
}
.text-muted {
  color: #999;
  font-size: 13px;
}
</style>
