<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../../stores/user'
import { authApi } from '../../api/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const sidebarOpen = ref(false)

const menus = [
  { path: '/admin/dashboard', title: '系统概览', icon: 'DataLine' },
  { path: '/admin/instances', title: '实例管理', icon: 'Monitor' },
  { path: '/admin/users', title: '用户管理', icon: 'User' },
  { path: '/admin/invitations', title: '邀请码', icon: 'Ticket' },
  { path: '/admin/audit', title: '审计日志', icon: 'Document' },
  { path: '/admin/settings', title: '系统设置', icon: 'Setting' },
]

const pageTitle: Record<string, string> = {
  '/admin/dashboard': '系统概览',
  '/admin/instances': '实例管理',
  '/admin/users': '用户管理',
  '/admin/invitations': '邀请码管理',
  '/admin/audit': '审计日志',
  '/admin/settings': '系统设置',
}

async function handleLogout() {
  await authApi.logout()
  userStore.logout()
  router.push('/login')
  ElMessage.success('已退出登录')
}

function onMenuClick() {
  sidebarOpen.value = false
}
</script>

<template>
  <div class="layout">
    <div v-if="sidebarOpen" class="sidebar-overlay" @click="sidebarOpen = false" />

    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-logo">
        <el-icon :size="22"><Setting /></el-icon>
        <span>AgentHub 管理</span>
      </div>
      <nav class="sidebar-nav">
        <router-link
          v-for="m in menus"
          :key="m.path"
          :to="m.path"
          class="nav-item"
          :class="{ active: route.path === m.path }"
          @click="onMenuClick"
        >
          <el-icon :size="18"><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </router-link>
      </nav>
      <div class="sidebar-bottom">
        <div class="user-info">
          <el-avatar :size="32" style="background: #dc2626">
            {{ (userStore.user?.name || 'A')[0] }}
          </el-avatar>
          <span class="user-name">{{ userStore.user?.name || userStore.user?.username }}</span>
        </div>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <button class="hamburger" @click="sidebarOpen = !sidebarOpen">
            <el-icon :size="20"><Fold /></el-icon>
          </button>
          <h1 class="page-title">{{ pageTitle[route.path] || '' }}</h1>
        </div>
        <el-dropdown>
          <span class="user-dropdown">
            <el-avatar :size="28" style="background: #dc2626; font-size: 12px">
              {{ (userStore.user?.name || 'A')[0] }}
            </el-avatar>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleLogout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background: #111827;
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease;
  z-index: 100;
}

.sidebar-logo {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: var(--radius);
  color: #94a3b8;
  text-decoration: none;
  font-size: 14px;
  margin-bottom: 2px;
  transition: all 0.2s;
}

.nav-item:hover {
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.06);
}

.nav-item.active {
  color: #fff;
  background: #dc2626;
}

.sidebar-bottom {
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-name {
  color: #e2e8f0;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.topbar {
  height: var(--header-height);
  min-height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hamburger {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  color: var(--text-secondary);
}

.hamburger:hover {
  background: var(--bg);
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.user-dropdown {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: var(--bg);
}

.sidebar-overlay {
  display: none;
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    width: 260px;
    min-width: 260px;
    transform: translateX(-100%);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 99;
  }

  .hamburger {
    display: flex;
  }

  .content {
    padding: 12px;
  }
}
</style>
