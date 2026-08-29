import { request } from './api'
import { mockProjects } from '../data/projects'
import type { Project } from '../types'

export const projectService = {
  async getProjects(): Promise<Project[]> {
    const response = await request<Project[]>('/projects')
    if (response.data) {
      return response.data
    }
    // Fallback to demo mode
    return mockProjects
  },

  async getProject(id: string): Promise<Project | null> {
    const response = await request<Project>(`/projects/${id}`)
    if (response.data) {
      return response.data
    }
    // Fallback to demo mode
    const local = mockProjects.find((p) => p.id === id)
    return local || null
  },

  async createProject(project: Omit<Project, 'id'>): Promise<Project> {
    const response = await request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(project),
    })
    if (response.data) {
      return response.data
    }
    // Fallback to demo mode
    const newProject: Project = {
      ...project,
      id: `proj-${Date.now()}`,
    }
    mockProjects.push(newProject)
    return newProject
  },

  async updateProject(id: string, project: Partial<Project>): Promise<Project | null> {
    const response = await request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(project),
    })
    if (response.data) {
      return response.data
    }
    // Fallback to demo mode
    const idx = mockProjects.findIndex((p) => p.id === id)
    if (idx !== -1) {
      mockProjects[idx] = { ...mockProjects[idx], ...project }
      return mockProjects[idx]
    }
    return null
  },

  async deleteProject(id: string): Promise<boolean> {
    const response = await request<{ success: boolean }>(`/projects/${id}`, {
      method: 'DELETE',
    })
    if (response.status === 200) {
      return true
    }
    // Fallback to demo mode
    const idx = mockProjects.findIndex((p) => p.id === id)
    if (idx !== -1) {
      mockProjects.splice(idx, 1)
      return true
    }
    return false
  },
}
