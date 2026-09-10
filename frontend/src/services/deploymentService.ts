import { request } from './api'
import type { Deployment } from '../types'

export const deploymentService = {
  async getDeployments(): Promise<Deployment[]> {
    const response = await request<Deployment[]>('/deployments')
    return response.data || []
  },

  async getDeployment(id: string): Promise<Deployment | null> {
    const response = await request<Deployment>(`/deployments/${id}`)
    return response.data || null
  },

  async createDeploymentPlan(plan: Partial<Deployment>): Promise<Deployment> {
    const response = await request<Deployment>('/deployments/plan', {
      method: 'POST',
      body: JSON.stringify(plan),
    })
    return response.data as Deployment
  },

  async applyDeployment(id: string): Promise<Deployment | null> {
    const response = await request<Deployment>(`/deployments/${id}/apply`, {
      method: 'POST',
    })
    return response.data || null
  },

  async getDeploymentLogs(id: string): Promise<string[]> {
    const response = await request<string[]>(`/deployments/${id}/logs`)
    return response.data || []
  },
}
