<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { instanceApi, type Instance } from '../../api/instance'
import { chatApi } from '../../api/chat'
import PhaseScreens from './components/PhaseScreens.vue'
import ConversationSidebar from './components/ConversationSidebar.vue'
import ChatPanel from './components/ChatPanel.vue'
import SettingsDrawer from './components/SettingsDrawer.vue'

// --- Phase state machine ---
type Phase = 'loading' | 'no-instance' | 'creating' | 'starting' | 'ready' | 'error'
const phase = ref<Phase>('loading')
const instance = ref<Instance | null>(null)
const errorMsg = ref('')
const progress = ref(0)
const progressText = ref('')

// --- Chat state ---
const messages = ref<{ role: string; content: string }[]>([])
const sending = ref(false)
const conversationId = ref<string | null>(null)
const conversations = ref<any[]>([])
const wsConnected = ref(false)
const sidebarOpen = ref(false)
const showSettings = ref(false)
let ws: WebSocket | null = null
let streamingContent = ''
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null
let wsReconnectAttempts = 0
const WS_MAX_RECONNECT_ATTEMPTS = 5
const WS_BASE_DELAY = 1000

const chatPanelRef = ref<InstanceType<typeof ChatPanel>>()
const settingsRef = ref<InstanceType<typeof SettingsDrawer>>()

// --- Lifecycle ---
onMounted(async () => { await checkInstance() })
onUnmounted(() => { disconnectWs() })

// --- Instance management ---
async function checkInstance() {
  phase.value = 'loading'
  try {
    const res = await instanceApi.list({ page: 1, page_size: 1 })
    if (res.code !== 0) throw new Error(res.message)
    const items = res.data.items
    if (items.length === 0) { phase.value = 'no-instance'; return }
    instance.value = items[0]
    if (instance.value!.status === 'running') {
      phase.value = 'ready'
      await loadConversations()
      if (conversations.value.length > 0 && !conversationId.value) {
        await loadConversation(conversations.value[0])
      }
      connectWs()
    } else if (['stopped', 'error'].includes(instance.value!.status)) {
      await startInstance()
    } else {
      phase.value = 'starting'
      pollStatus()
    }
  } catch (e: any) {
    phase.value = 'error'
    errorMsg.value = e?.message || '加载失败'
  }
}

async function createAndStart() {
  phase.value = 'creating'
  progress.value = 10
  progressText.value = '正在创建实例...'
  try {
    const res = await instanceApi.create({ name: 'hermes' })
    if (res.code !== 0) throw new Error(res.message)
    instance.value = res.data
    progress.value = 40
    progressText.value = '实例已创建，正在启动...'
    await startInstance()
  } catch (e: any) {
    phase.value = 'error'
    errorMsg.value = e?.message || '创建失败'
  }
}

async function startInstance() {
  phase.value = 'starting'
  progress.value = 50
  progressText.value = '正在启动 Hermes Agent...'
  try {
    const res = await instanceApi.start(instance.value!.id)
    if (res.code !== 0) throw new Error(res.message)
    progress.value = 60
    progressText.value = '等待服务就绪...'
    await pollReady()
  } catch (e: any) {
    phase.value = 'error'
    errorMsg.value = e?.message || '启动失败'
  }
}

function pollStatus() {
  pollReady()
}

async function pollReady() {
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 2000))
    try {
      const res = await instanceApi.list({ page: 1, page_size: 1 })
      if (res.code === 0 && res.data.items.length > 0) {
        instance.value = res.data.items[0]
        if (instance.value!.status === 'running') {
          progress.value = 100
          progressText.value = '就绪!'
          await new Promise(r => setTimeout(r, 400))
          phase.value = 'ready'
          await loadConversations()
          if (conversations.value.length > 0 && !conversationId.value) {
            await loadConversation(conversations.value[0])
          }
          connectWs()
          return
        }
        if (instance.value!.status === 'error') {
          phase.value = 'error'
          errorMsg.value = instance.value!.health_status || '启动失败'
          return
        }
      }
    } catch {}
    progress.value = Math.min(95, 60 + i * 2)
  }
  phase.value = 'error'
  errorMsg.value = '启动超时，请重试'
}

