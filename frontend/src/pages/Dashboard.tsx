import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  CheckCircle2,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  FileCode,
  Sparkles,
  RefreshCw,
  Download,
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { StatCard } from '../components/ui/stat-card'
import { AnimatedCounter } from '../components/ui/animated-counter'
import { ComplianceTrend } from '../components/charts/ComplianceTrend'
import { SecuritySeverity } from '../components/charts/SecuritySeverity'
import { DeploymentActivity } from '../components/charts/DeploymentActivity'
import { ResourceDistribution } from '../components/charts/ResourceDistribution'
import { request } from '../services/api'
import { complianceService } from '../services/complianceService'

export function DashboardPage() {
  const [stats, setStats] = useState<any>({
    complianceScore: 95,
    securityFindings: 0,
    activeProjects: 2,
    monitoredControls: 6,
    deploymentsTotal: 1,
    deploymentsSuccess: 1,
    deploymentsBlocked: 0,
    policyViolations: 0,
    recentActivities: []
  })
  const [isScanning, setIsScanning] = useState(false)
  const [scanMessage, setScanMessage] = useState<string | null>(null)

  const loadStats = async () => {
    const res = await request<any>('/dashboard/stats')
    if (res.data) {
      setStats(res.data)
    }
  }

  useEffect(() => {
    loadStats()
  }, [])

  const triggerScan = async () => {
    setIsScanning(true)
    setScanMessage('Executing deterministic compliance scan across project portfolio...')
    try {
      await complianceService.evaluateCompliance('proj-healthcare-india')
      await loadStats()
      setScanMessage('Compliance scan completed and metrics updated from live database.')
      setTimeout(() => setScanMessage(null), 4000)
    } catch (e) {
      console.error('Scan error', e)
      setScanMessage('Compliance scan failed.')
    } finally {
      setIsScanning(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-slate-400">Continuous Regulatory Telemetry</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white">Production Environment</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={triggerScan}
            disabled={isScanning}
            className="inline-flex items-center gap-2 rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-2.5 text-sm font-semibold text-slate-200 hover:bg-[#1C2633] transition disabled:opacity-50"
          >
            <RefreshCw size={16} className={`text-primary ${isScanning ? 'animate-spin' : ''}`} />
            {isScanning ? 'Scanning...' : 'Trigger Scan'}
          </button>
          <a
            href="/compliance"
            className="inline-flex items-center gap-2 rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-2.5 text-sm font-semibold text-slate-200 hover:bg-[#1C2633] transition"
          >
            <TrendingUp size={16} className="text-primary" />
            Compliance Matrix
          </a>
        </div>
      </div>

      {scanMessage && (
        <div className="rounded-xl border border-primary/30 bg-primary/10 p-3 text-xs font-semibold text-primary animate-pulse flex items-center justify-between">
          <span>{scanMessage}</span>
          <button onClick={() => setScanMessage(null)} className="text-slate-400 hover:text-white">Dismiss</button>
        </div>
      )}

      {/* KPI Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard
          label="Compliance Score"
          value={<AnimatedCounter value={Math.round(stats.complianceScore)} suffix="%" />}
          trend={`${stats.activeProjects} Active Projects`}
          icon={<ShieldCheck size={16} />}
        />
        <StatCard
          label="Security Findings"
          value={<AnimatedCounter value={stats.securityFindings} />}
          trend={`${stats.criticalFindings || 0} Critical / High`}
          icon={<ShieldAlert size={16} />}
        />
        <StatCard
          label="Active Controls"
          value={<AnimatedCounter value={stats.monitoredControls} />}
          trend="Real OPA & Sonar"
          icon={<Activity size={16} />}
        />
        <StatCard
          label="Total Deployments"
          value={<AnimatedCounter value={stats.deploymentsTotal} />}
          trend={`${stats.deploymentsSuccess} Success / ${stats.deploymentsBlocked} Blocked`}
          icon={<CheckCircle2 size={16} />}
        />
        <StatCard
          label="Policy Violations"
          value={<AnimatedCounter value={stats.policyViolations} />}
          trend={stats.policyViolations === 0 ? 'Gate Passed' : 'Gated / Blocked'}
          icon={<ShieldAlert size={16} />}
        />
      </div>

      {/* Quick Actions Bar */}
      <Card className="p-4 border border-[#1C2633] bg-[#0B0F14]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Quick Actions</span>
          <div className="flex flex-wrap gap-3">
            <a
              href="/deploy"
              className="inline-flex items-center gap-2 rounded-xl bg-primary/10 border border-primary/20 px-4 py-2 text-xs font-bold text-primary hover:bg-primary/25 transition"
            >
              <FileCode size={14} /> New Deployment
            </a>
            <a
              href="/ai-assistant"
              className="inline-flex items-center gap-2 rounded-xl bg-amber-500/10 border border-amber-500/20 px-4 py-2 text-xs font-bold text-amber-500 hover:bg-amber-500/25 transition"
            >
              <Sparkles size={14} /> Ask Assistant
            </a>
            <a
              href="/reports"
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-4 py-2 text-xs font-bold text-emerald-600 hover:bg-emerald-500/25 transition"
            >
              <Download size={14} /> Compile Reports
            </a>
          </div>
        </div>
      </Card>

      {/* Primary Charts Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-lg font-medium text-white">Compliance Trend</h2>
            <span className="text-xs uppercase tracking-[0.18em] text-emerald-600 font-bold">Stable</span>
          </div>
          <ComplianceTrend />
        </Card>

        <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-lg font-medium text-white">Security Findings Severity</h2>
            <span className="text-xs uppercase tracking-[0.18em] text-slate-500 font-bold">Active Findings</span>
          </div>
          <SecuritySeverity />
        </Card>
      </div>

      {/* Secondary Charts Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-lg font-medium text-white">Deployment Activity</h2>
            <span className="text-xs uppercase tracking-[0.18em] text-slate-500 font-bold">Weekly successful vs failed</span>
          </div>
          <DeploymentActivity />
        </Card>

        <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-lg font-medium text-white">Resource Allocation</h2>
            <span className="text-xs uppercase tracking-[0.18em] text-emerald-600 font-bold">52 Monitored Assets</span>
          </div>
          <ResourceDistribution />
        </Card>
      </div>

      {/* Recent Activity Table */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid gap-6">
        <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
          <h2 className="mb-4 text-lg font-medium text-white">Recent Compliance & Scanner Activity</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-[#1C2633] text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="pb-3 pr-4 font-semibold">Event</th>
                  <th className="pb-3 pr-4 font-semibold">Details</th>
                  <th className="pb-3 pr-4 font-semibold">Time</th>
                  <th className="pb-3 font-semibold text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1C2633]/60">
                {(stats.recentActivities || []).map((act: any) => (
                  <tr key={act.id} className="hover:bg-[#111720]/20 transition">
                    <td className="py-3.5 pr-4 font-semibold text-white">{act.event}</td>
                    <td className="py-3.5 pr-4 text-slate-400 text-xs">{act.details}</td>
                    <td className="py-3.5 pr-4 text-slate-500 text-xs">{act.time}</td>
                    <td className="py-3.5 text-right">
                      <span
                        className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          act.type === 'success' || act.type === 'scan'
                            ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-600'
                            : act.type === 'alert'
                              ? 'border-rose-500/20 bg-rose-500/10 text-rose-500'
                              : act.type === 'ai'
                                ? 'border-amber-500/20 bg-amber-500/10 text-amber-600'
                                : 'border-blue-500/20 bg-blue-500/10 text-primary'
                        }`}
                      >
                        {act.type}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>
    </div>
  )
}
