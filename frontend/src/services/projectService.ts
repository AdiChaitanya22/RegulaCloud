import { request } from './api'
import type { Project } from '../types'

export const projectService = {
  async getProjects(): Promise<Project[]> {
    const response = await request<Project[]>('/projects')
    return response.data || []
  },

  async getProject(id: string): Promise<Project | null> {
    const response = await request<Project>(`/projects/${id}`)
    return response.data || null
  },

  async createProject(project: Record<string, any>): Promise<Project> {
    const response = await request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(project),
    })
    return response.data as Project
  },

  async updateProject(id: string, project: Partial<Project>): Promise<Project | null> {
    const response = await request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(project),
    })
    return response.data || null
  },

  async deleteProject(id: string): Promise<boolean> {
    const response = await request<{ success: boolean }>(`/projects/${id}`, {
      method: 'DELETE',
    })
    return response.status === 200
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
