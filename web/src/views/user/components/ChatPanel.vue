<script setup lang="ts">
import { computed, ref, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const props = defineProps<{
  messages: { role: string; content: string }[]
  sending: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const inputText = ref('')
const messagesEl = ref<HTMLElement>()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  highlight(str: string, lang: string) {
    if (lang && hljs.getLanguage(lang)) {
      try { return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>` } catch {}
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

const renderedMessages = computed(() =>
  props.messages.map(m => ({
    ...m,
    html: m.role === 'assistant' ? md.render(m.content || '') : '',
  }))
)

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
}

function sendMessage() {
  if (!inputText.value.trim() || props.sending) return
  emit('send', inputText.value.trim())
  inputText.value = ''
}

function scrollToBottom() {
  nextTick(() => { if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight })
}

defineExpose({ scrollToBottom })
</script>

<template>
  <div class="chat-main">
    <!-- Empty state -->
    <div v-if="messages.length === 0" class="chat-empty">
      <div class="empty-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.4"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </div>
      <p class="empty-text">向 Hermes Agent 发送消息</p>
      <p class="empty-hint">Agent 拥有持久记忆，可跨对话记住上下文</p>
    </div>

    <!-- Messages -->
    <div v-else ref="messagesEl" class="messages">
      <div v-for="(msg, i) in renderedMessages" :key="i" class="msg-row" :class="msg.role">
        <div v-if="msg.role === 'assistant'" class="msg-avatar assistant">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 1 3 3v1a3 3 0 0 1-1.1 2.3"/><path d="M6 7a3 3 0 0 0-3 3v1a3 3 0 0 0 1.1 2.3"/><circle cx="12" cy="17" r="5"/><circle cx="10" cy="16" r="1" fill="currentColor"/><circle cx="14" cy="16" r="1" fill="currentColor"/><path d="M10 19c.8.6 2.4.6 3.2 0"/></svg>
        </div>
        <div class="msg-body">
          <div v-if="msg.role === 'user'" class="msg-content user-text">{{ msg.content }}</div>
          <div v-else class="msg-content md-body" v-html="msg.html || '<span class=typing>●●●</span>'" />
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="input-area">
      <div class="input-wrap">
        <textarea
          v-model="inputText"
          class="chat-input"
          placeholder="发送消息..."
          rows="1"
          @keydown="handleKeydown"
          :disabled="sending"
        />
        <button class="send-btn" :disabled="!inputText.trim() || sending" @click="sendMessage">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/></svg>
        </button>
      </div>
      <p class="input-hint">Enter 发送 · Shift + Enter 换行</p>
    </div>
  </div>
</template>

<style scoped>
.chat-main {
  flex: 1; display: flex; flex-direction: column; min-width: 0;
  background: #f8f9fa;
}

.chat-empty {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px;
}
.empty-text { color: #9aa0a6; font-size: 15px; margin: 0; }
.empty-hint { color: #bdc1c6; font-size: 13px; margin: 0; }

.messages { flex: 1; overflow-y: auto; padding: 24px 0; }

.msg-row {
  display: flex; gap: 16px; padding: 16px 24px;
  max-width: 800px; margin: 0 auto; width: 100%;
}
.msg-row.user { justify-content: flex-end; }

.msg-avatar {
  width: 32px; height: 32px; border-radius: 8px;
  font-size: 13px; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.msg-avatar.assistant {
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff;
}

.msg-body { flex: 1; min-width: 0; }
.msg-row.user .msg-body { flex: none; max-width: 75%; }
.msg-content { font-size: 14px; line-height: 1.7; }
.user-text {
  color: #fff; white-space: pre-wrap;
  background: linear-gradient(135deg, #6366f1, #818cf8);
  padding: 10px 16px; border-radius: 16px 16px 4px 16px;
  display: inline-block;
}

/* Markdown */
.md-body { color: #3c4043; }
.md-body :deep(p) { margin: 6px 0; }
.md-body :deep(pre.hljs) {
  border-radius: 8px; padding: 14px; margin: 10px 0;
  background: #1e1e1e; overflow-x: auto;
  border: 1px solid #e8eaed;
}
.md-body :deep(code) { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px; }
.md-body :deep(p code) {
  background: #f1f3f4; padding: 2px 6px; border-radius: 4px; color: #d63384;
}
.md-body :deep(ul), .md-body :deep(ol) { padding-left: 20px; }
.md-body :deep(blockquote) {
  border-left: 3px solid #6366f1; padding-left: 12px; margin: 8px 0; color: #5f6368;
}
.md-body :deep(a) { color: #6366f1; }
.md-body :deep(table) { border-collapse: collapse; margin: 8px 0; width: 100%; }
.md-body :deep(th), .md-body :deep(td) {
  border: 1px solid #e8eaed; padding: 6px 10px; text-align: left;
}
.md-body :deep(th) { background: #f1f3f4; }

.typing {
  display: inline-block;
  animation: pulse 1.4s infinite;
  color: #6366f1;
}
@keyframes pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

.input-area {
  padding: 12px 24px 16px;
  max-width: 800px; margin: 0 auto; width: 100%;
}

.input-wrap {
  display: flex; align-items: flex-end; gap: 8px;
  background: #fff; border-radius: 12px;
  border: 1px solid #dadce0;
  padding: 8px 8px 8px 16px;
  transition: border-color 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.input-wrap:focus-within { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,0.12); }

.chat-input {
  flex: 1; border: none; background: transparent;
  color: #1a1a1a; font-size: 14px; line-height: 1.5;
  resize: none; outline: none; font-family: inherit;
  max-height: 120px;
}
.chat-input::placeholder { color: #9aa0a6; }

.send-btn {
  width: 36px; height: 36px; border-radius: 8px; border: none;
  background: #6366f1; color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s; flex-shrink: 0;
}
.send-btn:hover:not(:disabled) { background: #818cf8; }
.send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.input-hint {
  text-align: center; font-size: 11px; color: #9aa0a6; margin: 6px 0 0;
}

@media (max-width: 640px) {
  .msg-row { padding: 12px 16px; }
  .input-area { padding: 8px 12px 12px; }
}

@media (min-width: 1025px) {
  .msg-row { max-width: 800px; }
}
</style>
