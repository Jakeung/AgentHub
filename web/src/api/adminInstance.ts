import request from './request'

export const adminInstanceApi = {
  list: (params?: { status?: string; owner_id?: number; keyword?: string; page?: number; page_size?: number }) =>
    request.get('/admin/instances', { params }),

  get: (id: number) =>
    request.get(`/admin/instances/${id}`),

  start: (id: number) =>
    request.post(`/admin/instances/${id}/start`),

  stop: (id: number) =>
    request.post(`/admin/instances/${id}/stop`),

  restart: (id: number) =>
    request.post(`/admin/instances/${id}/restart`),

  delete: (id: number) =>
    request.delete(`/admin/instances/${id}`),

  logs: (id: number, tail = 200) =>
    request.get(`/admin/instances/${id}/logs`, { params: { tail } }),
}
