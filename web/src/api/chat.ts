import request from './request'

export interface ConversationItem {
  uuid: string
  title: string
  instance_id: number
  message_count: number
  created_at: string
  updated_at: string
}

export interface MessageItem {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export const chatApi = {
  listConversations: (params?: { instance_id?: number; page?: number; page_size?: number }) =>
    request.get('/chat/conversations', { params }),

  getMessages: (conversationUuid: string) =>
    request.get(`/chat/conversations/${conversationUuid}/messages`),

  deleteConversation: (conversationUuid: string) =>
    request.delete(`/chat/conversations/${conversationUuid}`),
}
