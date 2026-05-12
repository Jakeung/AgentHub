<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { instanceApi, type Instance } from '../../../api/instance'
import { secretApi } from '../../../api/secret'
import { channelApi } from '../../../api/channel'
import { toolsApi, type ToolItem, type ToolUpdateItem } from '../../../api/tools'
import { skillsApi, type InstalledSkill, type SkillCategory } from '../../../api/skills'
import request from '../../../api/request'

const props = defineProps<{
  modelValue: boolean
  instance: Instance | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  stop: []
  restart: []
  start: []
  delete: []
}>()

// --- Secrets ---
const secrets = ref<any[]>([])
const secretForm = ref({ name: '', provider: 'deepseek', model_name: '', api_key: '' })
const secretLoading = ref(false)
const showAddModel = ref(false)
const defaultModel = ref({ provider: '', model: '' })
const selectedModel = ref('')
const hasActiveSecret = computed(() => secrets.value.some((s: any) => s.is_active))
const dynamicModels = ref<string[]>([])
const availableModels = computed(() => dynamicModels.value)
const modelSwitchProgress = ref(false)

function isSystemModel(_model: string) {
  return !hasActiveSecret.value
}

async function loadAvailableModels() {
  try {
    const res: any = await secretApi.availableModels()
    if (res.code === 0 && Array.isArray(res.data)) {
      dynamicModels.value = res.data
      if (res.data.length > 0 && (!selectedModel.value || !res.data.includes(selectedModel.value))) {
        selectedModel.value = res.data[0]
      }
    }
  } catch { ElMessage.error('加载模型列表失败') }
}

async function loadSecrets() {
  try {
    const res = await secretApi.list()
    if (res.code === 0) secrets.value = res.data.items
  } catch { ElMessage.error('加载密钥列表失败') }
}

async function loadDefaultModel() {
  try {
    const res: any = await request.get('/settings/default-model')
    if (res.code === 0) {
      defaultModel.value = res.data
      if (!selectedModel.value) selectedModel.value = res.data.model || ''
    }
  } catch { ElMessage.error('加载默认模型失败') }
}

async function createSecret() {
  if (!secretForm.value.name || !secretForm.value.api_key) { ElMessage.warning('请填写名称和密钥'); return }
  try {
    await ElMessageBox.confirm(
      '添加模型将自动重启 Agent 实例，过程可能需要 10-30 秒，期间无法使用聊天功能。',
      '确认添加',
      { confirmButtonText: '确认添加', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }

  secretLoading.value = true
  try {
    const res = await secretApi.create(secretForm.value)
    if (res.code === 0) {
      ElMessage.success('模型已添加，正在重启 Agent...')
      secretForm.value = { name: '', provider: 'deepseek', model_name: '', api_key: '' }
      showAddModel.value = false
      await loadSecrets()
      const newItem = secrets.value[0]
      if (newItem) {
        modelSwitchProgress.value = true
        await activateSecret(newItem.id)
        await waitForRestart()
        modelSwitchProgress.value = false
      }
    } else ElMessage.error(res.message || '保存失败')
  } finally { secretLoading.value = false }
}

async function waitForRestart() {
  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 3000))
    try {
      const res: any = await instanceApi.list({ page: 1, page_size: 1 })
      if (res.code === 0 && res.data?.items?.[0]?.status === 'running') {
        ElMessage.success('Agent 已重启完成')
        return
      }
    } catch {}
  }
  ElMessage.warning('重启超时，请手动检查')
}

async function activateSecret(id: number) {
  try {
    const res = await secretApi.activate(id)
    if (res.code === 0) { await loadSecrets(); await loadAvailableModels(); ElMessage.success('已切换模型') }
  } catch { ElMessage.error('切换模型失败') }
}

async function deleteSecret(id: number) {
  await ElMessageBox.confirm('确定删除该密钥?', '确认')
  try { await secretApi.delete(id); await loadSecrets(); ElMessage.success('已删除') } catch { ElMessage.error('删除密钥失败') }
}

// --- Channels ---
const channels = ref<any[]>([])
const platformSchemas = ref<Record<string, any>>({})
const showAddChannel = ref(false)
const channelLoading = ref(false)
const channelForm = ref<{ platform: string; config: Record<string, string> }>({ platform: '', config: {} })

