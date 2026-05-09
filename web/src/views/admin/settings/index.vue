<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { adminSettingsApi, type SettingUpdate } from '../../../api/adminSettings'

// Predefined setting keys for Hermes LLM config
const llmSettings = [
  { key: 'hermes_llm_provider', label: 'LLM Provider', desc: 'Hermes 使用的推理提供商 (如 custom)', placeholder: 'custom', sensitive: false },
  { key: 'hermes_llm_model', label: '默认模型', desc: '默认使用的模型名称', placeholder: 'deepseek-chat', sensitive: false },
  { key: 'hermes_llm_base_url', label: 'API Base URL', desc: 'LLM API 端点', placeholder: 'https://api.deepseek.com/v1', sensitive: false },
  { key: 'hermes_llm_api_key', label: 'API Key', desc: '系统默认的 LLM API 密钥，所有用户共享', placeholder: 'sk-...', sensitive: true },
]

const formData = ref<Record<string, string>>({})
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ status: string; models_count?: number; models?: string[] } | null>(null)

onMounted(async () => {
  await loadSettings()
})

async function loadSettings() {
  loading.value = true
  try {
    const res = await adminSettingsApi.list()
    if (res.code === 0) {
      const map: Record<string, string> = {}
      for (const s of res.data) {
        map[s.key] = s.value
      }
      formData.value = map
    }
  } catch (e: any) {
    ElMessage.error('加载设置失败')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  testResult.value = null
  try {
    const settings: SettingUpdate[] = llmSettings.map(s => ({
      key: s.key,
      value: formData.value[s.key] || '',
      description: s.desc,
    }))
    const res = await adminSettingsApi.update(settings)
    if (res.code === 0) {
      ElMessage.success('设置已保存')
      await loadSettings()
      await testConnection()
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (e: any) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    const res = await adminSettingsApi.testConnection()
    if (res.code === 0) {
      testResult.value = res.data
      ElMessage.success(`连接成功，发现 ${res.data.models_count} 个模型`)
    } else {
      testResult.value = { status: 'error' }
      ElMessage.warning(res.message || '连接测试失败')
    }
  } catch (e: any) {
    testResult.value = { status: 'error' }
    ElMessage.warning('连接测试失败')
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <div class="settings-page" v-loading="loading">
    <div class="page-header">
      <h2>系统设置</h2>
      <p class="page-desc">配置系统级默认参数，如 LLM API 密钥等。所有新创建的实例将使用这些默认配置。</p>
    </div>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <div class="card-header">
          <span>LLM 模型配置</span>
          <el-tag type="info" size="small">全局默认</el-tag>
        </div>
      </template>

      <el-form label-position="top" class="settings-form">
        <el-form-item v-for="s in llmSettings" :key="s.key" :label="s.label">
          <template #label>
            <div class="form-label">
              <span>{{ s.label }}</span>
              <span class="label-desc">{{ s.desc }}</span>
            </div>
          </template>
          <el-input
            v-model="formData[s.key]"
            :placeholder="s.placeholder"
            :type="s.sensitive ? 'password' : 'text'"
            :show-password="s.sensitive"
            clearable
          />
        </el-form-item>
      </el-form>

      <div class="card-actions">
        <el-button type="primary" :loading="saving" @click="saveSettings">
          保存配置
        </el-button>
        <el-button :loading="testing" @click="testConnection">
          测试连接
        </el-button>
        <el-button @click="loadSettings">重置</el-button>
      </div>

      <div v-if="testResult" class="test-result" :class="testResult.status === 'ok' ? 'success' : 'fail'">
        <template v-if="testResult.status === 'ok'">
          <div class="test-header">连接成功 — 发现 {{ testResult.models_count }} 个模型</div>
          <div v-if="testResult.models && testResult.models.length" class="test-models">
            <el-tag v-for="m in testResult.models" :key="m" size="small" type="info" style="margin: 2px 4px 2px 0">{{ m }}</el-tag>
          </div>
        </template>
        <template v-else>
          <div class="test-header">连接失败 — 请检查 API Key 和 Base URL</div>
        </template>
      </div>
    </el-card>

    <el-card shadow="never" class="settings-card hint-card">
      <template #header>
        <span>配置说明</span>
      </template>
      <div class="hint-content">
        <p><strong>DeepSeek 配置示例：</strong></p>
        <ul>
          <li>Provider: <code>custom</code></li>
          <li>模型: <code>deepseek-chat</code> 或 <code>deepseek-reasoner</code></li>
          <li>Base URL: <code>https://api.deepseek.com/v1</code></li>
          <li>API Key: 在 <a href="https://platform.deepseek.com/api-keys" target="_blank">DeepSeek 平台</a> 获取</li>
        </ul>
        <p><strong>OpenRouter 配置示例：</strong></p>
        <ul>
          <li>Provider: <code>openrouter</code></li>
          <li>模型: <code>anthropic/claude-sonnet-4</code></li>
          <li>Base URL: <code>https://openrouter.ai/api/v1</code></li>
          <li>API Key: 在 <a href="https://openrouter.ai/keys" target="_blank">OpenRouter</a> 获取</li>
        </ul>
        <el-alert type="info" :closable="false" style="margin-top: 12px">
          保存后，新创建的实例将自动使用这些配置。已有实例需要重启才能生效。
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.settings-page {
  max-width: 800px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 4px;
  font-size: 18px;
}

.page-desc {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0;
}

.settings-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.label-desc {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: normal;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.hint-content p {
  margin: 4px 0;
  font-size: 13px;
}

.hint-content ul {
  padding-left: 20px;
  margin: 4px 0 12px;
}

.hint-content li {
  font-size: 13px;
  margin: 2px 0;
}

.hint-content code {
  background: var(--primary-bg);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}

.hint-content a {
  color: var(--primary);
}

.test-result {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 13px;
}

.test-result.success {
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
}

.test-result.fail {
  background: #fef0f0;
  border: 1px solid #fde2e2;
}

.test-header {
  font-weight: 500;
  margin-bottom: 4px;
}

.test-models {
  margin-top: 8px;
}
</style>
