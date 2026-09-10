import { request } from './api'
import type { SecurityFinding } from '../types'

export const securityService = {
  async getSecurityFindings(projectId: string): Promise<SecurityFinding[]> {
    const response = await request<SecurityFinding[]>(`/security/findings?project_key=${encodeURIComponent(projectId)}`)
    if (response.data) {
      return response.data
    }
    return []
  },

  async scanSecurity(projectId: string): Promise<SecurityFinding[]> {
    const response = await request<SecurityFinding[]>('/security/scan', {
      method: 'POST',
      body: JSON.stringify({ projectId }),
    })
    if (response.data) {
      return response.data
    }
    return []
  },
}
