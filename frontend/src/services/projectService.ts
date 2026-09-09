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

  async uploadInfrastructure(id: string, file?: File, hclCode?: string): Promise<{ success: boolean; message?: string }> {
    const formData = new FormData()
    if (file) formData.append('file', file)
    if (hclCode) formData.append('hcl_code', hclCode)
    
    const response = await request<{ success: boolean; message: string }>(`/projects/${id}/upload/infrastructure`, {
      method: 'POST',
      body: formData,
    }, true) // Set true for isFormData if request utility supports it. Wait, the request utility might not support FormData correctly if it forces Content-Type: application/json.
    
    // I need to check the request utility.
    return response.data || { success: false, message: 'Upload failed' }
  },

  async uploadApplication(id: string, file: File): Promise<{ success: boolean; message?: string }> {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await request<{ success: boolean; message: string }>(`/projects/${id}/upload/application`, {
      method: 'POST',
      body: formData,
    }, true)
    
    return response.data || { success: false, message: 'Upload failed' }
  },

  async getProjectHcl(id: string): Promise<string> {
    const response = await request<{ hcl_code: string }>(`/projects/${id}/hcl`)
    return response.data?.hcl_code || ''
  },

  async applyRemediations(id: string, actionIds: string[]): Promise<{ success: boolean; hcl_code?: string; applied_actions?: string[]; skipped_actions?: string[]; message?: string }> {
    const response = await request<{ hcl_code: string; applied_actions: string[]; skipped_actions: string[]; message: string }>(`/projects/${id}/remediate`, {
      method: 'POST',
      body: JSON.stringify({ action_ids: actionIds }),
    })
    
    if (response.data) {
      return { success: true, ...response.data }
    }
    return { success: false, message: response.error || 'Remediation failed' }
  }
}
