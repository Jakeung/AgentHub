<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../../api/auth'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const userStore = useUserStore()

const loginForm = reactive({ username: '', password: '' })
const loading = ref(false)
const showRegister = ref(false)
const registerForm = reactive({ username: '', password: '', email: '', invitation_code: '' })
const registerLoading = ref(false)

async function handleLogin() {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await authApi.login(loginForm)
    if (res.code === 0) {
      userStore.setLogin(res.data.user, res.data.permissions)
      ElMessage.success('登录成功')
      if (res.data.user.role === 'admin') {
        router.push('/admin/dashboard')
      } else {
        router.push('/user')
      }
    } else {
      ElMessage.error(res.message || '登录失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!registerForm.username || !registerForm.password) {
    ElMessage.warning('请填写必填项')
    return
  }
  if (registerForm.password.length < 8) {
    ElMessage.warning('密码至少8位')
    return
  }
  if (!registerForm.invitation_code) {
    ElMessage.warning('请输入邀请码')
    return
  }
  registerLoading.value = true
  try {
    const res = await authApi.register(registerForm)
    if (res.code === 0) {
      ElMessage.success('注册成功，请登录')
      loginForm.username = registerForm.username
      showRegister.value = false
    } else {
      ElMessage.error(res.message || '注册失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '注册失败')
  } finally {
    registerLoading.value = false
  }
}
</script>

<template>
  <div class="login-container">
    <!-- Decorative background shapes -->
    <div class="bg-shape bg-shape-1"></div>
    <div class="bg-shape bg-shape-2"></div>
    <div class="bg-shape bg-shape-3"></div>

    <div class="login-card">
      <div class="login-header">
        <div class="logo-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 1 3 3v1a3 3 0 0 1-1.1 2.3"/><path d="M6 7a3 3 0 0 0-3 3v1a3 3 0 0 0 1.1 2.3"/><circle cx="12" cy="17" r="5"/><circle cx="10" cy="16" r="1" fill="currentColor"/><circle cx="14" cy="16" r="1" fill="currentColor"/><path d="M10 19c.8.6 2.4.6 3.2 0"/></svg>
        </div>
        <h1 class="login-title">AgentHub</h1>
        <p class="login-subtitle">智能体管理平台</p>
      </div>

      <el-form @submit.prevent="handleLogin" class="login-form">
        <el-form-item>
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="login-btn"
          :loading="loading"
          @click="handleLogin"
        >
          登 录
        </el-button>
      </el-form>

      <div class="login-footer">
        没有账号？
        <el-button type="primary" link @click="showRegister = true">去注册</el-button>
      </div>
    </div>

    <!-- Register Dialog -->
    <el-dialog
      v-model="showRegister"
      width="420px"
      :show-close="false"
      class="register-dialog"
      align-center
    >
      <template #header>
        <div class="register-header">
          <div class="register-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
          </div>
          <h3 class="register-title">创建新账号</h3>
          <p class="register-subtitle">填写以下信息完成注册</p>
        </div>
      </template>
      <el-form @submit.prevent="handleRegister" label-position="top" class="register-form">
        <el-form-item label="邀请码" required>
          <el-input v-model="registerForm.invitation_code" placeholder="请输入邀请码" size="large" />
        </el-form-item>
        <el-form-item label="用户名" required>
          <el-input v-model="registerForm.username" placeholder="3-50位字母、数字或下划线" size="large" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="registerForm.password" type="password" placeholder="至少8位" size="large" show-password />
        </el-form-item>
        <el-form-item label="邮箱（可选）">
          <el-input v-model="registerForm.email" placeholder="example@email.com" size="large" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="register-footer">
          <el-button size="large" round @click="showRegister = false">取消</el-button>
          <el-button type="primary" size="large" round :loading="registerLoading" @click="handleRegister" class="register-btn">注册</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  padding: 16px;
  position: relative;
  overflow: hidden;
}

/* Decorative blurred shapes */
.bg-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  pointer-events: none;
}
.bg-shape-1 {
  width: 400px; height: 400px;
  background: rgba(99, 102, 241, 0.15);
  top: -100px; right: -80px;
}
.bg-shape-2 {
  width: 300px; height: 300px;
  background: rgba(139, 92, 246, 0.12);
  bottom: -60px; left: -60px;
}
.bg-shape-3 {
  width: 200px; height: 200px;
  background: rgba(59, 130, 246, 0.1);
  top: 40%; left: 50%;
}

.login-card {
  position: relative; z-index: 1;
  width: 100%;
  max-width: 400px;
  padding: 40px 32px;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
  backdrop-filter: blur(10px);
}

.login-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 32px;
}

.logo-icon {
  width: 56px; height: 56px;
  border-radius: 16px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 16px;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3);
}

.login-title {
  text-align: center;
  margin: 0 0 4px;
  font-size: 26px;
  font-weight: 700;
  color: #1a1a1a;
}
.login-subtitle {
  text-align: center;
  margin: 0;
  color: #9aa0a6;
  font-size: 14px;
}

.login-form {
  margin-bottom: 16px;
}
.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
}
.login-btn:hover {
  background: linear-gradient(135deg, #818cf8, #a78bfa);
}
.login-footer {
  text-align: center;
  font-size: 13px;
  color: #9aa0a6;
}

/* Mobile */
@media (max-width: 480px) {
  .login-card {
    padding: 32px 20px;
    border-radius: 16px;
  }
  .login-title { font-size: 22px; }
  .logo-icon { width: 48px; height: 48px; border-radius: 14px; }
  .logo-icon svg { width: 24px; height: 24px; }
  .bg-shape-1 { width: 250px; height: 250px; }
  .bg-shape-2 { width: 180px; height: 180px; }
}

/* Large screens */
@media (min-width: 1024px) {
  .login-card {
    max-width: 420px;
    padding: 48px 40px;
  }
}
</style>

<style>
.register-dialog .el-dialog {
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}
.register-dialog .el-dialog__header {
  padding: 0;
  margin: 0;
}
.register-dialog .el-dialog__body {
  padding: 4px 28px 0;
}
.register-dialog .el-dialog__footer {
  padding: 12px 28px 24px;
}
.register-dialog .el-form-item {
  margin-bottom: 18px;
}
.register-dialog .el-input {
  width: 100% !important;
}
</style>

<style scoped>
.register-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 28px 16px;
  background: linear-gradient(135deg, #f5f3ff, #ede9fe);
}
.register-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}
.register-title {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}
.register-subtitle {
  margin: 0;
  font-size: 13px;
  color: #9aa0a6;
}
.register-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: #555;
}
.register-form :deep(.el-input__wrapper) {
  border-radius: 10px;
}
.register-form :deep(.el-form-item) {
  margin-bottom: 18px;
}
.register-form :deep(.el-input) {
  width: 100%;
}
.register-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
.register-btn {
  min-width: 100px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
}
.register-btn:hover {
  background: linear-gradient(135deg, #818cf8, #a78bfa);
}
</style>
