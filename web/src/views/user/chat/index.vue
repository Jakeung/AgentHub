<template>
  <div class="chat-page">
    <!-- Sidebar: conversation list -->
    <aside class="chat-sidebar">
      <div class="sidebar-header">
        <el-select
          v-model="selectedInstanceId"
          placeholder="选择实例"
          size="small"
          style="width: 100%"
          @change="onInstanceChange"
        >
          <el-option
            v-for="inst in instances"
            :key="inst.id"
            :value="inst.id"
            :label="inst.name"
          >
            <span>{{ inst.name }}</span>
            <el-tag :type="inst.status === 'running' ? 'success' : 'info'" size="small" style="margin-left: 8px">
              {{ inst.status === 'running' ? '运行中' : '已停止' }}
            </el-tag>
          </el-option>
        </el-select>
      </div>
      <div class="sidebar-actions">
        <el-button type="primary" size="small" style="width: 100%" @click="startNewChat" :disabled="!selectedInstanceId">
          + 新对话
        </el-button>
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in conversations"
          :key="conv.uuid"
          class="conv-item"
          :class="{ active: currentConvUuid === conv.uuid }"
          @click="loadConversation(conv)"
        >
          <span class="conv-title">{{ conv.title }}</span>
          <el-button
            type="danger" text size="small" class="conv-delete"
            @click.stop="deleteConversation(conv)"
          >×</el-button>
        </div>
      </div>
    </aside>

    <!-- Main chat area -->
    <main class="chat-main">
      <template v-if="!selectedInstanceId">
        <div class="chat-empty">
          <el-empty description="请先在左侧选择一个实例" />
        </div>
      </template>
      <template v-else>
        <!-- Messages -->
        <div class="messages-container" ref="messagesRef">
          <div v-if="messages.length === 0 && !streaming" class="chat-empty">
            <el-empty description="发送消息开始对话" />
          </div>
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="message-row"
            :class="msg.role"
          >
            <div class="message-avatar">
              {{ msg.role === 'user' ? '👤' : '🤖' }}
            </div>
            <div class="message-content" v-html="renderMarkdown(msg.content)" />
          </div>
          <!-- Streaming indicator -->
          <div v-if="streaming" class="message-row assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
              <span v-html="renderMarkdown(streamingContent)" />
              <span class="typing-cursor">▊</span>
            </div>
          </div>
        </div>

        <!-- Input area -->
        <div class="input-area">
          <el-input
            v-model="inputText"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 5 }"
            placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
            @keydown="handleKeydown"
            :disabled="!wsConnected && !streaming"
          />
          <el-button
            v-if="!streaming"
            type="primary"
            :disabled="!inputText.trim() || !wsConnected"
            @click="sendMessage"
          >发送</el-button>
          <el-button
            v-else
            type="danger"
            @click="stopStreaming"
          >停止</el-button>
        </div>

        <!-- Connection status -->
        <div class="connection-status">
          <span :class="wsConnected ? 'connected' : 'disconnected'">
            {{ wsConnected ? '● 已连接' : '○ 未连接' }}
          </span>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import { instanceApi, type Instance } from '@/api/instance'
import { chatApi, type ConversationItem } from '@/api/chat'

const route = useRoute()

// Markdown renderer
const md = new MarkdownIt({
  html: false,
  linkify: true,
  highlight: (str: string, lang: string) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`
      } catch { /* ignore */ }
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

function renderMarkdown(content: string): string {
  return md.render(content || '')
}

// State
const instances = ref<Instance[]>([])
const selectedInstanceId = ref<number | null>(null)
const conversations = ref<ConversationItem[]>([])
const currentConvUuid = ref<string | null>(null)
const messages = ref<{ role: string; content: string }[]>([])
const inputText = ref('')
const streaming = ref(false)
const streamingContent = ref('')
const wsConnected = ref(false)
const messagesRef = ref<HTMLElement | null>(null)

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 10
const BASE_RECONNECT_DELAY = 1000

// Load instances
async function loadInstances() {
  const res = await instanceApi.list({ page_size: 100 })
  instances.value = res.data.items
  // Auto-select from query param
  const qid = Number(route.query.instance)
  if (qid && instances.value.some((i: Instance) => i.id === qid)) {
    selectedInstanceId.value = qid
  } else if (!selectedInstanceId.value) {
    const running = instances.value.find((i: Instance) => i.status === 'running')
    if (running) selectedInstanceId.value = running.id
    else if (instances.value.length) selectedInstanceId.value = instances.value[0].id
  }
}

// Load conversations
async function loadConversations() {
  if (!selectedInstanceId.value) return
  const res = await chatApi.listConversations({
    instance_id: selectedInstanceId.value,
    page_size: 50,
  })
  conversations.value = res.data.items
}

function onInstanceChange() {
  disconnectWs()
  currentConvUuid.value = null
  messages.value = []
  loadConversations()
  connectWs()
}

function startNewChat() {
  currentConvUuid.value = null
  messages.value = []
  if (!wsConnected.value) connectWs()
}

async function loadConversation(conv: ConversationItem) {
  currentConvUuid.value = conv.uuid
  const res = await chatApi.getMessages(conv.uuid)
  messages.value = res.data.map((m: { role: string; content: string }) => ({
    role: m.role,
    content: m.content,
  }))
  scrollToBottom()
  if (!wsConnected.value) connectWs()
}

async function deleteConversation(conv: ConversationItem) {
  await ElMessageBox.confirm(`删除对话 "${conv.title}"？`, '确认', { type: 'warning' })
  await chatApi.deleteConversation(conv.uuid)
  if (currentConvUuid.value === conv.uuid) {
    currentConvUuid.value = null
    messages.value = []
  }
  loadConversations()
}

// WebSocket
function connectWs() {
  if (!selectedInstanceId.value) return
  disconnectWs()

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${location.host}/ws/chat/${selectedInstanceId.value}`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    wsConnected.value = true
    reconnectAttempts = 0
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    switch (data.type) {
      case 'conversation_id':
        currentConvUuid.value = data.conversation_id
        break
      case 'chunk':
        streamingContent.value += data.content
        scrollToBottom()
        break
      case 'done':
        messages.value.push({ role: 'assistant', content: streamingContent.value })
        streamingContent.value = ''
        streaming.value = false
        loadConversations()
        scrollToBottom()
        break
      case 'error':
        ElMessage.error(data.message)
        streaming.value = false
        streamingContent.value = ''
        break
      case 'pong':
        break
    }
  }

  ws.onclose = () => {
    wsConnected.value = false
    scheduleReconnect()
  }

  ws.onerror = () => {
    wsConnected.value = false
  }
}

