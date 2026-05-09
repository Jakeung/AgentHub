import request from './request'

export interface SystemSetting {
  id: number
  key: string
  value: string
  description: string
}

export interface SettingUpdate {
  key: string
  value: string
  description?: string
}

export const adminSettingsApi = {
  list: () => request.get('/admin/settings'),

  update: (settings: SettingUpdate[]) =>
    request.put('/admin/settings', { settings }),

  testConnection: () => request.post('/admin/settings/test'),
}
