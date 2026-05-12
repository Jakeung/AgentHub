import request from './request'

export const adminToolsApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    request.get('/admin/tools', { params }),

  create: (data: {
    name: string
    display_name: string
    description?: string
    category?: string
    icon?: string
    config_schema?: Record<string, any>
    default_config?: Record<string, any>
    is_active?: boolean
    requires_api_key?: boolean
    sort_order?: number
  }) => request.post('/admin/tools', data),

  update: (id: number, data: {
    display_name?: string
    description?: string
    category?: string
    icon?: string
    config_schema?: Record<string, any>
    default_config?: Record<string, any>
    is_active?: boolean
    requires_api_key?: boolean
    sort_order?: number
  }) => request.put(`/admin/tools/${id}`, data),

  delete: (id: number) =>
    request.delete(`/admin/tools/${id}`),
}
