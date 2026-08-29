import { motion } from 'framer-motion'

interface SwitchProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}

export function Switch({ checked, onChange, disabled = false }: SwitchProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-[#0B0F14] ${
        checked ? 'bg-primary' : 'bg-[#111720] border-[#1C2633]'
      } ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
    >
      <motion.span
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        className={`pointer-events-none inline-block h-5 w-5 rounded-full shadow ring-0 transition duration-200 ease-in-out ${
          checked ? 'translate-x-5 bg-white' : 'translate-x-0 bg-slate-400'
        }`}
      />
    </button>
  )
}
