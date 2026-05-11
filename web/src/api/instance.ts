import request from './request'

export interface Instance {
  id: number
  name: string
  container_name: string
  port: number
  status: string
  health_status: string
  cpu_limit: number
  memory_limit_mb: number
  data_dir: string
  env_config: Record<string, string>
  created_at: string
  updated_at: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface CreateInstanceReq {
  name: string
  cpu_limit?: number
  memory_limit_mb?: number
  env_config?: Record<string, string>
}

export interface UpdateInstanceReq {
  name?: string
  cpu_limit?: number
  memory_limit_mb?: number
  env_config?: Record<string, string>
}

export const instanceApi = {
  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    request.get('/instances', { params }),

  get: (id: number) =>
    request.get(`/instances/${id}`),

  create: (data: CreateInstanceReq) =>
    request.post('/instances', data),

  update: (id: number, data: UpdateInstanceReq) =>
    request.put(`/instances/${id}`, data),

  delete: (id: number) =>
    request.delete(`/instances/${id}`),

  start: (id: number) =>
    request.post(`/instances/${id}/start`),

  stop: (id: number) =>
    request.post(`/instances/${id}/stop`),

  restart: (id: number) =>
    request.post(`/instances/${id}/restart`),

  upgrade: (id: number) =>
    request.post(`/instances/${id}/upgrade`),

  checkUpgrade: () =>
    request.get('/instances/upgrade-available'),

  logs: (id: number, tail = 100) =>
    request.get(`/instances/${id}/logs`, { params: { tail } }),

  stats: (id: number) =>
    request.get(`/instances/${id}/stats`),
}
