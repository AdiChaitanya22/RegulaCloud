import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Download, FileText, Loader2, Plus, ShieldCheck } from 'lucide-react'
import { Card } from '../components/ui/card'
import { reportService } from '../services/reportService'
import type { Report } from '../types'

const extraReports = [
  {
    title: 'ISO 27001 ISMS Certification Audit',
    desc: 'Evaluation of the information security management system controls and corporate security governance policies.',
    score: '95.5%',
    grade: 'A',
  },
  {
    title: 'CIS Benchmarks Hardening Review',
    desc: 'Infrastructure configuration vulnerability and container hardening audit against CIS standard baselines.',
    score: '91.2%',
    grade: 'A',
  },
  {
    title: 'GDPR Privacy Impact Assessment',
    desc: 'Data storage, transfer encryption mechanisms, and right-to-be-forgotten checklist verification.',
    score: '99.0%',
    grade: 'A',
  },
]

export function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([])
  const [extraIndex, setExtraIndex] = useState(0)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setIsLoading(true)
      const data = await reportService.getReports()
      setReports(data)
      setIsLoading(false)
    }
    load()
  }, [])

  const handleGenerate = async () => {
    if (isGenerating || extraIndex >= extraReports.length) return
    setIsGenerating(true)

    const tempId = `rep-temp-${Date.now()}`
    const targetReport = extraReports[extraIndex]

    // Step 1: Add a loading skeleton report to the top of the list
    const newLoaderReport: Report = {
      id: tempId,
      title: targetReport.title,
      date: 'Generating...',
      status: 'Generating',
      grade: '-',
      score: '0%',
      desc: 'Retrieving audit evidence trails and evaluating OPA policy engine baseline parameters.',
      isGenerating: true,
    }

    setReports((prev) => [newLoaderReport, ...prev])
    setExtraIndex((prev) => prev + 1)

    // Call service to trigger backend or local compilation simulation
    const createdReport = await reportService.generateReport({
      title: targetReport.title,
      grade: targetReport.grade,
      score: targetReport.score,
      desc: targetReport.desc,
    })

    setReports((prev) =>
      prev.map((r) => (r.id === tempId ? { ...createdReport, isGenerating: false } : r))
    )
    setIsGenerating(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-slate-400">Documentation & Audits</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white">Compliance reports</h1>
        </div>
        <button
          onClick={handleGenerate}
          disabled={isGenerating || extraIndex >= extraReports.length || isLoading}
          className="inline-flex items-center gap-2 rounded-xl bg-primary hover:bg-blue-600 px-5 py-3 text-sm font-bold text-white transition disabled:opacity-40"
        >
          {isGenerating ? (
            <>
              <Loader2 size={16} className="animate-spin" /> Generating...
            </>
          ) : extraIndex >= extraReports.length ? (
            'All audits complete'
          ) : (
            <>
              <Plus size={16} /> Generate new report
            </>
          )}
        </button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence initial={false}>
          {reports.map((report) => (
            <motion.div
              key={report.id}
              layout
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.25 }}
              className="flex"
            >
              <Card className="p-5 flex flex-col justify-between w-full h-full relative overflow-hidden border border-[#1C2633] bg-[#0B0F14]">
                <div className="space-y-4">
                  <div className="flex items-start justify-between">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#1C2633] bg-[#111720] text-primary">
                      {report.isGenerating ? (
                        <Loader2 size={18} className="animate-spin text-primary" />
                      ) : (
                        <FileText size={18} />
                      )}
                    </div>
                    <span
                      className={`rounded-full border px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                        report.status === 'Ready'
                          ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-600'
                          : report.status === 'Generating'
                            ? 'border-blue-500/25 bg-blue-500/10 text-primary animate-pulse'
                            : 'border-amber-500/25 bg-amber-500/10 text-amber-600'
                      }`}
                    >
                      {report.status}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-lg font-medium text-white line-clamp-2">{report.title}</h3>
                    <p className={`mt-1 text-xs ${report.isGenerating ? 'text-primary font-medium' : 'text-slate-500'}`}>
                      {report.date}
                    </p>
                  </div>

                  <p className="text-sm text-slate-400 leading-relaxed">{report.desc}</p>
                </div>

                <div className="mt-6 border-t border-[#1C2633]/60 pt-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold text-white tracking-tight">{report.score}</span>
                    {!report.isGenerating && (
                      <span
                        className={`inline-flex items-center justify-center h-6 w-6 rounded-lg text-xs font-bold ${
                          report.grade === 'A'
                            ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20'
                            : 'bg-amber-500/10 text-amber-600 border border-amber-500/20'
                        }`}
                      >
                        {report.grade}
                      </span>
                    )}
                  </div>

                  <button
                    disabled={report.isGenerating}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[#1C2633] bg-[#111720] text-slate-400 hover:text-white hover:bg-[#1c2633] transition disabled:opacity-30"
                  >
                    <Download size={16} />
                  </button>
                </div>
              </Card>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <Card className="p-5">
        <div className="flex items-center gap-3 text-primary mb-4">
          <ShieldCheck size={20} />
          <h3 className="text-sm font-semibold text-white">Continuous audit compliance</h3>
        </div>
        <p className="text-sm leading-6 text-slate-400">
          All reports are generated automatically on schedule by OPA policy checking. The cloud rollout pipeline records immutable evidence hashes directly into the compliance vault, providing an audit trail for continuous assurance.
        </p>
      </Card>
    </div>
  )
}
