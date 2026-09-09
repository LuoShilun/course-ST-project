import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('../layouts/MainLayout.vue'),
      meta: { requiresAuth: true, role: 'user' },
      children: [
        { path: '', redirect: '/home' },
        { path: 'home', name: 'home', component: () => import('../views/user/HomeView.vue') },
        { path: 'dashboard', name: 'dashboard', component: () => import('../views/user/DashboardView.vue') },
        { path: 'map', name: 'map', component: () => import('../views/user/MapView.vue') },
        { path: 'records', name: 'records', component: () => import('../views/user/RecordsView.vue') },
        { path: 'detect', name: 'detect', component: () => import('../views/user/DetectView.vue') },
        { path: 'assistant', name: 'assistant', component: () => import('../views/user/AssistantView.vue') }
      ]
    },
    {
      path: '/admin',
      component: () => import('../layouts/AdminLayout.vue'),
      meta: { requiresAuth: true, role: 'admin' },
      children: [
        { path: '', redirect: '/admin/robots' },
        { path: 'dashboard', name: 'admin-dashboard', component: () => import('../views/user/DashboardView.vue') },
        { path: 'map', name: 'admin-map', component: () => import('../views/user/MapView.vue') },
        { path: 'robots', name: 'admin-robots', component: () => import('../views/admin/RobotManageView.vue') },
        { path: 'users', name: 'admin-users', component: () => import('../views/admin/UserManageView.vue') },
        { path: 'models', name: 'admin-models', component: () => import('../views/admin/ModelManageView.vue') },
        { path: 'rag-config', name: 'admin-rag', component: () => import('../views/admin/RAGConfigView.vue') },
        {
          path: 'announcements',
          name: 'admin-announcements',
          component: () => import('../views/admin/AnnouncementManageView.vue')
        }
      ]
    }
  ]
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()
  const requiresAuth = to.meta.requiresAuth !== false
  const requiredRole = (to.meta.role as string | undefined) || undefined

  if (!requiresAuth) {
    if (to.path === '/login' && auth.isLoggedIn) {
      return next(auth.isAdmin ? '/admin/robots' : '/home')
    }
    return next()
  }

  if (!auth.isLoggedIn) {
    return next('/login')
  }

  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.clearAuth()
      return next('/login')
    }
  }

  if (requiredRole === 'admin' && !auth.isAdmin) {
    return next('/home')
  }

  if (requiredRole === 'user' && auth.isAdmin && to.path.startsWith('/admin') === false) {
    return next('/admin/robots')
  }

  return next()
})

export default router
