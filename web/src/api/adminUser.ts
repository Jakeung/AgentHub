import request from './request'

export interface AdminUser {
  id: number
  username: string
  name: string
  email: string
  role_id: number
  role_name: string
  status: string
  last_login_at: string | null
  created_at: string
}

export const adminUserApi = {
  list: (params?: { status?: string; role_id?: number; keyword?: string; page?: number; page_size?: number }) =>
    request.get('/admin/users', { params }),

  update: (id: number, data: { name?: string; email?: string; role_id?: number; status?: string }) =>
    request.put(`/admin/users/${id}`, data),

  resetPassword: (id: number, new_password: string) =>
    request.put(`/admin/users/${id}/password`, { new_password }),
}
