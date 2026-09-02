const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export interface APIResponse<T> {
  data?: T
  error?: string
  status: number
}

// Global flag to track backend availability
let backendAvailable = true

export function setBackendAvailability(available: boolean) {
  backendAvailable = available
}

export function isBackendAvailable() {
  return backendAvailable
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs = 8000
): Promise<APIResponse<T>> {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeoutMs)

  const token = localStorage.getItem('auth_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> || {}),
  }

  const config: RequestInit = {
    ...options,
    headers,
    signal: controller.signal,
  }

  try {
    const url = `${BASE_URL.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}`
    const response = await fetch(url, config)
    clearTimeout(id)

    if (!response.ok) {
      const errText = await response.text()
      return {
        status: response.status,
        error: errText || `Request failed with status ${response.status}`,
      }
    }

    const data = await response.json()
    setBackendAvailability(true)
    return {
      status: response.status,
      data: data as T,
    }
  } catch (err: any) {
    clearTimeout(id)
    setBackendAvailability(false)
    return {
      status: 0,
      error: err.name === 'AbortError' ? 'Request timed out' : err.message || 'Connection failed',
    }
  }
}
