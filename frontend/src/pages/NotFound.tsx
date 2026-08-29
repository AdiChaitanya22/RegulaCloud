import { Link } from 'react-router-dom'
import { ShieldAlert, ArrowLeft } from 'lucide-react'
import { Card } from '../components/ui/card'

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-4">
      <Card className="max-w-md p-8 text-center border border-[#1C2633] bg-[#0B0F14] rounded-3xl shadow-soft">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-rose-500/20 bg-rose-500/10 text-rose-500">
          <ShieldAlert size={28} />
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-white mb-2">404</h1>
        <h2 className="text-lg font-medium text-slate-200 mb-4">Resource Not Found</h2>
        <p className="text-sm text-slate-500 mb-8 leading-relaxed">
          The compliance page or infrastructure node you are trying to access does not exist or has been relocated to another security zone.
        </p>
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 rounded-xl bg-primary hover:bg-blue-600 px-5 py-3 text-sm font-bold text-white transition"
        >
          <ArrowLeft size={16} /> Return to Dashboard
        </Link>
      </Card>
    </div>
  )
}
