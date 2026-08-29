import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Rocket,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Terminal,
  ArrowRight,
  X,
  Server,
  Layers,
  CircleDashed,
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { deploymentService } from '../services/deploymentService'
import type { Deployment, DeploymentStage } from '../types'

const requiredStages = [
  { key: 'REQUEST', name: 'Request Received', desc: 'Rollout request queued by pipeline runner.' },
  { key: 'ANALYZING', name: 'AI Requirement Review', desc: 'Scanning parameters for regulatory compliance.' },
  { key: 'GENERATING', name: 'Terraform Synthesis', desc: 'Generating plan structure files.' },
  { key: 'VALIDATING', name: 'Syntax Validation', desc: 'Running tf lint and validation checks.' },
  { key: 'POLICY_CHECK', name: 'OPA Policy Check', desc: 'Evaluating 184 guardrail checks.' },
  { key: 'SECURITY_SCAN', name: 'Checkov Security Scan', desc: 'Scanning for IAM leaks and open groups.' },
  { key: 'AWAITING_APPROVAL', name: 'Awaiting Approval', desc: 'Pending Security Lead manual verification.' },
  { key: 'DEPLOYING', name: 'Cloud Rollout', desc: 'Provisioning active network nodes.' },
  { key: 'SUCCESS', name: 'Deployment Success', desc: 'All assets active and verified compliant.' },
]

