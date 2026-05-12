import request from './request'

export const usageApi = {
  summary: () =>
    request.get('/usage/summary'),

  trend: (days = 30) =>
    request.get('/usage/trend', { params: { days } }),
}

export const adminUsageApi = {
  overview: () =>
    request.get('/admin/usage/overview'),

  byUser: () =>
    request.get('/admin/usage/by-user'),

  listPricing: () =>
    request.get('/admin/usage/model-pricing'),

  createPricing: (data: {
    model_name: string
    provider?: string
    input_price_per_1k?: number
    output_price_per_1k?: number
    currency?: string
    is_active?: boolean
  }) => request.post('/admin/usage/model-pricing', data),

  updatePricing: (id: number, data: {
    model_name: string
    provider?: string
    input_price_per_1k?: number
    output_price_per_1k?: number
    currency?: string
    is_active?: boolean
  }) => request.put(`/admin/usage/model-pricing/${id}`, data),
}
