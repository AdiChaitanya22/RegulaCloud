import type { ReactNode } from 'react'

interface BadgeProps {
  children: ReactNode
  variant?: 'primary' | 'success' | 'warning' | 'error' | 'default'
  className?: string
}

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  const styles = {
    default: 'border-slate-800 bg-[#111720] text-slate-300',
    primary: 'border-primary/20 bg-primary/10 text-primary',
    success: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-600',
    warning: 'border-amber-500/25 bg-amber-500/10 text-amber-600',
    error: 'border-rose-500/25 bg-rose-500/10 text-rose-500',
  }

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${styles[variant]} ${className}`}
    >
      {children}
    </span>
  )
}
