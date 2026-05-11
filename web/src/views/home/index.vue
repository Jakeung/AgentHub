<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const scrolled = ref(false)

function onScroll() {
  scrolled.value = window.scrollY > 20
}

function scrollToContact() {
  document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' })
}

onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <div class="landing">
    <!-- Navbar -->
    <nav class="navbar" :class="{ scrolled }">
      <div class="nav-inner">
        <div class="nav-logo">
          <div class="logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 1 3 3v1a3 3 0 0 1-1.1 2.3"/><path d="M6 7a3 3 0 0 0-3 3v1a3 3 0 0 0 1.1 2.3"/><circle cx="12" cy="17" r="5"/><circle cx="10" cy="16" r="1" fill="currentColor"/><circle cx="14" cy="16" r="1" fill="currentColor"/><path d="M10 19c.8.6 2.4.6 3.2 0"/></svg>
          </div>
          <span class="logo-text">AgentHub</span>
        </div>
        <router-link to="/login" class="nav-btn">登录</router-link>
      </div>
    </nav>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-bg">
        <div class="bg-circle c1"></div>
        <div class="bg-circle c2"></div>
        <div class="bg-circle c3"></div>
      </div>
      <div class="hero-content">
        <h1>你的专属 AI 智能体管理平台</h1>
        <p class="hero-sub">一站式部署和管理 Hermes AI Agent，轻松对接多平台消息渠道</p>
        <div class="hero-actions">
          <button class="btn-primary" @click="scrollToContact">获取邀请码</button>
          <router-link to="/login" class="btn-outline">登录</router-link>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section class="section">
      <div class="container">
        <h2 class="section-title">核心功能</h2>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon" style="background: rgba(59,130,246,0.1); color: #3b82f6">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
            </div>
            <h3>多平台接入</h3>
            <p>支持微信、Telegram、Discord 等 8 大消息平台，一次配置即可多端响应</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon" style="background: rgba(139,92,246,0.1); color: #8b5cf6">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/><circle cx="12" cy="10" r="3"/></svg>
            </div>
            <h3>一键管理</h3>
            <p>可视化创建和管理 AI 智能体，实时监控运行状态，一键启停</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon" style="background: rgba(16,185,129,0.1); color: #10b981">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>
            </div>
            <h3>安全可控</h3>
            <p>API 密钥加密存储，容器级隔离，操作审计日志全程记录</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon" style="background: rgba(245,158,11,0.1); color: #f59e0b">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/></svg>
            </div>
            <h3>多模型支持</h3>
            <p>灵活切换 DeepSeek、OpenAI、Anthropic 等多种 AI 模型</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Platforms -->
    <section class="section section-alt">
      <div class="container">
        <h2 class="section-title">支持接入平台</h2>
        <div class="platforms-grid">
          <div class="platform-item">
            <div class="platform-icon">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M8.69 4.66c2.65-1.2 5.54-1.05 8.05.19 2.42 1.2 4.17 3.43 4.76 6.03.4 1.7.28 3.51-.37 5.13-.86 2.16-2.63 3.87-4.77 4.74a8.98 8.98 0 0 1-5.48.42c-.87.47-1.76.9-2.66 1.3-.54.2-.96-.38-.75-.87.18-.47.38-.94.52-1.43a9.53 9.53 0 0 1-4.43-4.15c-1.14-2.23-1.14-4.93-.06-7.17a9.42 9.42 0 0 1 5.19-4.19z"/></svg>
            </div>
            <span>微信</span>
          </div>
          <div class="platform-item">
            <div class="platform-icon">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2-.08-.06-.19-.04-.27-.02-.12.03-1.97 1.25-5.55 3.67-.53.36-1.0.54-1.43.53-.47-.01-1.38-.27-2.05-.49-.83-.27-1.49-.42-1.43-.88.03-.24.37-.49 1.02-.74 3.99-1.74 6.65-2.89 7.99-3.44 3.8-1.58 4.59-1.86 5.1-1.87.11 0 .37.03.54.17.14.12.18.28.2.45-.01.06.01.24 0 .38z"/></svg>
            </div>
            <span>Telegram</span>
          </div>
          <div class="platform-item">
            <div class="platform-icon">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M20.32 4.37a19.8 19.8 0 0 0-4.93-1.51.07.07 0 0 0-.08.04c-.21.38-.45.87-.61 1.26a18.27 18.27 0 0 0-5.4 0 12.6 12.6 0 0 0-.62-1.26.08.08 0 0 0-.08-.04 19.74 19.74 0 0 0-4.93 1.51.07.07 0 0 0-.03.03C1.4 8.19.73 11.88 1.06 15.53a.08.08 0 0 0 .03.06 19.9 19.9 0 0 0 5.99 3.03.08.08 0 0 0 .08-.03c.46-.63.87-1.3 1.22-2a.08.08 0 0 0-.04-.11 13.1 13.1 0 0 1-1.87-.9.08.08 0 0 1 0-.12c.13-.09.25-.19.37-.29a.07.07 0 0 1 .08-.01c3.93 1.79 8.18 1.79 12.07 0a.07.07 0 0 1 .08.01c.12.1.25.2.37.29a.08.08 0 0 1 0 .12c-.6.35-1.22.65-1.87.9a.08.08 0 0 0-.04.1c.36.7.77 1.37 1.22 2a.08.08 0 0 0 .08.03 19.83 19.83 0 0 0 6-3.03.08.08 0 0 0 .03-.05c.39-4.17-.67-7.83-2.78-11.13a.06.06 0 0 0-.03-.03zM8.02 13.33c-.97 0-1.76-.89-1.76-1.98s.78-1.99 1.76-1.99c.99 0 1.78.9 1.76 1.99 0 1.09-.78 1.98-1.76 1.98zm6.52 0c-.97 0-1.76-.89-1.76-1.98s.78-1.99 1.76-1.99c.99 0 1.78.9 1.76 1.99 0 1.09-.77 1.98-1.76 1.98z"/></svg>
            </div>
            <span>Discord</span>
          </div>
          <div class="platform-item">
            <div class="platform-icon">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M5.04 15.16a2.53 2.53 0 0 1-2.53 2.53A2.53 2.53 0 0 1 0 15.16a2.53 2.53 0 0 1 2.5-2.53h2.53v2.53zm1.27 0a2.53 2.53 0 0 1 2.53-2.53 2.53 2.53 0 0 1 2.53 2.53v6.34A2.53 2.53 0 0 1 8.84 24a2.53 2.53 0 0 1-2.53-2.5v-6.34zm2.53-10.12A2.53 2.53 0 0 1 6.3 2.5 2.53 2.53 0 0 1 8.84 0a2.53 2.53 0 0 1 2.53 2.53v2.53H8.84v-.02zm0 1.27a2.53 2.53 0 0 1 2.53 2.53 2.53 2.53 0 0 1-2.53 2.53H2.5A2.53 2.53 0 0 1 0 8.84a2.53 2.53 0 0 1 2.5-2.53h6.34zm10.12 2.53a2.53 2.53 0 0 1 2.53-2.53A2.53 2.53 0 0 1 24 8.84a2.53 2.53 0 0 1-2.5 2.53h-2.54V8.84zm-1.27 0a2.53 2.53 0 0 1-2.53 2.53 2.53 2.53 0 0 1-2.53-2.53V2.5A2.53 2.53 0 0 1 15.16 0a2.53 2.53 0 0 1 2.53 2.5v6.34zm-2.53 10.12a2.53 2.53 0 0 1 2.53 2.53A2.53 2.53 0 0 1 15.16 24a2.53 2.53 0 0 1-2.53-2.5v-2.54h2.53zm0-1.27a2.53 2.53 0 0 1-2.53-2.53 2.53 2.53 0 0 1 2.53-2.53h6.34A2.53 2.53 0 0 1 24 15.16a2.53 2.53 0 0 1-2.5 2.53h-6.34z"/></svg>
            </div>
            <span>Slack</span>
          </div>
          <div class="platform-item">
            <div class="platform-icon">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.18L19.8 8 12 11.82 4.2 8 12 4.18zM4 9.18l7 3.5V19l-7-3.5V9.18zm9 9.82v-6.32l7-3.5V15.5l-7 3.5z"/></svg>
            </div>
            <span>飞书</span>
          </div>
          <div class="platform-item">
            <div class="platform-icon">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9v-2h2v2zm0-4H9V7h2v5zm4 4h-2v-2h2v2zm0-4h-2V7h2v5z"/></svg>
            </div>
            <span>钉钉</span>
          </div>
          <div class="platform-item">
            <div class="platform-icon">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/></svg>
            </div>
            <span>企业微信</span>
          </div>
          <div class="platform-item">
            <div class="platform-icon">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M12.003 2c-2.265 0-6.29 1.364-6.29 7.325v1.195S3.55 14.96 3.55 17.474c0 .665.17 1.025.396 1.025.226 0 .566-.34.972-.92.406-.58.96-1.194 1.68-1.863 0 0-.398 1.477-.398 2.588 0 .628.117.89.342.89.226 0 .505-.263.866-.665.36-.402.85-.982 1.44-1.742 0 0 .785 1.3 2.457 2.17 1.672.87 3.39.712 3.39.712s-.528-.593-.528-1.005c0-.412.234-.765.623-.765h.188c2.738 0 5.475-1.862 5.475-4.88 0-3.017-2.504-5.49-5.98-6.108v-.08C14.465 3.12 13.347 2 12.003 2z"/></svg>
            </div>
            <span>QQ</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Contact -->
    <section class="section" id="contact">
      <div class="container">
        <h2 class="section-title">获取邀请码</h2>
        <div class="contact-grid">
          <div class="contact-text">
            <h3>联系我们获取邀请码</h3>
            <p>AgentHub 目前采用邀请制注册。请通过以下方式联系我们获取邀请码，开始使用。</p>
            <a href="mailto:Jakeung@outlook.com" class="contact-email">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
              Jakeung@outlook.com
            </a>
          </div>
          <div class="contact-qr">
            <img src="/微信.jpg" alt="微信二维码" />
            <span>扫码添加微信</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-inner">
        <div class="footer-brand">AgentHub · AI 智能体管理平台</div>
        <div class="footer-links">
          <router-link to="/login">登录</router-link>
          <span class="sep">|</span>
          <router-link to="/login">注册</router-link>
        </div>
        <div class="footer-copy">Copyright 2025 AgentHub</div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  min-height: 100vh;
  background: #f8fafc;
  overflow-x: hidden;
}

