import request from './request'

export interface ToolItem {
  name: string
  display_name: string
  description: string
  category: string
  icon: string
  config_schema: Record<string, any>
  requires_api_key: boolean
  enabled: boolean
  config: Record<string, string>
}

export interface ToolUpdateItem {
  tool_name: string
  enabled: boolean
  config?: Record<string, string>
}

export const toolsApi = {
  list: (instanceId: number) =>
    request.get(`/instances/${instanceId}/tools`),

  update: (instanceId: number, tools: ToolUpdateItem[]) =>
    request.put(`/instances/${instanceId}/tools`, { tools }),
}
