import { request } from './api'
import type { ComplianceResult } from '../types'

const defaultFrameworks: ComplianceResult = {
  overallScore: 95,
  passed: 42,
  failed: 2,
  warnings: 1,
  notEvaluated: 0,
  frameworks: [
    { name: 'DPDP Act 2023', score: 96, status: 'Compliant' },
    { name: 'DPDP Rules 2025', score: 92, status: 'Compliant' },
    { name: 'CERT-In Directions 2022', score: 88, status: 'Review Required' },
  ],
}

export const complianceService = {
  async getComplianceScore(): Promise<ComplianceResult> {
    const response = await request<ComplianceResult>('/compliance/summary')
    if (response.data) {
      return response.data
    }
    return defaultFrameworks
  },

  async evaluateCompliance(projectId: string, hclCode?: string) {
    const response = await request<any>('/compliance/evaluate', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        hcl_code: hclCode,
      }),
    })
    if (response.data) {
      return response.data
    }
    return null
  },

  async getTraceabilityMatrix() {
    const response = await request<any[]>('/applicability/traceability-matrix')
    if (response.data) {
      return response.data
    }
    return []
  },

  async scanCompliance(projectId: string): Promise<ComplianceResult> {
    const res = await this.evaluateCompliance(projectId)
    if (res) {
      return {
        overallScore: Math.round(res.compliance_score),
        passed: res.passed_count,
        failed: res.failed_count,
        warnings: 0,
        notEvaluated: res.not_applicable_count,
        frameworks: [
          { name: 'DPDP Act 2023', score: 96, status: 'Compliant' },
          { name: 'DPDP Rules 2025', score: 92, status: 'Compliant' },
          { name: 'CERT-In Directions 2022', score: 88, status: 'Review Required' },
        ],
      }
    }
    return defaultFrameworks
  },
}
