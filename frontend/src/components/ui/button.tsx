import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  variant?: ButtonVariant
}

export function Button({ children, variant = 'primary', className = '', ...props }: ButtonProps) {
  const base =
    'inline-flex items-center justify-center rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-[#05070A] disabled:cursor-not-allowed disabled:opacity-50'

  const variants: Record<ButtonVariant, string> = {
    primary:
      'border-primary/50 bg-primary text-white hover:bg-blue-500 shadow-[0_0_0_1px_rgba(59,130,246,0.16)]',
    secondary:
      'border-[#1C2633] bg-[#111720] text-slate-100 hover:bg-[#17212d]',
    ghost: 'border-transparent bg-transparent text-slate-300 hover:bg-[#111720] hover:text-white',
  }

  return (
    <button type="button" className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}
