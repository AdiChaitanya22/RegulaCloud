import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogPortal = DialogPrimitive.Portal
export const DialogClose = DialogPrimitive.Close

export function DialogContent({ children, title }: { children: ReactNode; title: string }) {
  return (
    <DialogPortal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
      <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,720px)] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[#1C2633] bg-[#0B0F14] p-6 shadow-soft">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-medium text-white">{title}</h3>
          <DialogClose className="rounded-lg border border-[#1C2633] bg-[#111720] p-2 text-slate-300">
            <X size={16} />
          </DialogClose>
        </div>
        {children}
      </DialogPrimitive.Content>
    </DialogPortal>
  )
}
