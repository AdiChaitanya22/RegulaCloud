import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertTriangle,
  CheckCircle2,
  Search,
  SlidersHorizontal,
  XCircle,
  Download,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { Select } from '../components/ui/select'
import { auditService } from '../services/auditService'
import type { AuditLog } from '../types'

export function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [isLoading, setIsLoading] = useState(true)

  // Filters State
  const [search, setSearch] = useState('')
  const [actorFilter, setActorFilter] = useState('All')
  const [severityFilter, setSeverityFilter] = useState('All')

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 8

  useEffect(() => {
    async function load() {
      setIsLoading(true)
      const data = await auditService.getAuditLogs()
      setLogs(data)
      setIsLoading(false)
    }
    load()
  }, [])

  // Filter logs
  const filteredLogs = logs
    .filter(
      (log) =>
        log.action.toLowerCase().includes(search.toLowerCase()) ||
        log.resource.toLowerCase().includes(search.toLowerCase())
    )
    .filter((log) => (actorFilter === 'All' ? true : log.actor === actorFilter))
    .filter((log) => (severityFilter === 'All' ? true : log.severity === severityFilter))

  // Paginated logs
  const totalPages = Math.ceil(filteredLogs.length / itemsPerPage)
  const indexOfLastItem = currentPage * itemsPerPage
  const indexOfFirstItem = indexOfLastItem - itemsPerPage
  const currentLogs = filteredLogs.slice(indexOfFirstItem, indexOfLastItem)

  const handleExport = () => {
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      ['ID,Action,Actor,Resource,Severity,Timestamp']
        .concat(
          filteredLogs.map(
            (l) =>
              `"${l.id}","${l.action}","${l.actor}","${l.resource}","${l.severity}","${l.timestamp}"`
          )
        )
        .join('\n')

    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `regucloud_audit_export_${Date.now()}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const getLogStatusIcon = (severity: AuditLog['severity']) => {
    if (severity === 'Critical') {
      return <XCircle size={16} className="text-rose-500 shrink-0" />
    }
    if (severity === 'High') {
      return <AlertTriangle size={16} className="text-amber-500 shrink-0" />
    }
    return <CheckCircle2 size={16} className="text-emerald-500 shrink-0" />
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-slate-400">System Logs</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white">Audit logs</h1>
        </div>
        <button
          onClick={handleExport}
          className="inline-flex items-center gap-2 rounded-xl border border-[#1C2633] bg-[#111720] hover:bg-[#1c2633] px-4 py-2.5 text-sm font-semibold text-slate-200 transition self-start"
        >
          <Download size={16} className="text-primary" /> Export Logs
        </button>
      </div>

      {/* Toolbar Filter */}
      <Card className="p-4 flex flex-col md:flex-row gap-4 items-center justify-between border border-[#1C2633] bg-[#0B0F14]">
        {/* Search */}
        <div className="relative w-full md:max-w-xs">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setCurrentPage(1)
            }}
            placeholder="Search audit events or assets..."
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
            value={actorFilter}
            onChange={(val) => {
              setActorFilter(val)
              setCurrentPage(1)
            }}
            options={[
              { label: 'All Actors', value: 'All' },
              { label: 'AI Assistant', value: 'AI Assistant' },
              { label: 'CI/CD Pipeline', value: 'CI/CD Pipeline' },
              { label: 'Platform Team', value: 'Platform Team' },
              { label: 'Security Lead', value: 'Security Lead' },
              { label: 'Security Scanner', value: 'Security Scanner' },
            ]}
          />

          <Select
            className="w-36"
            value={severityFilter}
            onChange={(val) => {
              setSeverityFilter(val)
              setCurrentPage(1)
            }}
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

      {/* Logs Table */}
      <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl overflow-hidden">
        {isLoading ? (
          <div className="space-y-3 py-6">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-12 bg-[#111720]/40 rounded-xl animate-pulse border border-[#1C2633]/60" />
            ))}
          </div>
        ) : currentLogs.length === 0 ? (
          <div className="py-12 text-center text-slate-500 font-medium">No logs matched selection.</div>
        ) : (
          <div className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm text-slate-350">
                <thead className="border-b border-[#1C2633] text-slate-500 text-xs uppercase tracking-[0.1em]">
                  <tr>
                    <th className="pb-3 font-semibold">Event</th>
                    <th className="pb-3 font-semibold">Actor</th>
                    <th className="pb-3 font-semibold">Resource</th>
                    <th className="pb-3 font-semibold">Severity</th>
                    <th className="pb-3 font-semibold">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1C2633]/50">
                  <AnimatePresence mode="popLayout">
                    {currentLogs.map((log) => (
                      <motion.tr
                        key={log.id}
                        layout
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="hover:bg-[#111720]/20 transition"
                      >
                        <td className="py-3.5 flex items-center gap-3">
                          {getLogStatusIcon(log.severity)}
                          <span className="font-semibold text-white">{log.action}</span>
                        </td>
                        <td className="py-3.5 text-slate-400 font-medium">{log.actor}</td>
                        <td className="py-3.5">
                          <span className="font-mono text-xs bg-[#111720] border border-[#1C2633] px-2 py-0.5 rounded text-slate-300">
                            {log.resource}
                          </span>
                        </td>
                        <td className="py-3.5">
                          <span
                            className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                              log.severity === 'Critical' || log.severity === 'High'
                                ? 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                                : log.severity === 'Medium'
                                  ? 'bg-amber-500/10 text-amber-605 border-amber-500/20'
                                  : 'bg-blue-500/10 text-primary border-blue-500/20'
                            }`}
                          >
                            {log.severity}
                          </span>
                        </td>
                        <td className="py-3.5 text-slate-500 text-xs">{log.timestamp}</td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-[#1C2633]/60 pt-4 text-xs text-slate-500">
                <span>
                  Showing page {currentPage} of {totalPages} ({filteredLogs.length} items)
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                    disabled={currentPage === 1}
                    className="p-2 rounded-lg border border-[#1C2633] bg-[#111720] text-slate-400 hover:text-white transition disabled:opacity-40"
                  >
                    <ChevronLeft size={14} />
                  </button>
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                    disabled={currentPage === totalPages}
                    className="p-2 rounded-lg border border-[#1C2633] bg-[#111720] text-slate-400 hover:text-white transition disabled:opacity-40"
                  >
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
