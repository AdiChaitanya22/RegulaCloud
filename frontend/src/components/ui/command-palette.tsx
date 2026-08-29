import * as DialogPrimitive from '@radix-ui/react-dialog'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

const commands = [
  { label: 'Go to Dashboard', path: '/dashboard' },
  { label: 'Go to Projects', path: '/projects' },
  { label: 'Go to Compliance', path: '/compliance' },
  { label: 'Go to Infrastructure', path: '/infrastructure' },
  { label: 'Start Deployment', path: '/deploy' },
  { label: 'Open AI Assistant', path: '/ai-assistant' },
  { label: 'Open Policies', path: '/policies' },
  { label: 'Open Security Scanner', path: '/security' },
]

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setOpen(true)
      }
      if (event.key === 'Escape') setOpen(false)
    }

    const handleOpen = () => setOpen(true)

    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('open-command-palette', handleOpen)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('open-command-palette', handleOpen)
    }
  }, [])

  return (
    <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,620px)] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[#1C2633] bg-[#0B0F14] p-3 shadow-soft">
          <div className="mb-3 rounded-xl border border-[#1C2633] bg-[#111720] px-3 py-2 text-sm text-slate-300">
            Type a command or use Ctrl+K
          </div>
          <div className="space-y-2">
            {commands.map((command) => (
              <button
                key={command.label}
                type="button"
                onClick={() => {
                  navigate(command.path)
                  setOpen(false)
                }}
                className="flex w-full items-center justify-between rounded-xl border border-[#1C2633] bg-[#111720] px-3 py-2 text-left text-sm text-slate-200 hover:border-primary/30"
              >
                <span>{command.label}</span>
                <span className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Go</span>
              </button>
            ))}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
