import request from './request'

export interface Secret {
  id: number
  name: string
  provider: string
  model_name: string
  is_active: boolean
  key_suffix: string
  last_used_at: string | null
  created_at: string
}

export const secretApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    request.get('/secrets', { params }),

  create: (data: { name: string; provider: string; model_name: string; api_key: string }) =>
    request.post('/secrets', data),

  update: (id: number, data: { name?: string; provider?: string; model_name?: string; api_key?: string }) =>
    request.put(`/secrets/${id}`, data),

  delete: (id: number) =>
    request.delete(`/secrets/${id}`),

  activate: (id: number) =>
    request.post(`/secrets/${id}/activate`),

  availableModels: () =>
    request.get('/secrets/available-models'),
}
