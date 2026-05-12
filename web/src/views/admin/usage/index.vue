<template>
  <div class="admin-usage">
    <div class="page-header">
      <h2>用量统计</h2>
    </div>

    <!-- Overview Cards -->
    <div class="stat-cards" v-loading="loading">
      <div class="stat-card">
        <div class="stat-label">本月请求数</div>
        <div class="stat-value">{{ overview.this_month?.requests || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">本月 Token</div>
        <div class="stat-value">{{ formatTokens(overview.this_month?.total_tokens || 0) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">活跃用户</div>
        <div class="stat-value">{{ overview.active_users || 0 }}</div>
      </div>
    </div>

    <!-- By User Table -->
    <div class="section">
      <h3>按用户统计（本月）</h3>
      <el-table :data="userStats" border stripe style="width: 100%">
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="requests" label="请求数" width="100" />
        <el-table-column label="输入 Token" width="120">
          <template #default="{ row }">{{ formatTokens(row.prompt_tokens) }}</template>
        </el-table-column>
        <el-table-column label="输出 Token" width="120">
          <template #default="{ row }">{{ formatTokens(row.completion_tokens) }}</template>
        </el-table-column>
        <el-table-column label="总 Token" width="120">
          <template #default="{ row }">{{ formatTokens(row.total_tokens) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Model Pricing -->
    <div class="section">
      <div class="section-header">
        <h3>模型定价</h3>
        <el-button size="small" type="primary" @click="showPricingDialog">+ 添加</el-button>
      </div>
      <el-table :data="pricing" border stripe style="width: 100%">
        <el-table-column prop="model_name" label="模型" width="200" />
        <el-table-column prop="provider" label="供应商" width="120" />
        <el-table-column label="输入价格" width="140">
          <template #default="{ row }">{{ row.currency }} {{ row.input_price_per_1k }}/1K</template>
        </el-table-column>
        <el-table-column label="输出价格" width="140">
          <template #default="{ row }">{{ row.currency }} {{ row.output_price_per_1k }}/1K</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" text @click="editPricing(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Pricing Dialog -->
    <el-dialog v-model="pricingDialogVisible" :title="editingPricingId ? '编辑定价' : '添加定价'" width="420px">
      <el-form :model="pricingForm" label-width="100px">
        <el-form-item label="模型名称">
          <el-input v-model="pricingForm.model_name" placeholder="如 deepseek-chat" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="pricingForm.provider" placeholder="如 deepseek" />
        </el-form-item>
        <el-form-item label="输入价格/1K">
          <el-input-number v-model="pricingForm.input_price_per_1k" :precision="4" :step="0.001" :min="0" />
        </el-form-item>
        <el-form-item label="输出价格/1K">
          <el-input-number v-model="pricingForm.output_price_per_1k" :precision="4" :step="0.001" :min="0" />
        </el-form-item>
        <el-form-item label="货币">
          <el-select v-model="pricingForm.currency" style="width: 100px">
            <el-option value="CNY" label="CNY" />
            <el-option value="USD" label="USD" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pricingDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePricing">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminUsageApi } from '../../../api/usage'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const overview = ref<any>({})
const userStats = ref<any[]>([])
const pricing = ref<any[]>([])
const pricingDialogVisible = ref(false)
const editingPricingId = ref<number | null>(null)
const pricingForm = ref({
  model_name: '',
  provider: '',
  input_price_per_1k: 0,
  output_price_per_1k: 0,
  currency: 'CNY',
})

function formatTokens(n: number): string {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(n)
}

async function loadData() {
  loading.value = true
  try {
    const [ovRes, userRes, priceRes] = await Promise.all([
      adminUsageApi.overview(),
      adminUsageApi.byUser(),
      adminUsageApi.listPricing(),
    ])
    overview.value = ovRes.data || {}
    userStats.value = userRes.data || []
    pricing.value = priceRes.data || []
  } finally {
    loading.value = false
  }
}

function showPricingDialog() {
  editingPricingId.value = null
  pricingForm.value = { model_name: '', provider: '', input_price_per_1k: 0, output_price_per_1k: 0, currency: 'CNY' }
  pricingDialogVisible.value = true
}

function editPricing(row: any) {
  editingPricingId.value = row.id
  pricingForm.value = {
    model_name: row.model_name,
    provider: row.provider || '',
    input_price_per_1k: row.input_price_per_1k,
    output_price_per_1k: row.output_price_per_1k,
    currency: row.currency || 'CNY',
  }
  pricingDialogVisible.value = true
}

async function savePricing() {
  try {
    if (editingPricingId.value) {
      await adminUsageApi.updatePricing(editingPricingId.value, pricingForm.value)
    } else {
      await adminUsageApi.createPricing(pricingForm.value)
    }
    ElMessage.success('保存成功')
    pricingDialogVisible.value = false
    await loadData()
  } catch {}
}

onMounted(loadData)
</script>

<style scoped>
.page-header {
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
}
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
}
.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
}
.section {
  margin-bottom: 24px;
}
.section h3 {
  font-size: 15px;
  margin: 0 0 12px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.section-header h3 {
  margin: 0;
}
</style>
