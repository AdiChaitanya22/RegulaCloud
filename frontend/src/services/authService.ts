import { request } from './api'

export interface UserProfile {
  id: string
  username: string
  email: string
  role: string
  is_active: boolean
}

export interface AuthResponse {
  access_token: string
  token_type: string
  username: string
  role: string
  email: string
}

export const authService = {
  getToken(): string | null {
    return localStorage.getItem('auth_token')
  },

  setToken(token: string) {
    localStorage.setItem('auth_token', token)
  },

  clearToken() {
    localStorage.removeItem('auth_token')
  },

  async login(username: string, password: string): Promise<AuthResponse | null> {
    const res = await request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    })
    if (res.data && res.data.access_token) {
      this.setToken(res.data.access_token)
      return res.data
    }
    return null
  },

  async getCurrentUser(): Promise<UserProfile> {
    const res = await request<UserProfile>('/auth/me')
    if (res.data) {
      return res.data
    }
    // Token missing/expired — signal failure to caller
    throw new Error(`Auth check failed: ${res.status}`)
  }
}

