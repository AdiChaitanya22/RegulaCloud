import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const data = [
  { name: 'Jan', score: 71 },
  { name: 'Feb', score: 74 },
  { name: 'Mar', score: 78 },
  { name: 'Apr', score: 82 },
  { name: 'May', score: 88 },
  { name: 'Jun', score: 90 },
  { name: 'Jul', score: 94 },
]

export function ComplianceTrend() {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="scoreFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.5} />
              <stop offset="100%" stopColor="#3B82F6" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1C2633" strokeDasharray="4 4" vertical={false} />
          <XAxis dataKey="name" stroke="#64748b" tickLine={false} axisLine={false} />
          <YAxis stroke="#64748b" tickLine={false} axisLine={false} domain={[60, 100]} />
          <Tooltip
            contentStyle={{
              background: '#111720',
              border: '1px solid #1C2633',
              borderRadius: 12,
              color: '#e2e8f0',
            }}
          />
          <Area type="monotone" dataKey="score" stroke="#3B82F6" strokeWidth={2} fill="url(#scoreFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
