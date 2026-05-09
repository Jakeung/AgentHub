<template>
  <div class="admin-users-page">
    <div class="page-header">
      <h2>用户管理</h2>
      <div class="filters">
        <el-input v-model="keyword" placeholder="搜索用户名/姓名" clearable style="width: 200px" @clear="loadData" @keyup.enter="loadData" />
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px" @change="loadData">
          <el-option value="active" label="正常" />
          <el-option value="disabled" label="禁用" />
        </el-select>
        <el-select v-model="filterRole" placeholder="角色" clearable style="width: 120px" @change="loadData">
          <el-option :value="1" label="管理员" />
          <el-option :value="2" label="普通用户" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>
    </div>

    <el-table :data="users" v-loading="loading" border stripe>
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role_name === 'admin' ? 'danger' : 'info'" size="small">
            {{ row.role_name === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
            {{ row.status === 'active' ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最后登录" width="150">
        <template #default="{ row }">
          {{ row.last_login_at ? formatTime(row.last_login_at) : '未登录' }}
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="150">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text @click="showEditDialog(row)">编辑</el-button>
          <el-button size="small" text @click="showPasswordDialog(row)">重置密码</el-button>
          <el-button
            v-if="row.status === 'active'"
            type="danger" size="small" text
            :disabled="row.role_name === 'admin'"
            @click="toggleStatus(row, 'disabled')"
          >禁用</el-button>
          <el-button
            v-else
            type="success" size="small" text
            @click="toggleStatus(row, 'active')"
          >启用</el-button>
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

    <!-- Edit User Dialog -->
    <el-dialog v-model="editVisible" title="编辑用户" width="440px" destroy-on-close>
      <el-form :model="editForm" label-width="70px">
        <el-form-item label="用户名">
          <el-input :model-value="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="editForm.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" maxlength="200" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role_id" style="width: 100%">
            <el-option :value="1" label="管理员" />
            <el-option :value="2" label="普通用户" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- Reset Password Dialog -->
    <el-dialog v-model="pwdVisible" title="重置密码" width="400px" destroy-on-close>
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="目标用户">
          <el-input :model-value="pwdForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.password" show-password placeholder="至少6位" maxlength="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="handleResetPassword">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminUserApi, type AdminUser } from '@/api/adminUser'

const loading = ref(false)
const users = ref<AdminUser[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const keyword = ref('')
const filterStatus = ref('')
const filterRole = ref<number | ''>('')

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 16)
}

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize }
    if (keyword.value) params.keyword = keyword.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterRole.value !== '') params.role_id = filterRole.value
    const res = await adminUserApi.list(params as any)
    users.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

// Edit
const editVisible = ref(false)
const saving = ref(false)
const editForm = reactive({ id: 0, username: '', name: '', email: '', role_id: 2 })

function showEditDialog(row: AdminUser) {
  editForm.id = row.id
  editForm.username = row.username
  editForm.name = row.name
  editForm.email = row.email
  editForm.role_id = row.role_id
  editVisible.value = true
}

async function handleEdit() {
  saving.value = true
  try {
    await adminUserApi.update(editForm.id, {
      name: editForm.name,
      email: editForm.email,
      role_id: editForm.role_id,
    })
    ElMessage.success('更新成功')
    editVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

// Reset Password
const pwdVisible = ref(false)
const resetting = ref(false)
const pwdForm = reactive({ id: 0, username: '', password: '' })

function showPasswordDialog(row: AdminUser) {
  pwdForm.id = row.id
  pwdForm.username = row.username
  pwdForm.password = ''
  pwdVisible.value = true
}

async function handleResetPassword() {
  if (pwdForm.password.length < 6) {
    ElMessage.warning('密码至少6位')
    return
  }
  resetting.value = true
  try {
    await adminUserApi.resetPassword(pwdForm.id, pwdForm.password)
    ElMessage.success('密码重置成功')
    pwdVisible.value = false
  } finally {
    resetting.value = false
  }
}

// Toggle status
async function toggleStatus(row: AdminUser, newStatus: string) {
  const label = newStatus === 'disabled' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确认${label}用户 "${row.username}"？`, `${label}确认`, { type: 'warning' })
    await adminUserApi.update(row.id, { status: newStatus })
    ElMessage.success(`${label}成功`)
  } catch (e: any) {
    if (e !== 'cancel' && e?.toString() !== 'cancel') {
      ElMessage.error(`${label}失败`)
    }
  } finally {
    loadData()
  }
}

onMounted(loadData)
</script>

<style scoped>
.admin-users-page {
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

  .filters .el-input,
  .filters .el-select {
    flex: 1;
    min-width: 0;
  }

  :deep(.el-table) {
    font-size: 12px;
  }
}
</style>
