import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import type { Project } from '../types'

interface ProjectContextType {
  activeProject: Project | null
  setActiveProject: (project: Project | null) => void
  clearActiveProject: () => void
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined)

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [activeProject, setActiveProjectState] = useState<Project | null>(() => {
    try {
      const stored = sessionStorage.getItem('regulacloud_active_project')
      if (stored) {
        return JSON.parse(stored) as Project
      }
    } catch (e) {
      console.error('Failed to parse active project from session storage', e)
    }
    return null
  })

  const setActiveProject = (project: Project | null) => {
    setActiveProjectState(project)
    if (project) {
      sessionStorage.setItem('regulacloud_active_project', JSON.stringify(project))
    } else {
      sessionStorage.removeItem('regulacloud_active_project')
    }
  }

  const clearActiveProject = () => {
    setActiveProject(null)
  }

  return (
    <ProjectContext.Provider value={{ activeProject, setActiveProject, clearActiveProject }}>
      {children}
    </ProjectContext.Provider>
  )
}

export function useProject() {
  const context = useContext(ProjectContext)
  if (context === undefined) {
    throw new Error('useProject must be used within a ProjectProvider')
  }
  return context
}
