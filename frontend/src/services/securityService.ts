import { request } from './api'
import type { SecurityFinding } from '../types'

const mockFindings: SecurityFinding[] = [
  {
    id: 'sec-001',
    severity: 'Critical',
    title: 'RDS Public Ingress Enabled',
    description: 'Database instance ingress rules are open to the entire internet (0.0.0.0/0), posing an unauthorized database takeover risk.',
    resource: 'aws_db_instance.postgres',
    file: 'database.tf',
    line: 12,
    guideline: 'SOC 2 CC6.1 - Access Boundaries',
    remediation: 'Change publicly_accessible = true to publicly_accessible = false in the HCL file, and restrict security group ingress rules.',
  },
  {
    id: 'sec-002',
    severity: 'High',
    title: 'S3 Default SSE Encryption Disabled',
    description: 'S3 static asset bucket does not enforce server-side envelope encryption, allowing root administrators to expose object blobs.',
    resource: 'aws_s3_bucket.static_assets',
    file: 'storage.tf',
    line: 25,
    guideline: 'ISO 27001 A.12.4 - Data Cryptography',
    remediation: 'Attach an aws_s3_bucket_server_side_encryption_configuration block referencing an active KMS key.',
  },
]

export const securityService = {
  async getSecurityFindings(): Promise<SecurityFinding[]> {
    const response = await request<SecurityFinding[]>('/security/findings')
    if (response.data) {
      return response.data
    }
    return mockFindings
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
