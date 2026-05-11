<template>
  <div class="dashboard-page" ref="dashboardRef" v-loading="loading">
    <!-- Stats Cards -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon" style="background: #e0f2fe; color: #0284c7">
          <el-icon :size="24"><User /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.user_count }}</div>
          <div class="stat-label">用户总数</div>
          <div class="stat-sub">本周 +{{ stats.user_new_this_week }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fef3c7; color: #d97706">
          <el-icon :size="24"><Monitor /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.instance_total }}</div>
          <div class="stat-label">实例总数</div>
          <div class="stat-sub">本周 +{{ stats.instance_new_this_week }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #dcfce7; color: #16a34a">
          <el-icon :size="24"><CircleCheck /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.instance_running }}</div>
          <div class="stat-label">运行中</div>
          <div class="stat-sub">{{ runningPct }}%</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #f3e8ff; color: #9333ea">
          <el-icon :size="24"><ChatDotSquare /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.conversation_today }}</div>
          <div class="stat-label">今日对话</div>
          <div class="stat-sub">{{ convChange }}</div>
        </div>
      </div>
    </div>

    <!-- Charts Row 1 -->
    <div class="charts-row">
      <div class="chart-card">
        <h3>实例状态分布</h3>
        <div ref="statusChartRef" class="chart-container"></div>
      </div>
      <div class="chart-card">
        <h3>Token 消耗趋势（7天）</h3>
        <div ref="tokenChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- Charts Row 2 -->
    <div class="charts-row">
      <div class="chart-card">
        <h3>注册与实例创建趋势（7天）</h3>
        <div ref="activityChartRef" class="chart-container"></div>
      </div>
      <div class="chart-card">
        <h3>模型使用排行</h3>
        <div ref="modelChartRef" class="chart-container" v-if="data?.model_usage?.length"></div>
        <el-empty v-else description="暂无数据" :image-size="60" />
      </div>
    </div>

    <!-- Recent Logs -->
    <div class="chart-card full-width">
      <h3>最近操作日志</h3>
      <el-table :data="data?.recent_logs || []" stripe size="small" style="width: 100%">
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column label="操作" min-width="200">
          <template #default="{ row }">{{ formatAction(row.action) }}</template>
        </el-table-column>
        <el-table-column label="目标" width="120">
          <template #default="{ row }">
            <span v-if="row.target_type">{{ row.target_type }}#{{ row.target_id }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP" width="140" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { User, Monitor, CircleCheck, ChatDotSquare } from '@element-plus/icons-vue'
import { dashboardApi, type DashboardData } from '@/api/dashboard'
import * as echarts from 'echarts/core'
import { PieChart, LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([PieChart, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const loading = ref(false)
const data = ref<DashboardData | null>(null)

const statusChartRef = ref<HTMLElement>()
const tokenChartRef = ref<HTMLElement>()
const activityChartRef = ref<HTMLElement>()
const modelChartRef = ref<HTMLElement>()

let charts: echarts.ECharts[] = []

const stats = computed(() => data.value?.stats || {
  user_count: 0, user_new_this_week: 0,
  instance_total: 0, instance_new_this_week: 0,
  instance_running: 0, conversation_today: 0, conversation_yesterday: 0,
})

const runningPct = computed(() => {
  const t = stats.value.instance_total
  return t ? Math.round(stats.value.instance_running / t * 100) : 0
})

const convChange = computed(() => {
  const today = stats.value.conversation_today
  const yesterday = stats.value.conversation_yesterday
  if (!yesterday) return today ? `+${today}` : '-'
  const pct = Math.round((today - yesterday) / yesterday * 100)
  return pct >= 0 ? `+${pct}%` : `${pct}%`
})

const ACTION_MAP: Record<string, string> = {
  'auth:login': '登录',
  'instance:create': '创建实例',
  'instance:start': '启动实例',
  'instance:stop': '停止实例',
  'instance:delete': '删除实例',
  'instance:upgrade': '升级实例',
  'admin:user:create': '创建用户',
  'admin:user:update': '更新用户',
  'admin:invitation:create': '生成邀请码',
  'admin:invitation:update': '更新邀请码',
  'admin:invitation:delete': '删除邀请码',
}

function formatAction(action: string) {
  return ACTION_MAP[action] || action
}

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 16)
}

const STATUS_COLORS: Record<string, string> = {
  running: '#16a34a',
  stopped: '#9ca3af',
  error: '#dc2626',
  creating: '#3b82f6',
}

function initCharts() {
  if (!data.value) return

  // Instance status pie
  if (statusChartRef.value) {
    const chart = echarts.init(statusChartRef.value)
    charts.push(chart)
    const statusData = Object.entries(data.value.instance_status).map(([name, value]) => ({
      name, value, itemStyle: { color: STATUS_COLORS[name] || '#6b7280' },
    }))
    chart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      series: [{
        type: 'pie', radius: ['40%', '70%'], data: statusData,
        label: { formatter: '{b}\n{c}' },
      }],
    })
  }

  // Token trend line
  if (tokenChartRef.value) {
    const chart = echarts.init(tokenChartRef.value)
    charts.push(chart)
    const trend = data.value.token_trend
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 60, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: trend.map(t => t.date.slice(5)) },
      yAxis: { type: 'value' },
      series: [{ type: 'line', data: trend.map(t => t.tokens), smooth: true, areaStyle: { opacity: 0.15 }, itemStyle: { color: '#8b5cf6' } }],
    })
  }

  // Activity trend bar
  if (activityChartRef.value) {
    const chart = echarts.init(activityChartRef.value)
    charts.push(chart)
    const trend = data.value.activity_trend
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['注册用户', '创建实例'], bottom: 0 },
      grid: { left: 40, right: 20, top: 20, bottom: 40 },
      xAxis: { type: 'category', data: trend.map(t => t.date.slice(5)) },
      yAxis: { type: 'value', minInterval: 1 },
      series: [
        { name: '注册用户', type: 'bar', data: trend.map(t => t.users), itemStyle: { color: '#3b82f6' } },
        { name: '创建实例', type: 'bar', data: trend.map(t => t.instances), itemStyle: { color: '#f59e0b' } },
      ],
    })
  }

  // Model usage bar (horizontal)
  if (modelChartRef.value && data.value.model_usage.length) {
    const chart = echarts.init(modelChartRef.value)
    charts.push(chart)
    const usage = [...data.value.model_usage].reverse()
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 120, right: 40, top: 10, bottom: 20 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: usage.map(u => u.model) },
      series: [{ type: 'bar', data: usage.map(u => u.count), itemStyle: { color: '#06b6d4' }, barMaxWidth: 24 }],
    })
  }
}

let resizeObserver: ResizeObserver | null = null
const dashboardRef = ref<HTMLElement>()

function handleResize() {
  charts.forEach(c => c.resize())
}

async function loadData() {
  loading.value = true
  try {
    const res = await dashboardApi.get()
    data.value = res.data
    await nextTick()
    initCharts()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
  if (dashboardRef.value) {
    resizeObserver = new ResizeObserver(() => handleResize())
    resizeObserver.observe(dashboardRef.value)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  resizeObserver?.disconnect()
  charts.forEach(c => c.dispose())
  charts = []
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1200px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--text, #111);
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  margin-top: 2px;
}

.stat-sub {
  font-size: 12px;
  color: var(--text-muted, #9ca3af);
  margin-top: 2px;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.chart-card {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
  padding: 20px;
}

.chart-card h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text, #111);
}

.chart-container {
  width: 100%;
  height: 260px;
}

.full-width {
  margin-bottom: 20px;
}

@media (max-width: 900px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 500px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}
</style>
