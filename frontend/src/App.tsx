import { AppRoutes } from './routes'
import { ProjectProvider } from './context/ProjectContext'

function App() {
  return (
    <ProjectProvider>
      <AppRoutes />
    </ProjectProvider>
  )
}

export default App