function disconnectWs() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  reconnectAttempts = 0
  if (ws) {
    ws.close()
    ws = null
  }
  wsConnected.value = false
}

function scheduleReconnect() {
  if (!selectedInstanceId.value || reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return
  const delay = Math.min(BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts), 30000)
  reconnectAttempts++
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    if (!wsConnected.value && selectedInstanceId.value) {
      connectWs()
    }
  }, delay)
}

function sendMessage() {
  if (!inputText.value.trim() || !ws || ws.readyState !== WebSocket.OPEN) return

  const content = inputText.value.trim()
  messages.value.push({ role: 'user', content })
  inputText.value = ''
  streaming.value = true
  streamingContent.value = ''

  ws.send(JSON.stringify({
    type: 'message',
    content,
    conversation_id: currentConvUuid.value || undefined,
  }))

  scrollToBottom()
}

function stopStreaming() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'stop' }))
  }
  if (streamingContent.value) {
    messages.value.push({ role: 'assistant', content: streamingContent.value })
  }
  streaming.value = false
  streamingContent.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

// Heartbeat
let heartbeatTimer: ReturnType<typeof setInterval> | null = null

function startHeartbeat() {
  heartbeatTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }))
    }
  }, 30000)
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

watch(wsConnected, (connected) => {
  if (connected) startHeartbeat()
  else stopHeartbeat()
})

onMounted(async () => {
  await loadInstances()
  if (selectedInstanceId.value) {
    await loadConversations()
    connectWs()
  }
})

onUnmounted(() => {
  disconnectWs()
  stopHeartbeat()
})
</script>

<style scoped>
.chat-page {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.chat-sidebar {
  width: 260px;
  min-width: 260px;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
}

.sidebar-header {
  padding: 12px;
  border-bottom: 1px solid var(--border);
}

.sidebar-actions {
  padding: 8px 12px;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.conv-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}

.conv-item:hover {
  background: rgba(79, 70, 229, 0.06);
}

.conv-item.active {
  background: rgba(79, 70, 229, 0.08);
  border-left: 3px solid var(--primary);
}

.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: var(--text);
}

.conv-delete {
  opacity: 0;
  transition: opacity 0.2s;
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.message-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.message-row.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  background: var(--bg);
}

.message-row.user .message-avatar {
  background: rgba(79, 70, 229, 0.1);
}

.message-content {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.message-row.user .message-content {
  background: var(--primary);
  color: #fff;
  border-top-right-radius: 2px;
}

.message-row.assistant .message-content {
  background: var(--bg);
  color: var(--text);
  border-top-left-radius: 2px;
}

.message-content :deep(pre.hljs) {
  border-radius: var(--radius);
  padding: 12px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-content :deep(code) {
  font-family: 'Fira Code', monospace;
  font-size: 13px;
}

.message-content :deep(p) {
  margin: 4px 0;
}

.typing-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.input-area {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  background: var(--bg-card);
}

.input-area .el-textarea {
  flex: 1;
}

.connection-status {
  padding: 4px 20px;
  font-size: 12px;
  text-align: right;
}

.connected {
  color: #22c55e;
}

.disconnected {
  color: var(--text-muted);
}

@media (max-width: 768px) {
  .chat-sidebar {
    display: none;
  }

  .messages-container {
    padding: 12px;
  }

  .message-content {
    max-width: 85%;
  }

  .input-area {
    padding: 8px 12px;
  }
}
</style>
