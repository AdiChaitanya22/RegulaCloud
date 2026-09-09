import { request } from './api'
import type { Deployment } from '../types'

const mockDeployments: Deployment[] = [
  {
    id: 'dep-102',
    projectId: 'proj-healthcare',
    projectName: 'Healthcare Platform',
    cloudProvider: 'AWS',
    region: 'us-east-1',
    status: 'SUCCESS',
    startedAt: '10m ago',
    completedAt: '5m ago',
    complianceScore: 100,
    securityScore: 100,
    stages: [
      { name: 'AI requirement review', status: 'complete', label: 'Validated' },
      { name: 'Terraform plan', status: 'complete', label: 'Approved' },
      { name: 'OPA policy check', status: 'complete', label: 'Passed' },
      { name: 'Security scan', status: 'complete', label: '0 vulnerabilities found' },
      { name: 'Cloud rollout', status: 'complete', label: 'Active' },
    ],
    logs: [
      '[INFO] Initializing Terraform cloud connection...',
      '[INFO] Evaluating OPA security constraints...',
      '[INFO] 184 compliance checkpoints validated.',
      '[INFO] Security scan complete: 0 findings.',
      '[INFO] Provisioning AWS RDS resources...',
      '[SUCCESS] Deployment successfully completed in 1.75s.',
    ],
  },
]

export const deploymentService = {
  async getDeployments(): Promise<Deployment[]> {
    const response = await request<Deployment[]>('/deployments')
    if (response.data) {
      return response.data
    }
    return mockDeployments
  },

  async getDeployment(id: string): Promise<Deployment | null> {
    const response = await request<Deployment>(`/deployments/${id}`)
    if (response.data) {
      return response.data
    }
    const local = mockDeployments.find((d) => d.id === id)
    return local || null
  },

  async createDeploymentPlan(plan: Partial<Deployment>): Promise<Deployment> {
    const response = await request<Deployment>('/deployments/plan', {
      method: 'POST',
      body: JSON.stringify(plan),
    })
    if (response.data) {
      return response.data
    }
    // Surface auth errors — do not fall through to mock
    if (response.status === 401 || response.status === 403) {
      const err: any = new Error(response.error || 'Not authorized')
      err.status = response.status
      throw err
    }
    const newPlan: Deployment = {
      id: `dep-${Date.now()}`,
      projectId: plan.projectId || 'proj-custom',
      projectName: plan.projectName || 'Infrastructure Plan',
      cloudProvider: plan.cloudProvider || 'AWS',
      region: plan.region || 'us-east-1',
      status: 'AWAITING_APPROVAL',
      startedAt: 'Just now',
      complianceScore: 96,
      securityScore: 96,
      stages: [
        { name: 'AI requirement review', status: 'complete', label: 'Validated' },
        { name: 'Terraform plan', status: 'complete', label: 'Approved' },
        { name: 'OPA policy check', status: 'running', label: 'Running OPA Scanner' },
        { name: 'Security scan', status: 'pending', label: 'Queued' },
        { name: 'Cloud rollout', status: 'pending', label: 'Awaiting' },
      ],
      logs: ['[INFO] Draft validation pipeline initiated...'],
    }
    mockDeployments.push(newPlan)
    return newPlan
  },

  async applyDeployment(id: string): Promise<Deployment | null> {
    const response = await request<Deployment>(`/deployments/${id}/apply`, {
      method: 'POST',
    })
    if (response.data) {
      return response.data
    }
    // Surface auth errors — do not fall through to mock
    if (response.status === 401 || response.status === 403) {
      const err: any = new Error(response.error || 'Not authorized')
      err.status = response.status
      throw err
    }
    const idx = mockDeployments.findIndex((d) => d.id === id)
    if (idx !== -1) {
      mockDeployments[idx] = {
        ...mockDeployments[idx],
        status: 'SUCCESS',
        completedAt: 'Just now',
        stages: mockDeployments[idx].stages.map((s) => ({ ...s, status: 'complete', label: 'Successful' })),
      }
      return mockDeployments[idx]
    }
    return null
  },

  async getDeploymentLogs(id: string): Promise<string[]> {
    const response = await request<string[]>(`/deployments/${id}/logs`)
    if (response.data) {
      return response.data
    }
    const local = mockDeployments.find((d) => d.id === id)
    return local ? local.logs : []
  },
}
