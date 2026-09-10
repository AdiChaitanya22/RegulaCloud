import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Radar,
  CheckCircle2,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  Clock,
  Terminal,
  X,
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { securityService } from '../services/securityService'
import type { SecurityFinding } from '../types'
import { useProject } from '../context/ProjectContext'
import { AlertOctagon } from 'lucide-react'

const scanSteps = [
  'Initializing checkov scanner...',
  'Analyzing Terraform HCL assets...',
  'Evaluating IAM permissions & roles...',
  'Scanning security groups ingress...',
  'Inspecting S3 encryption config...',
  'Evaluating OPA regulatory rules...',
  'Scrutinizing credential leaks...',
  'Finalizing compliance scorecard...',
]

export function SecurityScannerPage() {
  const { activeProject } = useProject()
  const [findings, setFindings] = useState<SecurityFinding[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isScanning, setIsScanning] = useState(false)
  const [scanIndex, setScanIndex] = useState(scanSteps.length) // Completed state initially
  const [selectedFinding, setSelectedFinding] = useState<SecurityFinding | null>(null)

  // Load Initial Findings
  useEffect(() => {
    if (!activeProject) return
    async function load() {
      setIsLoading(true)
      const data = await securityService.getSecurityFindings(activeProject!.id)
      setFindings(data)
      setIsLoading(false)
    }
    load()
  }, [activeProject?.id])

  const runScan = async () => {
    if (isScanning || !activeProject) return
    setIsScanning(true)
    setScanIndex(2)
    try {
      const newFindings = await securityService.scanSecurity(activeProject.id)
      setFindings(newFindings)
      setSelectedFinding(null)
      setScanIndex(scanSteps.length)
    } catch (e) {
      console.error('Scan error', e)
    } finally {
      setIsScanning(false)
    }
  }

  const getSeverityBadge = (sev: SecurityFinding['severity']) => {
    switch (sev) {
      case 'Critical':
        return <Badge variant="error">Critical</Badge>
      case 'High':
        return <Badge variant="warning">High</Badge>
      case 'Medium':
        return <Badge variant="primary">Medium</Badge>
      default:
        return <Badge variant="default">Low</Badge>
    }
  }

  const criticalCount = findings.filter((f) => f.severity === 'Critical').length
  const highCount = findings.filter((f) => f.severity === 'High').length
  const totalFindings = findings.length

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <AlertOctagon size={48} className="text-slate-500" />
        <h2 className="text-xl font-bold text-white">No Project Selected</h2>
        <p className="text-slate-400">Please select a project from the Registry to scan for vulnerabilities.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 relative min-h-[85vh]">
      {/* Page Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-slate-400">Continuous Security Validation</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white flex items-center gap-2">
            <Radar size={26} className="text-primary animate-pulse" /> Security Scanner
          </h1>
        </div>
        <button
          onClick={runScan}
          disabled={isScanning}
          className="inline-flex items-center gap-2 rounded-xl bg-primary hover:bg-blue-600 px-5 py-3 text-sm font-bold text-white transition disabled:opacity-40 disabled:hover:bg-primary"
        >
          {isScanning ? 'Running Scan...' : 'Run security scan'}
        </button>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        {/* Scan pipeline steps */}
        <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
          <div className="mb-5 flex items-center justify-between border-b border-[#1C2633]/60 pb-3">
            <h2 className="text-lg font-medium text-white flex items-center gap-2">
              Pipeline Scanners
            </h2>
            <span
              className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                isScanning
                  ? 'border-blue-500/20 bg-blue-500/10 text-primary animate-pulse'
                  : totalFindings > 0
                    ? 'border-rose-500/20 bg-rose-500/10 text-rose-500'
                    : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-600'
              }`}
            >
              {isScanning ? 'Scanning...' : totalFindings > 0 ? 'Findings Open' : 'Clean'}
            </span>
          </div>

          <div className="space-y-2.5">
            {scanSteps.map((step, idx) => {
              const isPassed = idx < scanIndex
              const isCurrent = idx === scanIndex && isScanning

              return (
                <div
                  key={step}
                  className={`flex items-center gap-3 rounded-xl border p-3 transition ${
                    isCurrent
                      ? 'border-primary bg-primary/5'
                      : isPassed
                        ? 'border-[#1C2633]/65 bg-[#111720]/20'
                        : 'border-[#1C2633]/40 bg-[#111720]/5 opacity-40'
                  }`}
                >
                  <div
                    className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ${
                      isPassed
                        ? 'bg-emerald-500/15 text-emerald-500'
                        : isCurrent
                          ? 'bg-primary/20 text-primary'
                          : 'bg-[#05070A] text-slate-600'
                    }`}
                  >
                    {isPassed ? <CheckCircle2 size={14} /> : isCurrent ? <Clock size={14} className="animate-spin" /> : idx + 1}
                  </div>
                  <span className="text-sm font-medium text-slate-350">{step}</span>
                </div>
              )
            })}
          </div>
        </Card>

        {/* Scan Summary statistics */}
        <div className="space-y-4">
          <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
            <div className="mb-4 flex items-center gap-2 text-primary">
              <ShieldCheck size={18} />
              <h2 className="text-lg font-medium text-white">Vulnerability Summary</h2>
            </div>

            <div className="space-y-3">
              {[
                { label: 'Critical Risk Items', value: criticalCount, color: criticalCount > 0 ? 'text-rose-500' : 'text-slate-400' },
                { label: 'High Findings', value: highCount, color: highCount > 0 ? 'text-amber-500' : 'text-slate-450' },
                { label: 'Total active open issues', value: totalFindings, color: totalFindings > 0 ? 'text-rose-400 font-bold' : 'text-emerald-500 font-bold' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-xl border border-[#1C2633] bg-[#111720]/45 px-3.5 py-3">
                  <span className="text-xs text-slate-400 font-semibold">{item.label}</span>
                  <span className={`text-sm font-semibold ${item.color}`}>{item.value}</span>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-xl border border-[#1C2633] bg-[#111720] p-4">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
                <span>Scan Security Confidence</span>
                <span className="font-semibold text-white">{isScanning ? 'Scanning...' : totalFindings > 0 ? '96%' : '100%'}</span>
              </div>
              <div className="h-2 rounded-full bg-[#05070A] overflow-hidden">
                <motion.div
                  animate={{ width: isScanning ? '50%' : totalFindings > 0 ? '96%' : '100%' }}
                  className="h-2 rounded-full bg-gradient-to-r from-emerald-500 to-primary"
                />
              </div>
            </div>
          </Card>

          <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
            <div className="mb-3 flex items-center gap-2 text-primary">
              <Sparkles size={18} />
              <h2 className="text-sm font-semibold text-white">AI Remediation Assistant</h2>
            </div>
            <p className="text-xs text-slate-400 leading-5">
              Click on any security finding below to inspect details, locate code-line declarations, and download HCL remediation diff patches.
            </p>
          </Card>
        </div>
      </div>

      {/* Security Findings Grid */}
      <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
        <h2 className="text-lg font-medium text-white mb-4">Open Security Findings</h2>

        {isLoading ? (
          <div className="h-20 bg-[#111720]/40 rounded-xl animate-pulse border border-[#1C2633]/60" />
        ) : findings.length === 0 ? (
          <div className="py-12 text-center text-slate-500 font-medium">
            No active security findings detected. Security status is optimal.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-[#1C2633] text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="pb-3 pr-4 font-semibold">Severity</th>
                  <th className="pb-3 pr-4 font-semibold">Finding</th>
                  <th className="pb-3 pr-4 font-semibold">Resource</th>
                  <th className="pb-3 pr-4 font-semibold font-mono">File / Line</th>
                  <th className="pb-3 pr-4 font-semibold">Guideline</th>
                  <th className="pb-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1C2633]/60">
                {findings.map((finding) => (
                  <tr key={finding.id} className="hover:bg-[#111720]/20 transition group">
                    <td className="py-4 pr-4">{getSeverityBadge(finding.severity)}</td>
                    <td className="py-4 pr-4 text-slate-200 font-medium">{finding.title}</td>
                    <td className="py-4 pr-4 font-mono text-slate-350 text-xs">{finding.resource}</td>
                    <td className="py-4 pr-4 font-mono text-slate-400 text-xs">
                      {finding.file}:{finding.line}
                    </td>
                    <td className="py-4 pr-4 text-slate-400 text-xs font-semibold">{finding.guideline}</td>
                    <td className="py-4 text-right">
                      <button
                        onClick={() => setSelectedFinding(finding)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-[#1C2633] bg-[#111720] px-3 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-[#1c2633] transition"
                      >
                        Remediation <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Findings Details Drawer */}
      <AnimatePresence>
        {selectedFinding && (
          <div className="fixed inset-0 z-50 flex justify-end">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedFinding(null)}
              className="absolute inset-0 bg-black"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 24, stiffness: 180 }}
              className="relative w-full max-w-xl h-full bg-[#0B0F14] border-l border-[#1C2633] shadow-soft z-10 flex flex-col justify-between"
            >
              <div className="p-6 overflow-y-auto space-y-6 flex-1">
                {/* Header */}
                <div className="flex items-start justify-between border-b border-[#1C2633]/60 pb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider">
                        Finding - {selectedFinding.id}
                      </span>
                      {getSeverityBadge(selectedFinding.severity)}
                    </div>
                    <h2 className="text-xl font-semibold text-white">{selectedFinding.title}</h2>
                  </div>
                  <button
                    onClick={() => setSelectedFinding(null)}
                    className="rounded-lg border border-[#1C2633] bg-[#111720] p-1.5 text-slate-400 hover:text-white"
                  >
                    <X size={16} />
                  </button>
                </div>

                {/* Details */}
                <div className="space-y-4">
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/45 p-4 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Resource</span>
                      <span className="font-mono font-semibold text-slate-300">{selectedFinding.resource}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">File location</span>
                      <span className="font-mono font-semibold text-slate-300">
                        {selectedFinding.file} (Line {selectedFinding.line})
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Regulatory standard</span>
                      <span className="font-semibold text-slate-300">{selectedFinding.guideline}</span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Finding Description</h4>
                    <p className="text-sm text-slate-400 leading-relaxed">{selectedFinding.description}</p>
                  </div>
                </div>

                {/* Remediation code block */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <Terminal size={14} className="text-primary" /> Recommended Correction Action
                  </h4>
                  <div className="rounded-xl border border-[#1C2633] bg-[#05070A] p-4 font-mono text-[11px] select-text leading-5 text-slate-350">
                    <div className="mb-2 text-slate-500 text-[10px] uppercase border-b border-[#1C2633] pb-1 font-semibold">
                      Remediation Guide
                    </div>
                    <p className="whitespace-pre-wrap">{selectedFinding.remediation}</p>
                  </div>
                </div>
              </div>

              {/* Close Footer */}
              <div className="p-6 border-t border-[#1C2633]/60 bg-[#111720]/20 flex">
                <button
                  onClick={() => setSelectedFinding(null)}
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
