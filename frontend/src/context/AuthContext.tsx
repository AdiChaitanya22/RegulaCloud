import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authService, type UserProfile } from '../services/authService'

interface AuthState {
  user: UserProfile | null
  isLoading: boolean
  isAuthenticated: boolean
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // On mount: validate existing token via /auth/me
  useEffect(() => {
    async function checkSession() {
      const token = authService.getToken()
      if (!token) {
        setIsLoading(false)
        return
      }
      try {
        const profile = await authService.getCurrentUser()
        setUser(profile)
      } catch {
        // Token invalid/expired — clear it
        authService.clearToken()
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }
    checkSession()
  }, [])

  const login = async (username: string, password: string) => {
    try {
      const res = await authService.login(username, password)
      if (res) {
        // Token is stored by authService.login; now fetch the full profile
        const profile = await authService.getCurrentUser()
        setUser(profile)
        return { success: true }
      }
      return { success: false, error: 'Invalid username or password.' }
    } catch {
      return { success: false, error: 'Unable to reach the authentication server.' }
    }
  }

  const logout = () => {
    authService.clearToken()
    setUser(null)
  }

  const refreshUser = async () => {
    const profile = await authService.getCurrentUser()
    setUser(profile)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
