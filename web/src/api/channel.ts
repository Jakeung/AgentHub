import request from './request'

export interface ChannelConfig {
  id: number
  platform: string
  platform_label: string
  config: Record<string, string>
  status: string
  created_at: string | null
}

export interface PlatformField {
  key: string
  label: string
  required: boolean
  secret: boolean
  placeholder: string
}

export interface PlatformSchema {
  label: string
  fields: PlatformField[]
}

export const channelApi = {
  platforms: () =>
    request.get('/channels/platforms'),

  list: () =>
    request.get('/channels'),

  create: (data: { platform: string; config: Record<string, string> }) =>
    request.post('/channels', data),

  update: (id: number, data: { config: Record<string, string> }) =>
    request.put(`/channels/${id}`, data),

  delete: (id: number) =>
    request.delete(`/channels/${id}`),

  weixinQrStart: () =>
    request.post('/channels/weixin/qr-login'),

  weixinQrStatus: () =>
    request.get('/channels/weixin/qr-status'),
}
