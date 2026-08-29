import * as Tabs from '@radix-ui/react-tabs'
import type { ReactNode } from 'react'

interface TabItem {
  value: string
  label: string
}

export function GenericTabs({ items, children }: { items: TabItem[]; children: ReactNode[] }) {
  return (
    <Tabs.Root className="w-full" defaultValue={items[0]?.value ?? ''}>
      <Tabs.List className="mb-4 flex gap-2 rounded-xl border border-[#1C2633] bg-[#111720] p-1">
        {items.map((item) => (
          <Tabs.Trigger
            key={item.value}
            value={item.value}
            className="rounded-lg px-3 py-2 text-sm text-slate-300 data-[state=active]:bg-[#0B0F14] data-[state=active]:text-white"
          >
            {item.label}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
      {children}
    </Tabs.Root>
  )
}

export const TabsContent = Tabs.Content
