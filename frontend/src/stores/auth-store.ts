import { create } from 'zustand'
import { api, setAccessToken } from '@/lib/api-client'

interface AuthState {
  token: string | null
  user_id: string | null
  full_name: string | null
  role: string | null
  permissions: string[]
  tenant_id: string | null
  is_authenticated: boolean

  login: (username: string, pin: string) => Promise<void>
  logout: () => Promise<void>
  loadFromStorage: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user_id: null,
  full_name: null,
  role: null,
  permissions: [],
  tenant_id: null,
  is_authenticated: false,

  login: async (username: string, pin: string) => {
    const res = await api.post<{
      access_token: string
      user_id: string
      full_name: string
      role: string
      permissions: string[]
      tenant_id: string
    }>('/api/v1/auth/login', { username, pin })

    setAccessToken(res.access_token)

    set({
      token: res.access_token,
      user_id: res.user_id,
      full_name: res.full_name,
      role: res.role,
      permissions: res.permissions,
      tenant_id: res.tenant_id,
      is_authenticated: true,
    })
  },

  logout: async () => {
    try {
      await api.post('/api/v1/auth/logout')
    } catch {
      // ignore logout errors
    }
    setAccessToken(null)
    set({
      token: null,
      user_id: null,
      full_name: null,
      role: null,
      permissions: [],
      tenant_id: null,
      is_authenticated: false,
    })
  },

  loadFromStorage: () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('fixit_token') : null
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        set({
          token,
          user_id: payload.sub || null,
          full_name: payload.full_name || null,
          role: payload.role || null,
          permissions: payload.permissions || [],
          tenant_id: payload.tenant_id || null,
          is_authenticated: true,
        })
      } catch {
        set({ token, is_authenticated: true })
      }
    }
  },
}))
