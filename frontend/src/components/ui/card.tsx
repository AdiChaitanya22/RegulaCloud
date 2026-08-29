import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div className={`rounded-2xl border border-[#1C2633] bg-[#0B0F14] ${className}`}>
      {children}
    </div>
  )
}
