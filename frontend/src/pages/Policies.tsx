import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileCheck2,
  ShieldCheck,
  CheckCircle2,
  Search,
  SlidersHorizontal,
  X,
  BookOpen,
  Terminal,
  ShieldAlert,
  ArrowRight,
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { Select } from '../components/ui/select'
import { policyService } from '../services/policyService'
import type { Policy, Severity } from '../types'

export function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [isLoading, setIsLoading] = useState(true)

  // Filter/Search State
  const [search, setSearch] = useState('')
  const [frameworkFilter, setFrameworkFilter] = useState('All')
  const [severityFilter, setSeverityFilter] = useState('All')

  // Details Drawer State
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null)

  useEffect(() => {
    async function load() {
      setIsLoading(true)
      const data = await policyService.getPolicies()
      setPolicies(data)
      setIsLoading(false)
    }
    load()
  }, [])

  // Filter logic
  const filteredPolicies = policies
    .filter(
      (p) =>
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.id.toLowerCase().includes(search.toLowerCase())
    )
    .filter((p) => (frameworkFilter === 'All' ? true : p.framework === frameworkFilter))
    .filter((p) => (severityFilter === 'All' ? true : p.severity === severityFilter))

  const getSeverityColor = (sev: Severity) => {
    switch (sev) {
      case 'Critical':
        return 'text-rose-500 font-bold'
      case 'High':
        return 'text-amber-500 font-semibold'
      case 'Medium':
        return 'text-yellow-400'
      default:
        return 'text-blue-400'
    }
  }

  return (
    <div className="space-y-6 relative min-h-[80vh]">
      {/* Page Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-slate-400">Policy-as-Code registry</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white">Policy catalogue</h1>
        </div>
        <div className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3.5 py-2 text-xs font-semibold uppercase tracking-wider text-emerald-600">
          <CheckCircle2 size={14} /> 100% active
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid gap-4 md:grid-cols-3">
        {[
          { label: 'Policies catalogued', value: '28', icon: FileCheck2 },
          { label: 'Enforced guardrails', value: '184', icon: ShieldCheck },
          { label: 'Active scan coverage', value: '99.7%', icon: CheckCircle2 },
        ].map(({ label, value, icon: Icon }) => (
          <Card key={label} className="p-4 border border-[#1C2633] bg-[#0B0F14] rounded-2xl">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl border border-[#1C2633] bg-[#111720] text-primary">
              <Icon size={18} />
            </div>
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
            <div className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">{value}</div>
          </Card>
        ))}
      </div>

      {/* Toolbar Filter */}
      <Card className="p-4 flex flex-col md:flex-row gap-4 items-center justify-between border border-[#1C2633] bg-[#0B0F14]">
        {/* Search */}
        <div className="relative w-full md:max-w-xs">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search policies (ID or Name)..."
            className="w-full rounded-xl border border-[#1C2633] bg-[#111720] pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
            <SlidersHorizontal size={14} /> Filters:
          </div>

          <Select
            className="w-40"
            value={frameworkFilter}
            onChange={(val) => setFrameworkFilter(val)}
            options={[
              { label: 'All Frameworks', value: 'All' },
              { label: 'SOC 2 Type II', value: 'SOC 2 Type II' },
              { label: 'ISO 27001', value: 'ISO 27001' },
            ]}
          />

          <Select
            className="w-36"
            value={severityFilter}
            onChange={(val) => setSeverityFilter(val)}
            options={[
              { label: 'All Severities', value: 'All' },
              { label: 'Critical', value: 'Critical' },
              { label: 'High', value: 'High' },
              { label: 'Medium', value: 'Medium' },
              { label: 'Low', value: 'Low' },
            ]}
          />
        </div>
      </Card>

      {/* Policies table */}
      <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl overflow-hidden">
        {isLoading ? (
          <div className="space-y-3 py-6">
            {[1, 2].map((n) => (
              <div key={n} className="h-12 bg-[#111720]/40 rounded-xl animate-pulse border border-[#1C2633]/60" />
            ))}
          </div>
        ) : filteredPolicies.length === 0 ? (
          <div className="py-12 text-center text-slate-500 font-medium">No policies found matching selection.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-[#1C2633] text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="pb-3 pr-4 font-semibold">Policy ID</th>
                  <th className="pb-3 pr-4 font-semibold">Name</th>
                  <th className="pb-3 pr-4 font-semibold">Framework</th>
                  <th className="pb-3 pr-4 font-semibold">Severity</th>
                  <th className="pb-3 pr-4 font-semibold">Status</th>
                  <th className="pb-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1C2633]/60">
                {filteredPolicies.map((policy) => (
                  <tr key={policy.id} className="hover:bg-[#111720]/20 transition group">
                    <td className="py-4 pr-4 font-mono font-semibold text-white">{policy.id}</td>
                    <td className="py-4 pr-4 text-slate-200 font-medium">{policy.name}</td>
                    <td className="py-4 pr-4 text-slate-400 text-xs">{policy.framework}</td>
                    <td className={`py-4 pr-4 text-xs ${getSeverityColor(policy.severity)}`}>
                      {policy.severity}
                    </td>
                    <td className="py-4 pr-4">
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                          policy.status === 'PASS'
                            ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-600'
                            : 'border-rose-500/20 bg-rose-500/10 text-rose-500'
                        }`}
                      >
                        {policy.status}
                      </span>
                    </td>
                    <td className="py-4 text-right">
                      <button
                        onClick={() => setSelectedPolicy(policy)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-[#1C2633] bg-[#111720] px-3 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-[#1c2633] transition"
                      >
                        Inspect <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Details sidebar drawer */}
      <AnimatePresence>
        {selectedPolicy && (
          <div className="fixed inset-0 z-50 flex justify-end">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedPolicy(null)}
              className="absolute inset-0 bg-black"
            />

            {/* Drawer */}
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
                    <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider">
                      OPA Engine Rule - {selectedPolicy.id}
                    </span>
                    <h2 className="text-xl font-semibold text-white mt-1">{selectedPolicy.name}</h2>
                  </div>
                  <button
                    onClick={() => setSelectedPolicy(null)}
                    className="rounded-lg border border-[#1C2633] bg-[#111720] p-1.5 text-slate-400 hover:text-white"
                  >
                    <X size={16} />
                  </button>
                </div>

                {/* Metadata details */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/45 p-3 text-center">
                    <span className="block text-[9px] uppercase tracking-wider text-slate-500">Framework</span>
                    <span className="text-xs font-semibold text-slate-200 mt-1 block">{selectedPolicy.framework}</span>
                  </div>
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/45 p-3 text-center">
                    <span className="block text-[9px] uppercase tracking-wider text-slate-500">Severity</span>
                    <span className={`text-xs font-bold mt-1 block ${getSeverityColor(selectedPolicy.severity)}`}>
                      {selectedPolicy.severity}
                    </span>
                  </div>
                  <div className="rounded-xl border border-[#1C2633] bg-[#111720]/45 p-3 text-center">
                    <span className="block text-[9px] uppercase tracking-wider text-slate-500">Last Scanned</span>
                    <span className="text-xs font-semibold text-slate-400 mt-1 block">{selectedPolicy.lastEvaluation}</span>
                  </div>
                </div>

                {/* Rule description */}
                <div className="space-y-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <BookOpen size={14} className="text-primary" /> Rule Specification
                  </h3>
                  <p className="text-sm text-slate-450 leading-relaxed">{selectedPolicy.description}</p>
                </div>

                {/* Remediation diff code block */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <Terminal size={14} className="text-primary" /> Recommended HCL Correction
                  </h3>
                  <div className="rounded-xl border border-[#1C2633] bg-[#05070A] p-4 font-mono text-[11px] select-text leading-5 text-slate-350">
                    <div className="mb-2 text-slate-500 text-[10px] uppercase border-b border-[#1C2633] pb-1 font-semibold">
                      Terraform Patch diff
                    </div>
                    <pre className="whitespace-pre-wrap">{selectedPolicy.remediationCode}</pre>
                  </div>
                </div>

                {/* Exception Alert */}
                {selectedPolicy.status === 'FAIL' && (
                  <div className="p-4 rounded-xl border border-rose-500/20 bg-rose-500/5 text-xs text-rose-400 flex items-start gap-2.5">
                    <ShieldAlert size={16} className="shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold block mb-1">OPA Evaluation Alert</span>
                      Active resources are violating this policy rule. Check your latest rollout logs to apply automated remediation scripts.
                    </div>
                  </div>
                )}
              </div>

              {/* Close Footer */}
              <div className="p-6 border-t border-[#1C2633]/60 bg-[#111720]/20 flex">
                <button
                  onClick={() => setSelectedPolicy(null)}
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
