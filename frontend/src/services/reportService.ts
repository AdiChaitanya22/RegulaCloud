import { request } from './api'
import type { Report } from '../types'

const mockReports: Report[] = [
  {
    id: 'rep-1',
    title: 'PCI DSS Compliance Audit Report',
    date: 'August 2026',
    status: 'Ready',
    grade: 'A',
    score: '98.4%',
    desc: 'Full regulatory compliance audit for the core payment services environment.',
  },
  {
    id: 'rep-2',
    title: 'SOC 2 Type II Gap Analysis',
    date: 'July 2026',
    status: 'Ready',
    grade: 'A',
    score: '96.2%',
    desc: 'Annual system infrastructure and data privacy controls evaluation report.',
  },
  {
    id: 'rep-3',
    title: 'HIPAA Technical Safeguards Review',
    date: 'June 2026',
    status: 'Action Required',
    grade: 'B',
    score: '84.0%',
    desc: 'Evaluation of electronic protected health information (ePHI) access controls.',
  },
]

export const reportService = {
  async getReports(): Promise<Report[]> {
    const response = await request<Report[]>('/reports')
    if (response.data) {
      return response.data
    }
    return mockReports
  },

  async generateReport(template: { title: string; desc: string; score: string; grade: string }): Promise<Report> {
    const response = await request<Report>('/reports/generate', {
      method: 'POST',
      body: JSON.stringify(template),
    })
    if (response.data) {
      return response.data
    }
    const newReport: Report = {
      id: `rep-${Date.now()}`,
      title: template.title,
      date: 'Just now',
      status: 'Ready',
      grade: template.grade,
      score: template.score,
      desc: template.desc,
    }
    mockReports.unshift(newReport)
    return newReport
  },
}
