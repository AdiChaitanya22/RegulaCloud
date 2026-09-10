import { request } from './api'
import type { Report } from '../types'

export const reportService = {
  async getReports(): Promise<Report[]> {
    const response = await request<Report[]>('/reports')
    if (response.data) {
      return response.data
    }
    return []
  },

  async generateReport(template: { title: string; desc: string; score: string; grade: string }, projectId: string): Promise<Report> {
    const response = await request<Report>('/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ ...template, projectId }),
    })
    if (response.data) {
      return response.data
    }
    throw new Error('Failed to generate report')
  },
}
