import { request } from './api'
import type { ComplianceResult } from '../types'

export const complianceService = {

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

  async getComplianceScore(projectId: string): Promise<ComplianceResult | null> {
    const res = await this.evaluateCompliance(projectId)
    if (res) {
      return {
        overallScore: Math.round(res.compliance_score),
        passed: res.passed_count,
        failed: res.failed_count,
        warnings: 0,
        notEvaluated: res.not_applicable_count,
        frameworks: [
          { name: 'DPDP Act 2023', score: res.passed_count > 0 ? 100 : 0, status: res.passed_count > 0 ? 'Compliant' : 'Review Required' },
          { name: 'DPDP Rules 2025', score: res.passed_count > 0 ? 100 : 0, status: res.passed_count > 0 ? 'Compliant' : 'Review Required' },
          { name: 'CERT-In Directions 2022', score: res.passed_count > 0 ? 100 : 0, status: res.passed_count > 0 ? 'Compliant' : 'Review Required' },
        ],
      }
    }
    return null
  },
}
