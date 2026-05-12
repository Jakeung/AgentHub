<template>
  <div class="usage-page">
    <div class="page-header">
      <h2>用量统计</h2>
      <el-button text @click="$router.push('/user')">
        <el-icon><Back /></el-icon> 返回
      </el-button>
    </div>

    <!-- Summary Cards -->
    <div class="stat-cards" v-loading="loading">
      <div class="stat-card">
        <div class="stat-label">今日请求</div>
        <div class="stat-value">{{ summary.today?.requests || 0 }}</div>
        <div class="stat-sub">{{ formatTokens(summary.today?.total_tokens || 0) }} tokens</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">本周请求</div>
        <div class="stat-value">{{ summary.this_week?.requests || 0 }}</div>
        <div class="stat-sub">{{ formatTokens(summary.this_week?.total_tokens || 0) }} tokens</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">本月请求</div>
        <div class="stat-value">{{ summary.this_month?.requests || 0 }}</div>
        <div class="stat-sub">{{ formatTokens(summary.this_month?.total_tokens || 0) }} tokens</div>
      </div>
    </div>

    <!-- Trend Table -->
    <div class="section">
      <h3>每日用量明细（近 30 天）</h3>
      <el-table :data="trend" border stripe style="width: 100%" size="small">
        <el-table-column prop="date" label="日期" width="120" />
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
      <div v-if="!trend.length && !loading" class="empty-tip">暂无用量数据</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usageApi } from '../../../api/usage'

const loading = ref(false)
const summary = ref<any>({})
const trend = ref<any[]>([])

function formatTokens(n: number): string {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(n)
}

async function loadData() {
  loading.value = true
  try {
    const [sumRes, trendRes] = await Promise.all([
      usageApi.summary(),
      usageApi.trend(30),
    ])
    summary.value = sumRes.data || {}
    trend.value = (trendRes.data || []).reverse()
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.usage-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
}
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
}
.stat-label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #111;
}
.stat-sub {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}
.section {
  margin-bottom: 24px;
}
.section h3 {
  font-size: 15px;
  margin: 0 0 12px;
}
.empty-tip {
  text-align: center;
  color: #9ca3af;
  padding: 40px 0;
  font-size: 14px;
}
</style>
