import type { ReactNode } from 'react'

interface StatCardProps {
  label: string
  value: ReactNode
  trend?: string
  icon?: ReactNode
}

export function StatCard({ label, value, trend, icon }: StatCardProps) {
  return (
    <div className="rounded-2xl border border-[#1C2633] bg-[#0B0F14] p-4">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</span>
        {icon && <div className="text-primary">{icon}</div>}
      </div>
      <div className="text-3xl font-semibold tracking-[-0.04em] text-white">{value}</div>
      {trend && <div className="mt-2 text-xs text-emerald-400">{trend}</div>}
    </div>
  )
}
