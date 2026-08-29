import { useState, useRef, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'

interface SelectOption {
  label: string
  value: string
}

interface SelectProps {
  options: SelectOption[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

export function Select({ options, value, onChange, placeholder = 'Select option...', className = '' }: SelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  const selectedOption = options.find((opt) => opt.value === value)

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [])

  return (
    <div ref={containerRef} className={`relative w-full ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-2.5 text-left text-sm text-slate-200 focus:outline-none focus:border-primary transition"
      >
        <span className={selectedOption ? 'text-slate-200' : 'text-slate-500'}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown size={16} className={`text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <ul className="absolute z-[110] mt-1.5 max-h-60 w-full overflow-auto rounded-xl border border-[#1C2633] bg-[#0B0F14] p-1 shadow-soft focus:outline-none">
          {options.map((opt) => (
            <li
              key={opt.value}
              onClick={() => {
                onChange(opt.value)
                setIsOpen(false)
              }}
              className={`cursor-pointer rounded-lg px-3 py-2 text-sm transition ${
                opt.value === value
                  ? 'bg-primary text-white font-medium'
                  : 'text-slate-300 hover:bg-[#111720] hover:text-white'
              }`}
            >
              {opt.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
