import { request } from './api'
import type { Policy } from '../types'

const mockPolicies: Policy[] = [
  {
    id: 'POL-001',
    name: 'RDS Public Ingress Boundaries',
    framework: 'SOC 2 Type II',
    severity: 'Critical',
    description: 'Enforces database storage security by disallowing internet internet ingress routing configurations.',
    status: 'FAIL',
    lastEvaluation: '10m ago',
    remediationCode: `resource "aws_db_instance" "postgres" {
-  publicly_accessible = true
+  publicly_accessible = false
}`,
  },
  {
    id: 'POL-002',
    name: 'S3 Envelope Protection',
    framework: 'ISO 27001',
    severity: 'High',
    description: 'Enforces envelope static storage encryption using default KMS keys.',
    status: 'PASS',
    lastEvaluation: '10m ago',
    remediationCode: `resource "aws_s3_bucket" "secure" {
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
}`,
  },
]

export const policyService = {
  async getPolicies(): Promise<Policy[]> {
    const response = await request<Policy[]>('/policies')
    if (response.data) {
      return response.data
    }
    return mockPolicies
  },

  async getPolicyDetails(id: string): Promise<Policy | null> {
    const response = await request<Policy>(`/policies/${id}`)
    if (response.data) {
      return response.data
    }
    const local = mockPolicies.find((p) => p.id === id)
    return local || null
  },
}
