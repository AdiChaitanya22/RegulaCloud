import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { AIAssistantPage } from './pages/AIAssistant'
import { AuditLogsPage } from './pages/AuditLogs'
import { CompliancePage } from './pages/Compliance'
import { DashboardPage } from './pages/Dashboard'
import { DeployPage } from './pages/Deploy'
import { DeploymentsPage } from './pages/Deployments'
import { InfrastructurePage } from './pages/Infrastructure'
import { LandingPage } from './pages/Landing'
import { PoliciesPage } from './pages/Policies'
import { ProjectsPage } from './pages/Projects'
import { ReportsPage } from './pages/Reports'
import { SecurityScannerPage } from './pages/SecurityScanner'
import { SettingsPage } from './pages/Settings'
import { NotFoundPage } from './pages/NotFound'

export function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="*"
          element={
            <AppShell>
              <Routes>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/projects" element={<ProjectsPage />} />
                <Route path="/deployments" element={<DeploymentsPage />} />
                <Route path="/infrastructure" element={<InfrastructurePage />} />
                <Route path="/compliance" element={<CompliancePage />} />
                <Route path="/policies" element={<PoliciesPage />} />
                <Route path="/security" element={<SecurityScannerPage />} />
                <Route path="/ai-assistant" element={<AIAssistantPage />} />
                <Route path="/ai" element={<Navigate to="/ai-assistant" replace />} />
                <Route path="/audit" element={<AuditLogsPage />} />
                <Route path="/audit-logs" element={<Navigate to="/audit" replace />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/deploy" element={<DeployPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </AppShell>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
