<script setup lang="ts">
defineProps<{
  conversations: any[]
  conversationId: string | null
  sidebarOpen: boolean
  wsConnected: boolean
}>()

const emit = defineEmits<{
  newConversation: []
  loadConversation: [conv: any]
  deleteConversation: [conv: any]
  openSettings: []
  'update:sidebarOpen': [value: boolean]
}>()
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: !sidebarOpen }">
    <div class="sidebar-header">
      <button class="btn-icon" @click="emit('newConversation')" title="新对话">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
      </button>
      <button class="btn-icon toggle-btn" @click="emit('update:sidebarOpen', false)" title="收起">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 17l-5-5 5-5M18 17l-5-5 5-5"/></svg>
      </button>
    </div>

    <div class="conv-list">
      <div
        v-for="conv in conversations" :key="conv.id"
        class="conv-item" :class="{ active: conversationId === conv.uuid }"
        @click="emit('loadConversation', conv)"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="conv-icon"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span class="conv-title">{{ conv.title || '新对话' }}</span>
        <button class="conv-del" @click.stop="emit('deleteConversation', conv)">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </div>
      <div v-if="conversations.length === 0" class="conv-empty">暂无对话历史</div>
    </div>

    <div class="sidebar-footer">
      <button class="sidebar-btn" @click="emit('openSettings')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        设置
      </button>
      <div class="status-indicator" :class="wsConnected ? 'online' : 'offline'">
        <span class="status-dot-inner" />
        {{ wsConnected ? '已连接' : '未连接' }}
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 260px; min-width: 260px;
  background: #fff; display: flex; flex-direction: column;
  border-right: 1px solid #e8eaed;
  transition: all 0.25s ease;
}
.sidebar.collapsed { width: 0; min-width: 0; overflow: hidden; border: none; }

.sidebar-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px; border-bottom: 1px solid #e8eaed;
}

.btn-icon {
  width: 32px; height: 32px; border-radius: 8px; border: none;
  background: transparent; color: #5f6368; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.btn-icon:hover { background: #f1f3f4; color: #1a1a1a; }

.conv-list { flex: 1; overflow-y: auto; padding: 8px; }

.conv-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 8px; cursor: pointer;
  transition: background 0.15s; margin-bottom: 2px;
}
.conv-item:hover { background: #f1f3f4; }
.conv-item.active { background: rgba(99, 102, 241, 0.08); }

.conv-icon { flex-shrink: 0; opacity: 0.4; color: #5f6368; }
.conv-title {
  flex: 1; font-size: 13px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; color: #3c4043;
}
.conv-del {
  opacity: 0; border: none; background: transparent;
  color: #9aa0a6; cursor: pointer; padding: 2px; border-radius: 4px;
}
.conv-del:hover { color: #ef4444; }
.conv-item:hover .conv-del { opacity: 1; }
.conv-empty { text-align: center; color: #9aa0a6; font-size: 13px; padding: 24px 12px; }

.sidebar-footer {
  padding: 12px; border-top: 1px solid #e8eaed;
  display: flex; align-items: center; justify-content: space-between;
}

.sidebar-btn {
  display: flex; align-items: center; gap: 6px;
  border: none; background: transparent; color: #5f6368;
  font-size: 13px; cursor: pointer; padding: 4px 8px; border-radius: 6px;
}
.sidebar-btn:hover { color: #1a1a1a; background: #f1f3f4; }

.status-indicator {
  display: flex; align-items: center; gap: 6px; font-size: 12px; color: #9aa0a6;
}
.status-dot-inner { width: 6px; height: 6px; border-radius: 50%; }
.status-indicator.online .status-dot-inner { background: #22c55e; box-shadow: 0 0 6px rgba(34,197,94,0.4); }
.status-indicator.offline .status-dot-inner { background: #9aa0a6; }

@media (max-width: 640px) {
  .sidebar {
    position: fixed; left: 0; top: 52px; bottom: 0; z-index: 20;
    width: 280px; min-width: 280px;
    box-shadow: 4px 0 16px rgba(0,0,0,0.08);
  }
  .sidebar.collapsed { transform: translateX(-100%); width: 280px; }
}

@media (min-width: 641px) and (max-width: 1024px) {
  .sidebar { width: 220px; min-width: 220px; }
}
</style>