export function DeploymentsPage() {
  const [deployments, setDeployments] = useState<Deployment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedDep, setSelectedDep] = useState<Deployment | null>(null)

  useEffect(() => {
    async function load() {
      setIsLoading(true)
      const data = await deploymentService.getDeployments()
      setDeployments(data)
      setIsLoading(false)
    }
    load()
  }, [])

  const getStatusBadge = (status: Deployment['status']) => {
    switch (status) {
      case 'SUCCESS':
        return <Badge variant="success">Success</Badge>
      case 'FAILED':
        return <Badge variant="error">Failed</Badge>
      case 'BLOCKED':
        return <Badge variant="warning">Blocked</Badge>
      case 'DEPLOYING':
        return <Badge variant="primary">Deploying</Badge>
      default:
        return <Badge variant="default">Awaiting</Badge>
    }
  }

  const getStatusIcon = (status: 'complete' | 'running' | 'pending' | 'failed' | 'blocked') => {
    switch (status) {
      case 'complete':
        return <CheckCircle2 size={16} className="text-emerald-500 shrink-0" />
      case 'running':
        return <CircleDashed size={16} className="text-primary animate-spin shrink-0" />
      case 'failed':
        return <XCircle size={16} className="text-rose-500 shrink-0" />
      case 'blocked':
        return <AlertTriangle size={16} className="text-amber-500 shrink-0" />
      default:
        return <Clock size={16} className="text-slate-600 shrink-0" />
    }
  }

  return (
    <div className="space-y-6 relative min-h-[85vh]">
      {/* Header */}
      <div>
        <p className="text-sm text-slate-400">Rollout Logs & Actions</p>
        <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white flex items-center gap-2">
          <Rocket size={24} className="text-primary" /> Deployments
        </h1>
      </div>

      {/* Deployments List Card */}
      <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
        <h2 className="text-lg font-medium text-white mb-4">Deployment Pipeline Runs</h2>

        {isLoading ? (
          <div className="space-y-3 py-8">
            {[1, 2].map((n) => (
              <div key={n} className="h-16 rounded-xl bg-[#111720]/40 animate-pulse border border-[#1C2633]/60" />
            ))}
          </div>
        ) : deployments.length === 0 ? (
          <div className="py-12 text-center text-slate-500 font-medium">No recent deployments registered.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-[#1C2633] text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="pb-3 pr-4 font-semibold">Deployment ID</th>
                  <th className="pb-3 pr-4 font-semibold">Project</th>
                  <th className="pb-3 pr-4 font-semibold font-mono">Cloud / Region</th>
                  <th className="pb-3 pr-4 font-semibold text-center">Compliance</th>
                  <th className="pb-3 pr-4 font-semibold text-center">Security</th>
                  <th className="pb-3 pr-4 font-semibold">Started</th>
                  <th className="pb-3 pr-4 font-semibold">Status</th>
                  <th className="pb-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1C2633]/60">
                {deployments.map((dep) => (
                  <tr key={dep.id} className="hover:bg-[#111720]/20 transition group">
                    <td className="py-4 pr-4 font-mono font-semibold text-white">{dep.id}</td>
                    <td className="py-4 pr-4 text-slate-200 font-medium">{dep.projectName}</td>
                    <td className="py-4 pr-4 text-slate-400 text-xs font-mono">
                      {dep.cloudProvider} / {dep.region}
                    </td>
                    <td className="py-4 pr-4 text-center font-bold text-slate-200">{dep.complianceScore}%</td>
                    <td className="py-4 pr-4 text-center font-bold text-slate-200">{dep.securityScore}%</td>
                    <td className="py-4 pr-4 text-slate-500 text-xs">{dep.startedAt}</td>
                    <td className="py-4 pr-4">{getStatusBadge(dep.status)}</td>
                    <td className="py-4 text-right">
                      <button
                        onClick={() => setSelectedDep(dep)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-[#1C2633] bg-[#111720] px-3 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-[#1c2633] transition"
                      >
                        Details <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Deployment Details Drawer */}
      <AnimatePresence>
        {selectedDep && (
          <div className="fixed inset-0 z-50 flex justify-end">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedDep(null)}
              className="absolute inset-0 bg-black"
            />

            {/* Slide-out Drawer */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 24, stiffness: 180 }}
              className="relative w-full max-w-2xl h-full bg-[#0B0F14] border-l border-[#1C2633] shadow-soft z-10 flex flex-col justify-between"
            >
              <div className="p-6 overflow-y-auto space-y-6 flex-1">
                {/* Header */}
                <div className="flex items-start justify-between border-b border-[#1C2633]/60 pb-4">
                  <div>
                    <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider">
                      Run Detail logs - {selectedDep.id}
                    </span>
                    <h2 className="text-xl font-semibold text-white mt-1">{selectedDep.projectName}</h2>
                  </div>
                  <button
                    onClick={() => setSelectedDep(null)}
                    className="rounded-lg border border-[#1C2633] bg-[#111720] p-1.5 text-slate-400 hover:text-white"
                  >
                    <X size={16} />
                  </button>
                </div>

                {/* Cloud Metadata Indicators */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/40 p-3 text-center">
                    <span className="block text-[9px] uppercase tracking-wider text-slate-500">Cloud Provider</span>
                    <span className="text-sm font-semibold text-slate-200 mt-1 block">{selectedDep.cloudProvider}</span>
                  </div>
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/40 p-3 text-center">
                    <span className="block text-[9px] uppercase tracking-wider text-slate-500">Target Region</span>
                    <span className="text-sm font-semibold text-slate-200 mt-1 block">{selectedDep.region}</span>
                  </div>
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/40 p-3 text-center">
                    <span className="block text-[9px] uppercase tracking-wider text-slate-500">Compliance Rate</span>
                    <span className="text-sm font-bold text-emerald-500 mt-1 block">{selectedDep.complianceScore}%</span>
                  </div>
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/40 p-3 text-center">
                    <span className="block text-[9px] uppercase tracking-wider text-slate-500">Security Score</span>
                    <span className="text-sm font-bold text-primary mt-1 block">{selectedDep.securityScore}%</span>
                  </div>
                </div>

                {/* Scanner Framework Status */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/20 p-2.5 flex items-center justify-between text-xs">
                    <span className="text-slate-400">Terraform</span>
                    <span className="font-semibold text-emerald-500">Approved</span>
                  </div>
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/20 p-2.5 flex items-center justify-between text-xs">
                    <span className="text-slate-400">OPA Engine</span>
                    <span className="font-semibold text-emerald-500">Passed</span>
                  </div>
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/20 p-2.5 flex items-center justify-between text-xs">
                    <span className="text-slate-400">Checkov</span>
                    <span className="font-semibold text-emerald-500">0 Alerts</span>
                  </div>
                </div>

                {/* Animated Pipeline Stages Checklist */}
                <div className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <Layers size={14} className="text-primary" /> Pipeline Stages Audit
                  </h3>

                  <div className="relative border-l border-[#1C2633] ml-3.5 pl-5 space-y-4 py-2">
                    {requiredStages.map((stage) => {
                      // Determine the active state of this required stage
                      const activeStage = selectedDep.stages.find(
                        (s: DeploymentStage) => s.name.toLowerCase().includes(stage.key.toLowerCase().replace('_', ' '))
                      )
                      const status = activeStage ? activeStage.status : 'pending'
                      const label = activeStage ? activeStage.label : 'Awaiting'

                      return (
                        <div key={stage.key} className="relative flex items-start gap-3">
                          {/* Indicator dot */}
                          <div className="absolute -left-[29px] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-[#0B0F14] border border-[#1C2633]">
                            {getStatusIcon(status)}
                          </div>
                          <div>
                            <div className="text-sm font-semibold text-white flex items-center gap-2">
                              {stage.name}
                              <span className="text-[10px] text-slate-500 font-normal">({label})</span>
                            </div>
                            <p className="text-xs text-slate-500 mt-0.5">{stage.desc}</p>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Console Output Log */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <Terminal size={14} className="text-primary" /> Pipeline Console Output
                  </h3>
                  <div className="rounded-xl border border-[#1C2633] bg-[#05070A] p-4 font-mono text-[11px] text-slate-400 max-h-52 overflow-y-auto space-y-1 select-text leading-5">
                    {selectedDep.logs.map((log: string, idx: number) => (
                      <div key={idx} className={log.includes('[SUCCESS]') ? 'text-emerald-500' : log.includes('[ERROR]') ? 'text-rose-500 font-semibold' : ''}>
                        {log}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Resource List */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <Server size={14} className="text-primary" /> Resource Inventory
                  </h3>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {['aws_db_instance.postgres', 'aws_s3_bucket.static_assets', 'aws_security_group.ingress'].map((res) => (
                      <div key={res} className="rounded-xl border border-[#1C2633] bg-[#111720]/30 px-3 py-2 flex items-center justify-between text-xs">
                        <span className="font-mono text-slate-300">{res}</span>
                        <span className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-[9px] uppercase font-bold text-emerald-600">
                          Active
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Close Footer */}
              <div className="p-6 border-t border-[#1C2633]/60 bg-[#111720]/20 flex">
                <button
                  onClick={() => setSelectedDep(null)}
                  className="w-full inline-flex justify-center rounded-xl border border-[#1C2633] bg-[#111720] hover:bg-[#1c2633] py-3 text-sm font-bold text-slate-300 transition"
                >
                  Close Drawer
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
