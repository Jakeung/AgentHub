<script setup lang="ts">
defineProps<{
  phase: string
  errorMsg: string
  progress: number
  progressText: string
}>()

const emit = defineEmits<{
  createAndStart: []
  retry: []
}>()
</script>

<template>
  <!-- Loading -->
  <div v-if="phase === 'loading'" class="phase-center">
    <div class="spinner" />
    <p class="phase-label">加载中...</p>
  </div>

  <!-- No Instance -->
  <div v-else-if="phase === 'no-instance'" class="phase-center">
    <div class="hero-icon">
      <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/>
        <path d="M18 14a6 6 0 0 0-12 0v4a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-4z"/>
        <circle cx="9" cy="16" r="1"/><circle cx="15" cy="16" r="1"/>
      </svg>
    </div>
    <h2 class="hero-title">创建你的 AI Agent</h2>
    <p class="hero-desc">一键部署 Hermes Agent 实例，拥有持久记忆的智能助手</p>
    <button class="btn-primary" @click="emit('createAndStart')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5v14"/></svg>
      创建并启动
    </button>
  </div>

  <!-- Creating / Starting -->
  <div v-else-if="phase === 'creating' || phase === 'starting'" class="phase-center">
    <div class="spinner lg" />
    <h2 class="hero-title">{{ progressText }}</h2>
    <div class="progress-bar-wrap">
      <div class="progress-bar-track">
        <div class="progress-bar-fill" :style="{ width: progress + '%' }" />
      </div>
      <span class="progress-pct">{{ progress }}%</span>
    </div>
    <p class="hero-desc">首次启动可能需要 30-60 秒</p>
  </div>

  <!-- Error -->
  <div v-else-if="phase === 'error'" class="phase-center">
    <div class="hero-icon error">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>
    </div>
    <h2 class="hero-title">启动失败</h2>
    <p class="hero-desc error-text">{{ errorMsg }}</p>
    <button class="btn-primary" @click="emit('retry')">重试</button>
  </div>
</template>

<style scoped>
.phase-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px;
  text-align: center;
}

.spinner {
  width: 32px; height: 32px;
  border: 3px solid #e8eaed;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.spinner.lg { width: 44px; height: 44px; border-width: 4px; }
@keyframes spin { to { transform: rotate(360deg); } }

.phase-label { color: #5f6368; font-size: 14px; margin: 0; }

.hero-icon {
  width: 80px; height: 80px; border-radius: 20px;
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
  display: flex; align-items: center; justify-content: center;
}
.hero-icon.error { background: rgba(239, 68, 68, 0.08); color: #ef4444; }

.hero-title { font-size: 22px; font-weight: 600; margin: 0; color: #1a1a1a; }
.hero-desc { font-size: 14px; color: #5f6368; margin: 0; max-width: 400px; }
.error-text { color: #ef4444; word-break: break-all; }

.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 24px; border-radius: 10px; border: none;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff; font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(99, 102, 241, 0.25); }

.progress-bar-wrap {
  display: flex; align-items: center; gap: 12px; width: 320px; max-width: 80vw;
}
.progress-bar-track {
  flex: 1; height: 6px; border-radius: 3px;
  background: #e8eaed; overflow: hidden;
}
.progress-bar-fill {
  height: 100%; border-radius: 3px;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  transition: width 0.4s ease;
}
.progress-pct { font-size: 13px; color: #5f6368; min-width: 36px; }
</style>
