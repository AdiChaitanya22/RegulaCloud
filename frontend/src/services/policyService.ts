import { request } from './api'
import type { Policy } from '../types'

export const policyService = {
  async getPolicies(): Promise<Policy[]> {
    const response = await request<Policy[]>('/policies')
    return response.data || []
  },

  async getPolicyDetails(id: string): Promise<Policy | null> {
    const response = await request<Policy>(`/policies/${id}`)
    return response.data || null
  },
}
