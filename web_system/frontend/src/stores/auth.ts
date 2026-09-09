import { defineStore } from 'pinia'
import { api } from '@/services/api'

export type UserProfile = {
  id: number
  username: string
  display_name: string
  role: 'admin' | 'user'
  is_active: boolean
}

type AuthState = {
  token: string
  user: UserProfile | null
}

const TOKEN_KEY = 'uw_token'
const USER_KEY = 'uw_user'

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: (() => {
      const raw = localStorage.getItem(USER_KEY)
      if (!raw) return null
      try {
        return JSON.parse(raw) as UserProfile
      } catch {
        return null
      }
    })()
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    isAdmin: (state) => state.user?.role === 'admin'
  },
  actions: {
    setAuth(token: string, user: UserProfile) {
      this.token = token
      this.user = user
      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    },
    clearAuth() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
    async login(username: string, password: string) {
      const { data } = await api.post('/auth/login', { username, password })
      this.setAuth(data.data.access_token, data.data.user)
      return data.data.user as UserProfile
    },
    async fetchMe() {
      if (!this.token) return null
      const { data } = await api.get('/auth/me')
      const user = data.data as UserProfile
      this.user = user
      localStorage.setItem(USER_KEY, JSON.stringify(user))
      return user
    }
  }
})
