export type CloudProvider = 'AWS' | 'Azure' | 'GCP'
export type Severity = 'Low' | 'Medium' | 'High' | 'Critical'
export type Status = 'PASS' | 'FAIL' | 'WARNING' | 'PENDING' | 'ACTIVE' | 'PROTECTED' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'BLOCKED'

export interface Project {
  id: string
  name: string
  cloudProvider: CloudProvider
  region: string
  complianceScore: number
  lastDeployment: string
  status: 'Protected' | 'Review' | 'At Risk'
  owner: string
  regulatory_scope?: string[]
}

export interface DeploymentStage {
  name: string
  status: 'complete' | 'running' | 'pending'
  label: string
}

export interface Deployment {
  id: string
  projectId: string
  projectName: string
  cloudProvider: CloudProvider
  region: string
  status: 'AWAITING_APPROVAL' | 'DEPLOYING' | 'SUCCESS' | 'FAILED' | 'BLOCKED'
  startedAt: string
  completedAt?: string
  complianceScore: number
  securityScore: number
  stages: DeploymentStage[]
  logs: string[]
}

export interface ComplianceFramework {
  name: string
  score: number
  status: 'Compliant' | 'Review Required'
}

export interface ComplianceResult {
  overallScore: number
  passed: number
  failed: number
  warnings: number
  notEvaluated: number
  frameworks: ComplianceFramework[]
}

export interface SecurityFinding {
  id: string
  severity: Severity
  title: string
  description: string
  resource: string
  file: string
  line: number
  guideline: string
  remediation: string
}

export interface Policy {
  id: string
  name: string
  framework: string
  severity: Severity
  description: string
  status: Status
  lastEvaluation: string
  remediationCode: string
}

export interface AIMessage {
  sender: 'user' | 'ai'
  text: string
}

export interface AuditLog {
  id: string
  actor: string
  action: string
  resource: string
  severity: Severity
  timestamp: string
}

export interface Report {
  id: string
  title: string
  date: string
  status: string
  grade: string
  score: string
  desc: string
  isGenerating?: boolean
}

export interface InfrastructureResource {
  id: string
  name: string
  type: string
  status: 'Healthy' | 'Critical' | 'Warning'
  complianceState: string
  details: Record<string, string>
  connections: string[]
}

export interface ThemeMode {
  mode: 'dark' | 'light'
}
