<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'
import { authApi } from '../../api/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

async function handleLogout() {
  await authApi.logout()
  userStore.logout()
  router.push('/login')
  ElMessage.success('已退出登录')
}
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <div class="topbar-left">
        <div class="logo-mark">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 1 3 3v1a3 3 0 0 1-1.1 2.3"/><path d="M6 7a3 3 0 0 0-3 3v1a3 3 0 0 0 1.1 2.3"/><circle cx="12" cy="17" r="5"/><circle cx="10" cy="16" r="1" fill="currentColor"/><circle cx="14" cy="16" r="1" fill="currentColor"/><path d="M10 19c.8.6 2.4.6 3.2 0"/></svg>
        </div>
        <span class="app-title">AgentHub</span>
      </div>
      <div class="topbar-right">
        <el-dropdown trigger="click">
          <div class="user-pill">
            <div class="user-avatar">
              {{ (userStore.user?.name || userStore.user?.username || 'U')[0].toUpperCase() }}
            </div>
            <span class="user-name">{{ userStore.user?.name || userStore.user?.username }}</span>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleLogout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: #f8f9fa;
}

.topbar {
  height: 52px;
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid #e8eaed;
  z-index: 10;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.app-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  letter-spacing: -0.01em;
}

.topbar-right {
  display: flex;
  align-items: center;
}

.user-pill {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 4px;
  border-radius: 20px;
  transition: background 0.15s;
  color: #5f6368;
}

.user-pill:hover {
  background: #f1f3f4;
}

.user-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-name {
  font-size: 13px;
  color: #3c4043;
}

.content {
  flex: 1;
  overflow: hidden;
  display: flex;
}

@media (max-width: 768px) {
  .topbar {
    padding: 0 12px;
  }
  .user-name {
    display: none;
  }
}
</style>
