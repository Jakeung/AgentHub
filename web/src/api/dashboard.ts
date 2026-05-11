import request from './request'

export interface DashboardData {
  stats: {
    user_count: number
    user_new_this_week: number
    instance_total: number
    instance_new_this_week: number
    instance_running: number
    conversation_today: number
    conversation_yesterday: number
  }
  instance_status: Record<string, number>
  token_trend: { date: string; tokens: number }[]
  activity_trend: { date: string; users: number; instances: number }[]
  model_usage: { model: string; count: number; percentage: number }[]
  recent_logs: {
    username: string
    action: string
    target_type: string
    target_id: number | null
    ip_address: string
    created_at: string
  }[]
}

export const dashboardApi = {
  get: () => request.get<DashboardData>('/admin/dashboard'),
}
