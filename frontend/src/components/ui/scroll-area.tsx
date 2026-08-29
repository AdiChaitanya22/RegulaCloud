import * as ScrollArea from '@radix-ui/react-scroll-area'
import type { ReactNode } from 'react'

export function ScrollAreaPanel({ children }: { children: ReactNode }) {
  return (
    <ScrollArea.Root className="h-[420px] overflow-hidden rounded-2xl border border-[#1C2633] bg-[#0B0F14]">
      <ScrollArea.Viewport className="h-full w-full p-3">{children}</ScrollArea.Viewport>
      <ScrollArea.Scrollbar orientation="vertical" className="w-2 bg-[#111720]">
        <ScrollArea.Thumb className="rounded-full bg-[#374151]" />
      </ScrollArea.Scrollbar>
    </ScrollArea.Root>
  )
}
