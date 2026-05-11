<template>
  <div class="instances-page">
    <!-- Header -->
    <div class="page-header">
      <h2>我的实例</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        创建实例
      </el-button>
    </div>

    <!-- Filter -->
    <div class="filter-bar">
      <el-radio-group v-model="statusFilter" @change="loadInstances">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="running">运行中</el-radio-button>
        <el-radio-button label="stopped">已停止</el-radio-button>
        <el-radio-button label="error">异常</el-radio-button>
      </el-radio-group>
    </div>

    <!-- Instance Cards -->
    <div v-loading="loading" class="cards-container">
      <el-empty v-if="!loading && instances.length === 0" description="暂无实例，点击右上角创建" />
      <div v-else class="cards-grid">
        <div
          v-for="inst in instances"
          :key="inst.id"
          class="instance-card"
          :class="'status-' + inst.status"
        >
          <div class="card-header">
            <span class="card-name clickable" @click="openDetail(inst)">{{ inst.name }}</span>
            <el-tag :type="statusTagType(inst.status)" size="small">
              {{ statusLabel(inst.status) }}
            </el-tag>
          </div>
          <div class="card-body">
            <div class="card-info">
              <span class="info-label">容器</span>
              <span class="info-value">{{ inst.container_name }}</span>
            </div>
            <div class="card-info">
              <span class="info-label">端口</span>
              <span v-if="inst.status === 'running'" class="info-value">
                <a :href="getDashUrl(inst.port)" target="_blank" class="clickable">{{ inst.port }}</a>
              </span>
              <span v-else class="info-value">{{ inst.port }}</span>
            </div>
            <div class="card-info">
              <span class="info-label">资源</span>
              <span class="info-value">{{ inst.cpu_limit }} Core / {{ inst.memory_limit_mb }} MB</span>
            </div>
            <div class="card-info">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{ formatTime(inst.created_at) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <el-button
              v-if="inst.status === 'stopped' || inst.status === 'error'"
              type="success"
              size="small"
              :loading="inst._actionLoading"
              @click="handleStart(inst)"
            >启动</el-button>
            <el-button
              v-if="inst.status === 'running'"
              type="warning"
              size="small"
              :loading="inst._actionLoading"
              @click="handleStop(inst)"
            >停止</el-button>
            <el-button
              v-if="inst.status === 'running'"
              size="small"
              :loading="inst._actionLoading"
              @click="handleRestart(inst)"
            >重启</el-button>
            <el-button
              v-if="inst.status === 'running'"
              type="primary"
              size="small"
              @click="goChat(inst)"
            >对话</el-button>
            <el-button
              v-if="upgradeAvailable[inst.id]?.available"
              type="info"
              size="small"
              :loading="inst._actionLoading"
              @click="handleUpgrade(inst)"
            >升级</el-button>
            <el-button
              type="danger"
              size="small"
              plain
              @click="handleDelete(inst)"
            >删除</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > pageSize" class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadInstances"
      />
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreateDialog" title="创建实例" width="500px" destroy-on-close>
      <el-form :model="createForm" label-width="100px" :rules="createRules" ref="createFormRef">
        <el-form-item label="实例名称" prop="name">
          <el-input v-model="createForm.name" placeholder="为实例起个名字" maxlength="50" />
        </el-form-item>
        <el-form-item label="CPU 核数">
          <el-input-number v-model="createForm.cpu_limit" :min="0.5" :max="4" :step="0.5" />
        </el-form-item>
        <el-form-item label="内存 (MB)">
          <el-select v-model="createForm.memory_limit_mb" style="width: 100%">
            <el-option :value="1024" label="1024 MB" />
            <el-option :value="2048" label="2048 MB" />
            <el-option :value="4096" label="4096 MB" />
            <el-option :value="8192" label="8192 MB" />
          </el-select>
        </el-form-item>
        <el-form-item label="环境变量">
          <div v-for="(_, idx) in envPairs" :key="idx" class="env-row">
            <el-input v-model="envPairs[idx].key" placeholder="KEY" style="width: 40%" />
            <el-input v-model="envPairs[idx].value" placeholder="VALUE" style="width: 45%; margin-left: 4px" />
            <el-button type="danger" text size="small" @click="envPairs.splice(idx, 1)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-button text type="primary" size="small" @click="envPairs.push({ key: '', value: '' })">
            + 添加变量
          </el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- Detail Drawer -->
    <el-drawer
      v-model="showDetail"
      :title="detailInstance?.name || '实例详情'"
      size="560px"
      destroy-on-close
    >
      <template v-if="detailInstance">
        <el-tabs v-model="detailTab">
          <!-- Info Tab -->
          <el-tab-pane label="基本信息" name="info">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="实例名称">{{ detailInstance.name }}</el-descriptions-item>
              <el-descriptions-item label="容器名">{{ detailInstance.container_name }}</el-descriptions-item>
              <el-descriptions-item label="端口">{{ detailInstance.port }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="statusTagType(detailInstance.status)" size="small">
                  {{ statusLabel(detailInstance.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="健康状态">{{ detailInstance.health_status }}</el-descriptions-item>
              <el-descriptions-item label="CPU">{{ detailInstance.cpu_limit }} Core</el-descriptions-item>
              <el-descriptions-item label="内存">{{ detailInstance.memory_limit_mb }} MB</el-descriptions-item>
              <el-descriptions-item label="数据目录">{{ detailInstance.data_dir }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatTime(detailInstance.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="更新时间">{{ formatTime(detailInstance.updated_at) }}</el-descriptions-item>
            </el-descriptions>
            <div v-if="Object.keys(detailInstance.env_config || {}).length" style="margin-top: 16px">
              <h4 style="margin-bottom: 8px">环境变量</h4>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item
                  v-for="(val, key) in detailInstance.env_config"
                  :key="key"
                  :label="String(key)"
                >{{ val }}</el-descriptions-item>
              </el-descriptions>
            </div>
          </el-tab-pane>

          <!-- Logs Tab -->
          <el-tab-pane label="运行日志" name="logs">
            <div class="logs-toolbar">
              <el-select v-model="logTail" size="small" style="width: 120px" @change="fetchLogs">
                <el-option :value="50" label="最近 50 行" />
                <el-option :value="100" label="最近 100 行" />
                <el-option :value="500" label="最近 500 行" />
              </el-select>
              <el-button size="small" @click="fetchLogs" :loading="logsLoading">刷新</el-button>
            </div>
            <pre class="logs-content" v-loading="logsLoading">{{ logs || '暂无日志' }}</pre>
          </el-tab-pane>

          <!-- Edit Tab -->
          <el-tab-pane label="编辑配置" name="edit">
            <el-form :model="editForm" label-width="100px" size="small">
              <el-form-item label="实例名称">
                <el-input v-model="editForm.name" maxlength="50" />
              </el-form-item>
              <el-form-item label="CPU 核数">
                <el-input-number v-model="editForm.cpu_limit" :min="0.5" :max="4" :step="0.5" />
              </el-form-item>
              <el-form-item label="内存 (MB)">
                <el-select v-model="editForm.memory_limit_mb" style="width: 100%">
                  <el-option :value="1024" label="1024 MB" />
                  <el-option :value="2048" label="2048 MB" />
                  <el-option :value="4096" label="4096 MB" />
                  <el-option :value="8192" label="8192 MB" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { instanceApi, type Instance } from '@/api/instance'

const router = useRouter()

// State
const loading = ref(false)
const instances = ref<(Instance & { _actionLoading?: boolean })[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const statusFilter = ref('')
const upgradeAvailable = ref<Record<number, { available: boolean }>>({})

// Create dialog
const showCreateDialog = ref(false)
const creating = ref(false)
const createFormRef = ref()
const createForm = reactive({
  name: '',
  cpu_limit: 1,
  memory_limit_mb: 2048,
})
const envPairs = ref<{ key: string; value: string }[]>([])
const createRules = {
  name: [{ required: true, message: '请输入实例名称', trigger: 'blur' }],
}

// Helpers
function statusTagType(status: string) {
  const map: Record<string, string> = {
    running: 'success',
    stopped: 'info',
    error: 'danger',
    creating: 'warning',
  }
  return map[status] || 'info'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    running: '运行中',
    stopped: '已停止',
    error: '异常',
    creating: '创建中',
    deleted: '已删除',
  }
  return map[status] || status
}

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 16)
}

// Data loading
async function loadInstances() {
  loading.value = true
  try {
    const res = await instanceApi.list({
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

async function loadUpgradeStatus() {
  try {
    const res = await instanceApi.checkUpgrade()
    if (res.code === 0) {
      upgradeAvailable.value = res.data
    }
  } catch {
    // ignore — upgrade check is non-critical
  }
}

// Actions
async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  const envConfig: Record<string, string> = {}
  envPairs.value.forEach((p) => {
    if (p.key.trim()) envConfig[p.key.trim()] = p.value
  })

  creating.value = true
  try {
    await instanceApi.create({
      name: createForm.name,
      cpu_limit: createForm.cpu_limit,
      memory_limit_mb: createForm.memory_limit_mb,
      env_config: Object.keys(envConfig).length > 0 ? envConfig : undefined,
    })
    ElMessage.success('实例创建成功')
    showCreateDialog.value = false
    createForm.name = ''
    envPairs.value = []
    loadInstances()
  } finally {
    creating.value = false
  }
}

async function handleStart(inst: Instance & { _actionLoading?: boolean }) {
  inst._actionLoading = true
  try {
    const res = await instanceApi.start(inst.id)
    if (res.code === 0) {
      ElMessage.success('启动指令已发送')
    } else {
      ElMessage.error(res.message || '启动失败')
    }
    loadInstances()
  } catch (e: any) {
    ElMessage.error(e?.message || '启动请求失败')
  } finally {
    inst._actionLoading = false
  }
}

async function handleStop(inst: Instance & { _actionLoading?: boolean }) {
  inst._actionLoading = true
  try {
    const res = await instanceApi.stop(inst.id)
    if (res.code === 0) {
      ElMessage.success('停止指令已发送')
    } else {
      ElMessage.error(res.message || '停止失败')
    }
    loadInstances()
  } catch (e: any) {
    ElMessage.error(e?.message || '停止请求失败')
  } finally {
    inst._actionLoading = false
  }
}

async function handleRestart(inst: Instance & { _actionLoading?: boolean }) {
  inst._actionLoading = true
  try {
    const res = await instanceApi.restart(inst.id)
    if (res.code === 0) {
      ElMessage.success('重启指令已发送')
    } else {
      ElMessage.error(res.message || '重启失败')
    }
    loadInstances()
  } catch (e: any) {
    ElMessage.error(e?.message || '重启请求失败')
  } finally {
    inst._actionLoading = false
  }
}

async function handleUpgrade(inst: Instance & { _actionLoading?: boolean }) {
  await ElMessageBox.confirm(
    '升级将拉取最新镜像并重建容器，您的对话记录、记忆和配置都会保留。是否继续？',
    '升级确认',
    { type: 'info', confirmButtonText: '确认升级', cancelButtonText: '取消' },
  )
  inst._actionLoading = true
  try {
    const res = await instanceApi.upgrade(inst.id)
    if (res.code === 0) {
      ElMessage.success('升级完成，实例已停止，请手动启动')
    } else {
      ElMessage.error(res.message || '升级失败')
    }
    loadInstances()
    loadUpgradeStatus()
  } catch (e: any) {
    ElMessage.error(e?.message || '升级请求失败')
  } finally {
    inst._actionLoading = false
  }
}

async function handleDelete(inst: Instance) {
  await ElMessageBox.confirm(`确认删除实例 "${inst.name}" 吗？此操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  })
  await instanceApi.delete(inst.id)
  ElMessage.success('删除成功')
  loadInstances()
}

function goChat(inst: Instance) {
  window.open(getDashUrl(inst.port), `hermes-${inst.id}`)
}

function getDashUrl(port: number) {
  return `${window.location.protocol}//${window.location.hostname}:${port}`
}

// Detail drawer
const showDetail = ref(false)
const detailInstance = ref<Instance | null>(null)
const detailTab = ref('info')
const logs = ref('')
const logsLoading = ref(false)
const logTail = ref(100)
const saving = ref(false)
const editForm = reactive({
  name: '',
  cpu_limit: 1,
  memory_limit_mb: 2048,
})

function openDetail(inst: Instance) {
  detailInstance.value = inst
  detailTab.value = 'info'
  editForm.name = inst.name
  editForm.cpu_limit = inst.cpu_limit
  editForm.memory_limit_mb = inst.memory_limit_mb
  logs.value = ''
  showDetail.value = true
}

async function fetchLogs() {
  if (!detailInstance.value) return
  logsLoading.value = true
  try {
    const res = await instanceApi.logs(detailInstance.value.id, logTail.value)
    logs.value = Array.isArray(res.data.logs) ? res.data.logs.join('\n') : res.data.logs
  } catch {
    logs.value = '获取日志失败'
  } finally {
    logsLoading.value = false
  }
}

async function handleSave() {
  if (!detailInstance.value) return
  saving.value = true
  try {
    await instanceApi.update(detailInstance.value.id, {
      name: editForm.name,
      cpu_limit: editForm.cpu_limit,
      memory_limit_mb: editForm.memory_limit_mb,
    })
    ElMessage.success('保存成功')
    showDetail.value = false
    loadInstances()
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadInstances()
  loadUpgradeStatus()
})
</script>

<style scoped>
.instances-page {
  max-width: 1200px;
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
  margin-bottom: 20px;
}

.cards-container {
  min-height: 200px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.instance-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  background: var(--bg-card);
  transition: box-shadow 0.2s, transform 0.2s;
}

.instance-card:hover {
  box-shadow: var(--shadow);
  transform: translateY(-2px);
}

.instance-card.status-running {
  border-left: 3px solid #22c55e;
}

.instance-card.status-stopped {
  border-left: 3px solid #94a3b8;
}

.instance-card.status-error {
  border-left: 3px solid #ef4444;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-name {
  font-weight: 600;
  font-size: 15px;
  color: var(--text);
}

.card-body {
  margin-bottom: 12px;
}

.card-info {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.info-label {
  color: var(--text-muted);
}

.card-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

.env-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.clickable {
  cursor: pointer;
  color: var(--primary);
}

.clickable:hover {
  text-decoration: underline;
}

.logs-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
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
  .cards-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>
