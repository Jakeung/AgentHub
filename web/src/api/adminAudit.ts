import request from './request'

export interface AuditLog {
  id: number
  user_id: number | null
  username: string
  action: string
  target_type: string
  target_id: number | null
  detail: string
  ip_address: string
  created_at: string
}

export const adminAuditApi = {
  list: (params?: { action?: string; user_id?: number; target_type?: string; keyword?: string; page?: number; page_size?: number }) =>
    request.get('/admin/audit-logs', { params }),
}