const channelEmojis: Record<string, string> = {
  telegram: '✈️', discord: '🎮', slack: '💬', weixin: '💚', wecom: '🏢',
  feishu: '🐦', dingtalk: '🔔', qqbot: '🐧',
}
function channelEmoji(platform: string) { return channelEmojis[platform] || '📡' }

async function loadChannels() {
  try {
    const res: any = await channelApi.list()
    if (res.code === 0) channels.value = res.data
  } catch { ElMessage.error('加载渠道列表失败') }
}

async function loadPlatforms() {
  if (Object.keys(platformSchemas.value).length > 0) return
  try {
    const res: any = await channelApi.platforms()
    if (res.code === 0) platformSchemas.value = res.data
  } catch { ElMessage.error('加载平台列表失败') }
}

function onChannelPlatformChange() {
  channelForm.value.config = {}
}

async function createChannel() {
  if (!channelForm.value.platform) { ElMessage.warning('请选择平台'); return }
  channelLoading.value = true
  try {
    const res: any = await channelApi.create({
      platform: channelForm.value.platform,
      config: channelForm.value.config,
    })
    if (res.code === 0) {
      ElMessage.success('渠道已绑定，Agent 重启中...')
      showAddChannel.value = false
      channelForm.value = { platform: '', config: {} }
      await loadChannels()
    } else {
      ElMessage.error(res.message || '绑定失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '绑定失败')
  } finally {
    channelLoading.value = false
  }
}

async function deleteChannel(id: number) {
  try {
    await ElMessageBox.confirm('确定解除该渠道绑定？Agent 将重启', '确认')
  } catch { return }
  try {
    const res: any = await channelApi.delete(id)
    if (res.code === 0) { ElMessage.success('已解绑'); await loadChannels() }
    else ElMessage.error(res.message || '解绑失败')
  } catch { ElMessage.error('解绑渠道失败') }
}

// --- WeChat QR ---
import QRCode from 'qrcode'

const weixinQrUrl = ref('')
const weixinQrLoading = ref(false)
const weixinQrStatus = ref('')
const weixinQrError = ref(false)
let weixinPollTimer: any = null

async function startWeixinQr() {
  weixinQrLoading.value = true
  weixinQrStatus.value = ''
  weixinQrError.value = false
  try {
    const res: any = await channelApi.weixinQrStart()
    if (res.code === 0) {
      const qrContent = res.data.qr_url || ''
      if (!qrContent) {
        ElMessage.error('获取二维码失败: 返回数据为空')
        return
      }
      if (qrContent.startsWith('data:')) {
        weixinQrUrl.value = qrContent
      } else {
        weixinQrUrl.value = await QRCode.toDataURL(qrContent, { width: 200, margin: 2 })
      }
      pollWeixinStatus()
    } else {
      ElMessage.error(res.message || '获取二维码失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '获取二维码失败')
  } finally {
    weixinQrLoading.value = false
  }
}

function pollWeixinStatus() {
  if (weixinPollTimer) clearInterval(weixinPollTimer)
  weixinPollTimer = setInterval(async () => {
    try {
      const res: any = await channelApi.weixinQrStatus()
      if (res.code === 0) {
        const s = res.data.status
        weixinQrStatus.value = s
        if (s === 'confirmed') {
          clearInterval(weixinPollTimer)
          weixinPollTimer = null
          ElMessage.success('微信绑定成功！Agent 重启中...')
          showAddChannel.value = false
          weixinQrUrl.value = ''
          await loadChannels()
        } else if (s === 'expired' || s === 'error') {
          clearInterval(weixinPollTimer)
          weixinPollTimer = null
          weixinQrUrl.value = ''
          ElMessage.warning('二维码已过期，请重新获取')
        }
      }
    } catch {}
  }, 2000)
}

function cancelWeixinQr() {
  if (weixinPollTimer) { clearInterval(weixinPollTimer); weixinPollTimer = null }
  weixinQrUrl.value = ''
  weixinQrStatus.value = ''
}

// --- Active Tab ---
const activeTab = ref('basic')

// --- Tools ---
const toolsList = ref<ToolItem[]>([])
const toolsLoading = ref(false)
const toolsSaving = ref(false)
const toolsModified = ref(false)
const toolConfigs = ref<Record<string, Record<string, string>>>({})

async function loadTools() {
  if (!props.instance) return
  toolsLoading.value = true
  try {
    const res: any = await toolsApi.list(props.instance.id)
    if (res.code === 0) {
      toolsList.value = res.data
      toolConfigs.value = {}
      for (const t of res.data) {
        if (t.config && Object.keys(t.config).length > 0) {
          toolConfigs.value[t.name] = { ...t.config }
        }
      }
      toolsModified.value = false
    }
  } catch { ElMessage.error('加载工具列表失败') }
  finally { toolsLoading.value = false }
}

function onToolToggle() {
  toolsModified.value = true
}

function onToolConfigInput(toolName: string, key: string, value: string) {
  if (!toolConfigs.value[toolName]) toolConfigs.value[toolName] = {}
  toolConfigs.value[toolName][key] = value
  toolsModified.value = true
}

async function saveTools() {
  if (!props.instance) return
  toolsSaving.value = true
  try {
    const updates: ToolUpdateItem[] = toolsList.value.map(t => ({
      tool_name: t.name,
      enabled: t.enabled,
      config: toolConfigs.value[t.name] || t.config || {},
    }))
    const res: any = await toolsApi.update(props.instance.id, updates)
    if (res.code === 0) {
      ElMessage.success('工具配置已保存，实例重启中...')
      toolsModified.value = false
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch { ElMessage.error('保存工具配置失败') }
  finally { toolsSaving.value = false }
}

// --- Skills ---
const installedSkills = ref<InstalledSkill[]>([])
const skillsStats = ref({ total_installed: 0, enabled: 0, disabled: 0, custom: 0 })
const skillsLoading = ref(false)
const availableCategories = ref<SkillCategory[]>([])
const availableTotal = ref(0)
const showAvailable = ref(false)
const availableLoading = ref(false)
const showCustomForm = ref(false)
const customSkillForm = ref({ name: '', display_name: '', description: '', tags: '', content: '' })
const customSaving = ref(false)

async function loadSkills() {
  if (!props.instance) return
  skillsLoading.value = true
  try {
    const res: any = await skillsApi.list(props.instance.id)
    if (res.code === 0) {
      installedSkills.value = res.data.installed
      skillsStats.value = res.data.stats
    }
  } catch { ElMessage.error('加载技能列表失败') }
  finally { skillsLoading.value = false }
}

async function loadAvailableSkills() {
  if (!props.instance) return
  availableLoading.value = true
  showAvailable.value = true
  try {
    const res: any = await skillsApi.available(props.instance.id)
    if (res.code === 0) {
      availableCategories.value = res.data.categories
      availableTotal.value = res.data.total_available
    }
  } catch { ElMessage.error('加载可用技能列表失败（需要实例处于运行状态）') }
  finally { availableLoading.value = false }
}

async function installSkill(skillName: string, source: string) {
  if (!props.instance) return
  try {
    const res: any = await skillsApi.install(props.instance.id, { skill_name: skillName, source })
    if (res.code === 0) {
      ElMessage.success('技能已安装')
      await loadSkills()
      await loadAvailableSkills()
    } else ElMessage.error(res.message || '安装失败')
  } catch { ElMessage.error('安装技能失败') }
}

async function uninstallSkill(skillName: string) {
  try {
    await ElMessageBox.confirm(`确定卸载技能 ${skillName}？`, '确认')
  } catch { return }
  if (!props.instance) return
  try {
    const res: any = await skillsApi.uninstall(props.instance.id, { skill_name: skillName })
    if (res.code === 0) { ElMessage.success('已卸载'); await loadSkills() }
    else ElMessage.error(res.message || '卸载失败')
  } catch { ElMessage.error('卸载失败') }
}

async function toggleSkill(skill: InstalledSkill) {
  if (!props.instance) return
  const newEnabled = !skill.enabled
  try {
    const res: any = await skillsApi.toggle(props.instance.id, { skill_name: skill.name, enabled: newEnabled })
    if (res.code === 0) {
      skill.enabled = newEnabled
      ElMessage.success(newEnabled ? '已启用' : '已禁用')
    } else ElMessage.error(res.message || '操作失败')
  } catch { ElMessage.error('操作失败') }
}

async function createCustomSkill() {
  if (!props.instance) return
  if (!customSkillForm.value.name || !customSkillForm.value.display_name || !customSkillForm.value.content) {
    ElMessage.warning('请填写名称、显示名和内容')
    return
  }
  customSaving.value = true
  try {
    const tags = customSkillForm.value.tags ? customSkillForm.value.tags.split(',').map(t => t.trim()).filter(Boolean) : []
    const res: any = await skillsApi.createCustom(props.instance.id, {
      name: customSkillForm.value.name,
      display_name: customSkillForm.value.display_name,
      description: customSkillForm.value.description,
      tags,
      content: customSkillForm.value.content,
    })
    if (res.code === 0) {
      ElMessage.success('自定义技能已创建')
      showCustomForm.value = false
      customSkillForm.value = { name: '', display_name: '', description: '', tags: '', content: '' }
      await loadSkills()
    } else ElMessage.error(res.message || '创建失败')
  } catch { ElMessage.error('创建失败') }
  finally { customSaving.value = false }
}

async function deleteCustomSkill(skillName: string) {
  try {
    await ElMessageBox.confirm(`确定删除自定义技能 ${skillName}？`, '确认')
  } catch { return }
  if (!props.instance) return
  try {
    const res: any = await skillsApi.deleteCustom(props.instance.id, { skill_name: skillName })
    if (res.code === 0) { ElMessage.success('已删除'); await loadSkills() }
    else ElMessage.error(res.message || '删除失败')
  } catch { ElMessage.error('删除失败') }
}

function onOpen() {
  activeTab.value = 'basic'
  loadSecrets()
  loadDefaultModel()
  loadAvailableModels()
  loadChannels()
}

defineExpose({ selectedModel, onOpen })
</script>

<template>
  <el-drawer :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)"
    title="设置" size="400px" direction="rtl" :modal-class="'settings-modal'" :z-index="2000"
    @open="onOpen">

    <!-- Instance card -->
    <div class="settings-block">
      <h4>Agent 实例</h4>
      <div v-if="instance" class="instance-card">
        <div class="instance-card-header">
          <div class="instance-card-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/><path d="M18 14a6 6 0 0 0-12 0v4a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-4z"/></svg>
          </div>
          <div class="instance-card-info">
            <span class="instance-card-name">{{ instance.name }}</span>
            <span class="status-badge" :class="instance.status">
              <span class="status-dot-sm" />
              {{ instance.status === 'running' ? '运行中' : instance.status === 'stopped' ? '已停止' : instance.status }}
            </span>
          </div>
        </div>
        <div class="instance-card-actions">
          <button v-if="instance.status === 'running'" class="action-btn warning" @click="emit('stop')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
            停止
          </button>
          <button v-if="instance.status === 'running'" class="action-btn info" @click="emit('restart')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
            重启
          </button>
          <button v-if="['stopped','error'].includes(instance.status)" class="action-btn success" @click="emit('start')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            启动
          </button>
          <button class="action-btn danger" @click="emit('delete')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6h14"/></svg>
            删除
          </button>
        </div>
      </div>
      <div v-else class="no-instance-card">
        <p>暂无实例</p>
        <button class="btn-primary sm" @click="emit('update:modelValue', false); emit('start')">创建实例</button>
      </div>
    </div>

    <div class="settings-divider" />

    <!-- Tab bar -->
    <div class="settings-tabs">
      <button class="settings-tab" :class="{ active: activeTab === 'basic' }" @click="activeTab = 'basic'">基本设置</button>
      <button class="settings-tab" :class="{ active: activeTab === 'tools' }" @click="activeTab = 'tools'; loadTools()">工具管理</button>
      <button class="settings-tab" :class="{ active: activeTab === 'skills' }" @click="activeTab = 'skills'; loadSkills()">技能管理</button>
    </div>

    <!-- === Basic Settings Tab === -->
    <div v-show="activeTab === 'basic'">
      <div class="settings-block">
        <h4>模型配置</h4>

        <div v-if="modelSwitchProgress" class="model-restart-progress">
          <div class="spinner sm" />
          <span>Agent 重启中，请稍候...</span>
        </div>

        <div class="model-selector">
          <label class="selector-label">当前模型</label>
          <select v-model="selectedModel" class="form-select model-select">
            <option v-for="m in availableModels" :key="m" :value="m">{{ m }}{{ isSystemModel(m) ? ' (系统模型)' : '' }}</option>
          </select>
        </div>

        <div v-if="showAddModel" class="add-model-form">
          <input v-model="secretForm.name" class="form-input" placeholder="名称，如 My DeepSeek" autocomplete="off" />
          <select v-model="secretForm.provider" class="form-select">
            <option value="deepseek">DeepSeek</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="openrouter">OpenRouter</option>
            <option value="other">其他</option>
          </select>
          <input v-model="secretForm.api_key" type="password" class="form-input" placeholder="API Key: sk-..." autocomplete="new-password" />
          <div class="add-model-btns">
            <button class="btn-primary sm" :disabled="secretLoading" @click="createSecret">
              {{ secretLoading ? '保存中...' : '保存' }}
            </button>
            <button class="action-btn info" @click="showAddModel = false">取消</button>
          </div>
        </div>
        <button v-else class="add-model-trigger" @click="showAddModel = true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          添加模型
        </button>
      </div>

      <div class="settings-divider" />

      <!-- Channel bindings -->
      <div class="settings-block">
        <h4>渠道绑定</h4>
        <p class="settings-hint">绑定消息平台，让 Agent 连接到微信、Telegram 等</p>

        <div v-for="ch in channels" :key="ch.id" class="channel-card">
          <div class="channel-card-header">
            <span class="channel-card-icon">{{ channelEmoji(ch.platform) }}</span>
            <span class="channel-card-name">{{ ch.platform_label }}</span>
            <span class="channel-status-dot" :class="ch.status" />
            <button class="btn-icon-sm danger" @click="deleteChannel(ch.id)" title="删除">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </div>
        </div>

        <div v-if="showAddChannel" class="add-model-form">
          <select v-model="channelForm.platform" class="form-select" @change="onChannelPlatformChange">
            <option value="" disabled>选择平台</option>
            <option v-for="(schema, key) in platformSchemas" :key="key" :value="key"
              :disabled="channels.some(c => c.platform === key)">
              {{ schema.label }}{{ channels.some(c => c.platform === key) ? ' (已绑定)' : '' }}
            </option>
          </select>

          <template v-if="channelForm.platform === 'weixin'">
            <div class="weixin-qr-area">
              <div v-if="weixinQrLoading" style="text-align:center;padding:20px">
                <div class="spinner sm" />
                <p class="settings-hint" style="margin-top:8px">正在获取二维码...</p>
              </div>
              <div v-else-if="weixinQrUrl" style="text-align:center">
                <p class="settings-hint">请使用微信扫描二维码</p>
                <img v-if="!weixinQrError" :src="weixinQrUrl" style="width:200px;height:200px;border-radius:8px;border:1px solid #e8eaed" @error="weixinQrError = true" />
                <div v-else style="padding:16px;background:#fef2f2;border-radius:8px;font-size:13px;color:#dc2626">
                  二维码图片加载失败，请检查网络后重试
                </div>
                <p class="settings-hint" style="margin-top:8px">
                  {{ weixinQrStatus === 'scanned' ? '已扫码，请在微信确认...' : weixinQrStatus === 'confirmed' ? '绑定成功！' : '等待扫码...' }}
                </p>
              </div>
              <button v-else class="btn-primary sm" @click="startWeixinQr" style="width:100%">
                获取二维码
              </button>
            </div>
          </template>

          <template v-else-if="channelForm.platform && platformSchemas[channelForm.platform]">
            <div v-for="field in platformSchemas[channelForm.platform].fields" :key="field.key">
              <input
                v-model="channelForm.config[field.key]"
                :type="field.secret ? 'password' : 'text'"
                :placeholder="field.label + (field.required ? ' *' : '') + ' - ' + field.placeholder"
                class="form-input"
                :autocomplete="field.secret ? 'new-password' : 'off'"
              />
            </div>
          </template>

          <div v-if="channelForm.platform !== 'weixin'" class="add-model-btns">
            <button class="btn-primary sm" :disabled="channelLoading" @click="createChannel">
              {{ channelLoading ? '保存中...' : '绑定' }}
            </button>
            <button class="action-btn info" @click="showAddChannel = false; cancelWeixinQr()">取消</button>
          </div>
          <div v-else class="add-model-btns">
            <button class="action-btn info" @click="showAddChannel = false; cancelWeixinQr()">关闭</button>
          </div>
        </div>
        <button v-else class="add-model-trigger" @click="showAddChannel = true; loadPlatforms()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          绑定渠道
        </button>
      </div>
    </div>

    <!-- === Tools Tab === -->
    <div v-show="activeTab === 'tools'">
      <div class="settings-block">
        <p class="settings-hint">启用或禁用 Agent 的工具集，保存后实例将自动重启</p>

        <div v-if="toolsLoading" style="text-align:center;padding:20px">
          <div class="spinner sm" />
        </div>

        <div v-else>
          <div v-for="tool in toolsList" :key="tool.name" class="tool-card">
            <div class="tool-card-header">
              <div class="tool-card-info">
                <span class="tool-card-name">{{ tool.display_name }}</span>
                <span class="tool-card-desc">{{ tool.description }}</span>
              </div>
              <el-switch v-model="tool.enabled" size="small" @change="onToolToggle" />
            </div>
            <div v-if="tool.enabled && tool.requires_api_key && tool.config_schema?.properties" class="tool-config-fields">
              <div v-for="(field, key) in tool.config_schema.properties" :key="key" class="tool-config-field"
                v-show="!field.backend || field.backend === toolConfigs[tool.name]?.['WEB_BACKEND']">
                <label class="selector-label">{{ field.title || key }}</label>
                <select
                  v-if="field.enum"
                  :value="toolConfigs[tool.name]?.[key as string] || ''"
                  @change="onToolConfigInput(tool.name, key as string, ($event.target as HTMLSelectElement).value)"
                  class="form-input"
                >
                  <option value="" disabled>{{ field.description || '请选择' }}</option>
                  <option v-for="opt in field.enum" :key="opt" :value="opt">{{ opt }}</option>
                </select>
                <input
                  v-else
                  :value="toolConfigs[tool.name]?.[key as string] || ''"
                  @input="onToolConfigInput(tool.name, key as string, ($event.target as HTMLInputElement).value)"
                  type="password"
                  class="form-input"
                  :placeholder="field.description || ''"
                  autocomplete="new-password"
                />
              </div>
            </div>
          </div>

          <button v-if="toolsModified" class="btn-primary" style="width:100%;margin-top:12px" :disabled="toolsSaving" @click="saveTools">
            {{ toolsSaving ? '保存中...' : '保存并重启实例' }}
          </button>
        </div>
      </div>
    </div>

    <!-- === Skills Tab === -->
    <div v-show="activeTab === 'skills'">
      <div class="settings-block">
        <div class="skills-header">
          <p class="settings-hint" style="margin:0">已安装 {{ skillsStats.total_installed }} 个技能</p>
          <div class="skills-header-actions">
            <button class="action-btn info" @click="showCustomForm = true" style="font-size:12px">+ 自定义</button>
            <button class="action-btn info" @click="loadAvailableSkills" style="font-size:12px">+ 安装</button>
          </div>
        </div>

        <div v-if="skillsLoading" style="text-align:center;padding:20px">
          <div class="spinner sm" />
        </div>

        <div v-else>
          <!-- Custom skill form -->
          <div v-if="showCustomForm" class="add-model-form" style="margin-bottom:12px">
            <input v-model="customSkillForm.name" class="form-input" placeholder="标识名（英文，如 my-translator）" autocomplete="off" />
            <input v-model="customSkillForm.display_name" class="form-input" placeholder="显示名称" autocomplete="off" />
            <input v-model="customSkillForm.description" class="form-input" placeholder="描述（可选）" autocomplete="off" />
            <input v-model="customSkillForm.tags" class="form-input" placeholder="标签，逗号分隔（可选）" autocomplete="off" />
            <textarea v-model="customSkillForm.content" class="form-input" placeholder="技能内容（Markdown 格式）" rows="5" style="resize:vertical" />
            <div class="add-model-btns">
              <button class="btn-primary sm" :disabled="customSaving" @click="createCustomSkill">
                {{ customSaving ? '创建中...' : '创建' }}
              </button>
              <button class="action-btn info" @click="showCustomForm = false">取消</button>
            </div>
          </div>

          <!-- Installed skills list -->
          <div v-for="skill in installedSkills" :key="skill.name" class="skill-card">
            <div class="skill-card-header">
              <div class="skill-card-info">
                <span class="skill-card-name">{{ skill.display_name || skill.name }}</span>
                <span class="skill-card-meta">
                  <span class="skill-source-badge" :class="skill.source">{{ skill.source === 'builtin' ? '内置' : skill.source === 'optional' ? '可选' : '自定义' }}</span>
                  {{ skill.name }}
                </span>
              </div>
              <div class="skill-card-actions">
                <el-switch v-model="skill.enabled" size="small" @change="toggleSkill(skill)" />
                <button class="btn-icon-sm danger" @click="skill.source === 'custom' ? deleteCustomSkill(skill.name) : uninstallSkill(skill.name)" title="卸载">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </div>
            </div>
          </div>

          <div v-if="installedSkills.length === 0 && !skillsLoading" class="no-instance-card" style="padding:16px">
            <p style="margin:0">暂无已安装技能</p>
          </div>
        </div>

        <!-- Available skills dialog -->
        <el-dialog v-model="showAvailable" title="安装技能" width="500px" :z-index="2100">
          <div v-if="availableLoading" style="text-align:center;padding:30px">
            <div class="spinner" />
            <p class="settings-hint" style="margin-top:12px">正在从容器中扫描可用技能...</p>
          </div>
          <div v-else>
            <p class="settings-hint">共 {{ availableTotal }} 个可用技能</p>
            <div v-for="cat in availableCategories" :key="cat.name" style="margin-bottom:16px">
              <h4 style="font-size:13px;margin:0 0 8px;color:#3c4043;text-transform:capitalize">{{ cat.display_name }}</h4>
              <div v-for="skill in cat.skills" :key="skill.name" class="available-skill-item">
                <div class="skill-card-info" style="flex:1">
                  <span class="skill-card-name">{{ skill.display_name || skill.name }}</span>
                  <span class="skill-card-meta">{{ skill.description }}</span>
                </div>
                <button v-if="!skill.installed" class="btn-primary sm" @click="installSkill(skill.name, skill.source)">安装</button>
                <span v-else style="color:#16a34a;font-size:12px">已安装</span>
              </div>
            </div>
          </div>
        </el-dialog>
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.settings-block h4 { font-size: 14px; font-weight: 600; margin: 0 0 12px; color: #1a1a1a; }
.settings-hint { font-size: 13px; color: #5f6368; margin: 0 0 12px; }
.settings-divider { height: 1px; background: #e8eaed; margin: 20px 0; }

.instance-card {
  background: #f1f3f4; border-radius: 12px;
  border: 1px solid #e8eaed; padding: 16px;
}
.instance-card-header {
  display: flex; align-items: center; gap: 12px; margin-bottom: 14px;
}
.instance-card-icon {
  width: 40px; height: 40px; border-radius: 10px;
  background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.12));
  color: #6366f1;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.instance-card-info { display: flex; flex-direction: column; gap: 4px; }
.instance-card-name { font-size: 15px; font-weight: 600; color: #1a1a1a; }

.status-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 500;
  width: fit-content;
}
.status-badge.running { background: rgba(34,197,94,0.1); color: #16a34a; }
.status-badge.stopped { background: #e8eaed; color: #5f6368; }
.status-badge.error { background: rgba(239,68,68,0.08); color: #ef4444; }
.status-dot-sm { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.instance-card-actions { display: flex; gap: 6px; flex-wrap: wrap; }

.action-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 12px; border-radius: 8px; border: none;
  font-size: 12px; font-weight: 500; cursor: pointer;
  transition: all 0.15s;
}
.action-btn.warning { background: rgba(245,158,11,0.1); color: #d97706; }
.action-btn.warning:hover { background: rgba(245,158,11,0.18); }
.action-btn.success { background: rgba(34,197,94,0.1); color: #16a34a; }
.action-btn.success:hover { background: rgba(34,197,94,0.18); }
.action-btn.info { background: rgba(99,102,241,0.08); color: #6366f1; }
.action-btn.info:hover { background: rgba(99,102,241,0.15); }
.action-btn.danger { background: rgba(239,68,68,0.06); color: #9aa0a6; }
.action-btn.danger:hover { background: rgba(239,68,68,0.1); color: #ef4444; }

.no-instance-card {
  background: #f1f3f4; border-radius: 12px;
  border: 1px dashed #dadce0; padding: 24px;
  text-align: center; color: #5f6368;
}

.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 24px; border-radius: 10px; border: none;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff; font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(99, 102, 241, 0.25); }
.btn-primary.sm { padding: 6px 16px; font-size: 13px; border-radius: 8px; }

.spinner {
  width: 32px; height: 32px;
  border: 3px solid #e8eaed;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.spinner.sm { width: 16px; height: 16px; border-width: 2px; }
@keyframes spin { to { transform: rotate(360deg); } }

.model-selector { margin-top: 12px; }
.model-restart-progress {
  display: flex; align-items: center; gap: 10px;
  padding: 12px; border-radius: 8px;
  background: rgba(99,102,241,0.06);
  color: #6366f1; font-size: 13px;
  margin-bottom: 12px;
}
.selector-label { display: block; font-size: 12px; color: #5f6368; margin-bottom: 6px; }
.model-select { width: 100%; }

.add-model-form {
  margin-top: 8px; display: flex; flex-direction: column; gap: 8px;
  background: #f1f3f4; border-radius: 10px;
  border: 1px solid #e8eaed; padding: 12px;
}
.add-model-btns { display: flex; gap: 8px; }
.add-model-trigger {
  display: flex; align-items: center; gap: 6px; justify-content: center;
  width: 100%; padding: 10px; border-radius: 8px; border: 1px dashed #dadce0;
  background: transparent; color: #5f6368; font-size: 13px; cursor: pointer;
  transition: all 0.15s; margin-top: 4px;
}
.add-model-trigger:hover { border-color: #6366f1; color: #6366f1; }

.btn-icon-sm {
  width: 24px; height: 24px; border-radius: 4px; border: none;
  background: transparent; cursor: pointer; display: flex;
  align-items: center; justify-content: center;
}
.btn-icon-sm.danger { color: #9aa0a6; }
.btn-icon-sm.danger:hover { color: #ef4444; background: rgba(239,68,68,0.08); }

.form-input, .form-select {
  padding: 8px 12px; border-radius: 8px;
  border: 1px solid #dadce0;
  background: #fff; color: #1a1a1a; font-size: 13px;
  outline: none; font-family: inherit;
}
.form-input:focus, .form-select:focus { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,0.1); }
.form-select { appearance: none; }

.channel-card {
  background: #f1f3f4; border-radius: 8px;
  border: 1px solid #e8eaed; padding: 10px 12px;
  margin-bottom: 6px;
}
.channel-card-header {
  display: flex; align-items: center; gap: 8px;
}
.channel-card-icon { font-size: 16px; }
.channel-card-name { flex: 1; font-size: 13px; font-weight: 500; color: #3c4043; }
.channel-status-dot {
  width: 6px; height: 6px; border-radius: 50%;
}
.channel-status-dot.active { background: #22c55e; }
.channel-status-dot.pending { background: #f59e0b; }
.channel-status-dot.error { background: #ef4444; }

/* Tabs */
.settings-tabs {
  display: flex; gap: 4px; margin-bottom: 16px;
  background: #f1f3f4; border-radius: 10px; padding: 3px;
}
.settings-tab {
  flex: 1; padding: 7px 12px; border-radius: 8px; border: none;
  background: transparent; color: #5f6368; font-size: 13px;
  font-weight: 500; cursor: pointer; transition: all 0.15s;
}
.settings-tab.active {
  background: #fff; color: #1a1a1a;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.settings-tab:hover:not(.active) { color: #3c4043; }

/* Tool cards */
.tool-card {
  background: #f8f9fa; border-radius: 10px;
  border: 1px solid #e8eaed; padding: 12px;
  margin-bottom: 8px; transition: border-color 0.15s;
}
.tool-card:hover { border-color: #dadce0; }
.tool-card-header {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
}
.tool-card-info { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.tool-card-name { font-size: 13px; font-weight: 600; color: #1a1a1a; }
.tool-card-desc { font-size: 12px; color: #5f6368; line-height: 1.4; }
.tool-config-fields {
  margin-top: 10px; padding-top: 10px;
  border-top: 1px solid #e8eaed;
}
.tool-config-field { margin-bottom: 6px; }

/* Skill cards */
.skills-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}
.skills-header-actions { display: flex; gap: 6px; }
.skill-card {
  background: #f8f9fa; border-radius: 8px;
  border: 1px solid #e8eaed; padding: 10px 12px;
  margin-bottom: 6px;
}
.skill-card-header {
  display: flex; align-items: center; gap: 8px;
}
.skill-card-info { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.skill-card-name {
  font-size: 13px; font-weight: 500; color: #1a1a1a;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.skill-card-meta {
  font-size: 11px; color: #9aa0a6; display: flex; align-items: center; gap: 4px;
}
.skill-card-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.skill-source-badge {
  padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 500;
}
.skill-source-badge.builtin { background: rgba(34,197,94,0.1); color: #16a34a; }
.skill-source-badge.optional { background: rgba(99,102,241,0.08); color: #6366f1; }
.skill-source-badge.custom { background: rgba(245,158,11,0.1); color: #d97706; }

.available-skill-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px;
  border: 1px solid #e8eaed; margin-bottom: 6px;
}
</style>
