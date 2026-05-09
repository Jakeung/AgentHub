import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'

interface UserInfo {
  id: number
  username: string
  name: string
  role: string
}

export const useUserStore = defineStore('user', () => {
  const user = ref<UserInfo | null>(null)
  const permissions = ref<string[]>([])

  const isLoggedIn = computed(() => !!user.value)
  const role = computed(() => user.value?.role ?? '')
  const isAdmin = computed(() => role.value === 'admin')

  function hasPermission(code: string): boolean {
    return permissions.value.includes(code)
  }

  async function fetchMe() {
    const res = await authApi.me()
    if (res.code === 0) {
      user.value = {
        id: res.data.id,
        username: res.data.username,
        name: res.data.name,
        role: res.data.role,
      }
      permissions.value = res.data.permissions
    }
  }

  function setLogin(userData: UserInfo, perms: string[]) {
    user.value = userData
    permissions.value = perms
  }

  function logout() {
    user.value = null
    permissions.value = []
  }

  return { user, permissions, isLoggedIn, role, isAdmin, hasPermission, fetchMe, setLogin, logout }
})