/* Navbar */
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  z-index: 100;
  transition: all 0.3s;
  background: rgba(248, 250, 252, 0.6);
  backdrop-filter: blur(12px);
}
.navbar.scrolled {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.06);
}
.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}
.nav-logo {
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
}
.nav-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #6366f1;
  border: 1px solid #6366f1;
  text-decoration: none;
  transition: all 0.2s;
}
.nav-btn:hover {
  background: #6366f1;
  color: #fff;
}

/* Hero */
.hero {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 80px 24px 60px;
}
.hero-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}
.bg-circle {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
}
.c1 { width: 500px; height: 500px; background: rgba(99,102,241,0.15); top: -150px; right: -100px; }
.c2 { width: 400px; height: 400px; background: rgba(139,92,246,0.12); bottom: -100px; left: -100px; }
.c3 { width: 300px; height: 300px; background: rgba(59,130,246,0.1); top: 40%; left: 30%; }
.hero-content {
  position: relative;
  text-align: center;
  max-width: 700px;
  animation: fadeUp 0.8s ease-out;
}
.hero-content h1 {
  font-size: 42px;
  font-weight: 800;
  color: #1a1a1a;
  line-height: 1.3;
  margin: 0 0 16px;
}
.hero-sub {
  font-size: 18px;
  color: #6b7280;
  margin: 0 0 36px;
  line-height: 1.6;
}
.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

