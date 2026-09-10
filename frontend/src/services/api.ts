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
  isFormData: boolean = false,
  timeoutMs = 8000
): Promise<APIResponse<T>> {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeoutMs)

  const token = localStorage.getItem('auth_token')
  const headers: Record<string, string> = {
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> || {}),
  }
  
  if (!isFormData) {
    headers['Content-Type'] = 'application/json'
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
      let parsedError = errText
      try {
        const json = JSON.parse(errText)
        parsedError = json.detail || json.message || errText
        if (typeof parsedError !== 'string') {
          parsedError = JSON.stringify(parsedError)
        }
      } catch (e) {}
      
      const error: any = new Error(parsedError || `Request failed with status ${response.status}`)
      error.status = response.status
      throw error
    }

    const data = await response.json()
    setBackendAvailability(true)
    return {
      status: response.status,
      data: data as T,
    }
  } catch (err: any) {
    clearTimeout(id)
    if (!err.status) {
      setBackendAvailability(false)
    }
    throw err
  }
}
