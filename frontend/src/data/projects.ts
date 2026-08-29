import type { Project } from '../types'

export const mockProjects: Project[] = [
  {
    id: 'proj-healthcare',
    name: 'Healthcare Platform',
    cloudProvider: 'AWS',
    region: 'ap-south-1',
    complianceScore: 94,
    lastDeployment: '2 hours ago',
    status: 'Protected',
    owner: 'Platform Team',
  },
  {
    id: 'proj-analytics',
    name: 'Analytics Lakehouse',
    cloudProvider: 'Azure',
    region: 'centralus',
    complianceScore: 88,
    lastDeployment: '1 day ago',
    status: 'Review',
    owner: 'Data Platform',
  },
]
