import { request } from './api'
import type { AuditLog } from '../types'

const fallbackLogs: AuditLog[] = [
  {
    id: 'log-1',
    actor: 'admin@regulacloud.gov.in',
    action: 'Compliance Verification Executed',
    resource: 'Project:Ayushman Digital Health Registry',
    severity: 'Low',
    timestamp: 'Just now',
  },
  {
    id: 'log-2',
    actor: 'system.compliance_gate',
    action: 'MANDATORY_GATE_EVALUATION',
    resource: 'DPDPA-2023-SEC8.5',
    severity: 'Low',
    timestamp: '5m ago',
  },
]

export const auditService = {
  async getAuditLogs(): Promise<AuditLog[]> {
    const response = await request<AuditLog[]>('/audit/logs')
    if (response.data && response.data.length > 0) {
      return response.data
    }
    return fallbackLogs
  },
}