// --- WebSocket ---
function connectWs() {
  if (!instance.value) return
  cancelWsReconnect()
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws/chat/${instance.value.id}`)
  ws.onopen = () => { wsConnected.value = true; wsReconnectAttempts = 0 }
  ws.onclose = (event) => {
    wsConnected.value = false
    if (!event.wasClean && phase.value === 'ready') scheduleWsReconnect()
  }
  ws.onerror = () => { wsConnected.value = false }
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'conversation_id') {
        conversationId.value = data.conversation_id
      } else if (data.type === 'chunk') {
        streamingContent += data.content
        if (messages.value.length && messages.value[messages.value.length - 1].role === 'assistant') {
          messages.value[messages.value.length - 1].content = streamingContent
        }
        chatPanelRef.value?.scrollToBottom()
      } else if (data.type === 'done') {
        sending.value = false
        loadConversations()
      } else if (data.type === 'error') {
        ElMessage.error(data.message || 'Agent 错误')
        sending.value = false
      }
    } catch { /* JSON parse error in WS message, ignore malformed frames */ }
  }
}

function disconnectWs() { cancelWsReconnect(); ws?.close(); ws = null }

function cancelWsReconnect() {
  if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null }
}

function scheduleWsReconnect() {
  if (wsReconnectAttempts >= WS_MAX_RECONNECT_ATTEMPTS) {
    ElMessage.warning('WebSocket 连接断开，请刷新页面重试')
    return
  }
  const delay = WS_BASE_DELAY * Math.pow(2, wsReconnectAttempts)
  wsReconnectAttempts++
  wsReconnectTimer = setTimeout(() => { connectWs() }, delay)
}

function sendMessage(text: string) {
  if (!text || sending.value || !ws) return
  sending.value = true
  streamingContent = ''
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '' })
  chatPanelRef.value?.scrollToBottom()
  const model = settingsRef.value?.selectedModel || undefined
  ws.send(JSON.stringify({ type: 'message', content: text, conversation_id: conversationId.value, model }))
}

// --- Conversations ---
async function loadConversations() {
  if (!instance.value) return
  try {
    const res = await chatApi.listConversations({ instance_id: instance.value.id })
    if (res.code === 0) conversations.value = res.data.items
  } catch { ElMessage.error('加载对话列表失败') }
}

async function loadConversation(conv: any) {
  conversationId.value = conv.uuid
  try {
    const res = await chatApi.getMessages(conv.uuid)
    if (res.code === 0) {
      messages.value = res.data.map((m: any) => ({ role: m.role, content: m.content }))
      chatPanelRef.value?.scrollToBottom()
    }
  } catch { ElMessage.error('加载对话消息失败') }
}

function newConversation() { conversationId.value = null; messages.value = [] }

async function deleteConversation(conv: any) {
  try {
    await chatApi.deleteConversation(conv.uuid)
    if (conversationId.value === conv.uuid) newConversation()
    await loadConversations()
  } catch { ElMessage.error('删除对话失败') }
}

// --- Instance actions ---
async function handleStop() {
  try {
    const res = await instanceApi.stop(instance.value!.id)
    if (res.code === 0) { ElMessage.success('已停止'); disconnectWs(); instance.value!.status = 'stopped' }
    else ElMessage.error(res.message || '停止失败')
  } catch (e: any) { ElMessage.error(e?.message || '停止失败') }
}

async function handleRestart() {
  try {
    const res = await instanceApi.restart(instance.value!.id)
    if (res.code === 0) {
      ElMessage.success('重启中...')
      instance.value!.status = 'running'
      disconnectWs()
      setTimeout(() => connectWs(), 3000)
    } else ElMessage.error(res.message || '重启失败')
  } catch (e: any) { ElMessage.error(e?.message || '重启失败') }
}

async function handleSettingsStart() {
  showSettings.value = false
  await startInstance()
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm('删除实例将清除所有对话历史，确定继续？', '确认删除', { type: 'warning' })
  } catch { return }
  if (instance.value!.status === 'running') {
    try { await instanceApi.stop(instance.value!.id) } catch {}
  }
  try {
    const res = await instanceApi.delete(instance.value!.id)
    if (res.code === 0) {
      ElMessage.success('实例已删除')
      disconnectWs()
      instance.value = null
      conversations.value = []
      messages.value = []
      showSettings.value = false
      phase.value = 'no-instance'
    } else ElMessage.error(res.message || '删除失败')
  } catch (e: any) { ElMessage.error(e?.message || '删除失败') }
}
</script>

<template>
  <div class="user-page">
    <!-- Phase screens: loading, no-instance, creating, starting, error -->
    <PhaseScreens
      v-if="phase !== 'ready'"
      :phase="phase"
      :error-msg="errorMsg"
      :progress="progress"
      :progress-text="progressText"
      @create-and-start="createAndStart"
      @retry="checkInstance"
    />

    <!-- Ready: Chat UI -->
    <template v-else>
      <ConversationSidebar
        :conversations="conversations"
        :conversation-id="conversationId"
        v-model:sidebar-open="sidebarOpen"
        :ws-connected="wsConnected"
        @new-conversation="newConversation"
        @load-conversation="loadConversation"
        @delete-conversation="deleteConversation"
        @open-settings="showSettings = true"
      />

      <!-- Sidebar collapsed toggle -->
      <button v-if="!sidebarOpen" class="sidebar-expand" @click="sidebarOpen = true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 17l5-5-5-5M6 17l5-5-5-5"/></svg>
      </button>

      <ChatPanel
        ref="chatPanelRef"
        :messages="messages"
        :sending="sending"
        @send="sendMessage"
      />
    </template>

    <SettingsDrawer
      ref="settingsRef"
      v-model="showSettings"
      :instance="instance"
      @stop="handleStop"
      @restart="handleRestart"
      @start="handleSettingsStart"
      @delete="handleDelete"
    />
  </div>
</template>

<style scoped>
.user-page {
  flex: 1;
  display: flex;
  overflow: hidden;
  background: #f8f9fa;
  color: #1a1a1a;
}

.sidebar-expand {
  position: absolute; left: 4px; top: 50%; transform: translateY(-50%);
  z-index: 5; width: 28px; height: 56px; border-radius: 0 8px 8px 0;
  border: 1px solid #e8eaed; border-left: none;
  background: #fff; color: #5f6368; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.sidebar-expand:hover { color: #1a1a1a; background: #f1f3f4; }
</style>
