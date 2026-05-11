import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/home/index.vue'),
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/login/index.vue'),
  },
  // User — single page
  {
    path: '/user',
    component: () => import('../components/layout/UserLayout.vue'),
    children: [
      {
        path: '',
        name: 'user-home',
        component: () => import('../views/user/index.vue'),
      },
    ],
  },
  // Admin layout
  {
    path: '/admin',
    component: () => import('../components/layout/AdminLayout.vue'),
    children: [
      { path: '', redirect: '/admin/dashboard' },
      {
        path: 'dashboard',
        name: 'admin-dashboard',
        component: () => import('../views/admin/dashboard/index.vue'),
      },
      {
        path: 'instances',
        name: 'admin-instances',
        component: () => import('../views/admin/instances/index.vue'),
      },
      {
        path: 'users',
        name: 'admin-users',
        component: () => import('../views/admin/users/index.vue'),
      },
      {
        path: 'audit',
        name: 'admin-audit',
        component: () => import('../views/admin/audit/index.vue'),
      },
      {
        path: 'settings',
        name: 'admin-settings',
        component: () => import('../views/admin/settings/index.vue'),
      },
      {
        path: 'invitations',
        name: 'admin-invitations',
        component: () => import('../views/admin/invitations/index.vue'),
      },
    ],
  },
  // Catch-all
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const userStore = useUserStore()

  // Public pages
  if (to.path === '/' || to.path === '/login') {
    if (to.path === '/login' && userStore.isLoggedIn) {
      return next(userStore.isAdmin ? '/admin/dashboard' : '/user')
    }
    return next()
  }

  // Not logged in — try to restore session
  if (!userStore.isLoggedIn) {
    try {
      await userStore.fetchMe()
    } catch {
      return next('/login')
    }
    if (!userStore.isLoggedIn) return next('/login')
  }

  // Admin accessing /user/* → redirect
  if (to.path.startsWith('/user') && userStore.isAdmin) {
    return next('/admin/dashboard')
  }

  // User accessing /admin/* → redirect
  if (to.path.startsWith('/admin') && !userStore.isAdmin) {
    return next('/user')
  }

  next()
})

export default router
