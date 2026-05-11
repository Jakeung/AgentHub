import request from './request'

export interface InstalledSkill {
  name: string
  display_name: string
  description: string
  category: string
  source: string
  enabled: boolean
  tags: string[]
}

export interface AvailableSkill {
  name: string
  display_name: string
  description: string
  source: string
  installed: boolean
  tags: string[]
}

export interface SkillCategory {
  name: string
  display_name: string
  skills: AvailableSkill[]
}

export const skillsApi = {
  list: (instanceId: number) =>
    request.get(`/instances/${instanceId}/skills`),

  available: (instanceId: number) =>
    request.get(`/instances/${instanceId}/skills/available`),

  install: (instanceId: number, data: { skill_name: string; source: string }) =>
    request.post(`/instances/${instanceId}/skills/install`, data),

  uninstall: (instanceId: number, data: { skill_name: string }) =>
    request.post(`/instances/${instanceId}/skills/uninstall`, data),

  toggle: (instanceId: number, data: { skill_name: string; enabled: boolean }) =>
    request.put(`/instances/${instanceId}/skills/toggle`, data),

  createCustom: (instanceId: number, data: {
    name: string
    display_name: string
    description?: string
    tags?: string[]
    content: string
  }) =>
    request.post(`/instances/${instanceId}/skills/custom`, data),

  updateCustom: (instanceId: number, data: {
    skill_name: string
    display_name?: string
    description?: string
    tags?: string[]
    content?: string
  }) =>
    request.put(`/instances/${instanceId}/skills/custom`, data),

  deleteCustom: (instanceId: number, data: { skill_name: string }) =>
    request.delete(`/instances/${instanceId}/skills/custom`, { data }),
}
