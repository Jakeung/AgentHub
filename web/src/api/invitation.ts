import request from './request'

export interface InvitationCode {
  id: number
  code: string
  max_uses: number
  used_count: number
  created_by: number
  expires_at: string | null
  is_active: boolean
  created_at: string
}

export interface CreateInvitationReq {
  count?: number
  max_uses?: number
  expires_at?: string
}

export const invitationApi = {
  list: (params?: { is_active?: boolean; page?: number; page_size?: number }) =>
    request.get('/admin/invitations', { params }),

  create: (data: CreateInvitationReq) =>
    request.post('/admin/invitations', data),

  update: (id: number, data: { is_active?: boolean; max_uses?: number }) =>
    request.put(`/admin/invitations/${id}`, data),

  delete: (id: number) =>
    request.delete(`/admin/invitations/${id}`),
}