/* Buttons */
.btn-primary {
  padding: 14px 32px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
}
.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
}
.btn-outline {
  padding: 14px 32px;
  border-radius: 12px;
  border: 2px solid #e5e7eb;
  background: transparent;
  color: #374151;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
}
.btn-outline:hover {
  border-color: #6366f1;
  color: #6366f1;
}

/* Sections */
.section {
  padding: 80px 24px;
}
.section-alt {
  background: #fff;
}
.container {
  max-width: 1200px;
  margin: 0 auto;
}
.section-title {
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 48px;
}

/* Features */
.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}
.feature-card {
  background: #fff;
  border: 1px solid #f1f5f9;
  border-radius: 16px;
  padding: 32px;
  transition: all 0.3s;
}
.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.06);
}
.feature-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.feature-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px;
}
.feature-card p {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
  line-height: 1.6;
}

/* Platforms */
.platforms-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 32px;
}
.platform-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.platform-icon {
  width: 60px;
  height: 60px;
  border-radius: 14px;
  background: #f1f5f9;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.platform-item:hover .platform-icon {
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
}
.platform-item span {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

/* Contact */
.contact-grid {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 48px;
  align-items: center;
  max-width: 800px;
  margin: 0 auto;
  background: #fff;
  border: 1px solid #f1f5f9;
  border-radius: 20px;
  padding: 48px;
}
.contact-text h3 {
  font-size: 22px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 12px;
}
.contact-text p {
  font-size: 15px;
  color: #6b7280;
  margin: 0 0 24px;
  line-height: 1.6;
}
.contact-email {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #6366f1;
  font-size: 15px;
  font-weight: 500;
  text-decoration: none;
}
.contact-email:hover {
  text-decoration: underline;
}
.contact-qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.contact-qr img {
  width: 180px;
  height: 180px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  object-fit: cover;
}
.contact-qr span {
  font-size: 13px;
  color: #9ca3af;
}

/* Footer */
.footer {
  background: #1a1a2e;
  padding: 40px 24px;
}
.footer-inner {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
}
.footer-brand {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 12px;
}
.footer-links {
  margin-bottom: 12px;
}
.footer-links a {
  color: rgba(255, 255, 255, 0.5);
  text-decoration: none;
  font-size: 13px;
}
.footer-links a:hover {
  color: #fff;
}
.footer-links .sep {
  color: rgba(255, 255, 255, 0.2);
  margin: 0 12px;
}
.footer-copy {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
}

/* Animation */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Responsive */
@media (max-width: 768px) {
  .hero-content h1 { font-size: 28px; }
  .hero-sub { font-size: 15px; }
  .section { padding: 48px 16px; }
  .section-title { font-size: 22px; margin-bottom: 32px; }
  .features-grid { grid-template-columns: 1fr; }
  .platforms-grid { gap: 20px; }
  .platform-icon { width: 48px; height: 48px; border-radius: 10px; }
  .contact-grid { grid-template-columns: 1fr; text-align: center; padding: 32px 24px; }
  .contact-qr { margin-top: 16px; }
}
</style>
