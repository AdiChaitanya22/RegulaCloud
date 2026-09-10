import { request } from './api'
import type { AuditLog } from '../types'

export const auditService = {
  async getAuditLogs(): Promise<AuditLog[]> {
    const response = await request<AuditLog[]>('/audit/logs')
    return response.data || []
  },
}
