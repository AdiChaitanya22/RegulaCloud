import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const data = [
  { name: 'Mon', Success: 18, Failed: 0 },
  { name: 'Tue', Success: 24, Failed: 1 },
  { name: 'Wed', Success: 15, Failed: 2 },
  { name: 'Thu', Success: 30, Failed: 0 },
  { name: 'Fri', Success: 22, Failed: 1 },
  { name: 'Sat', Success: 8, Failed: 0 },
  { name: 'Sun', Success: 12, Failed: 0 },
]

export function DeploymentActivity() {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#1C2633" strokeDasharray="4 4" vertical={false} />
          <XAxis dataKey="name" stroke="#64748b" tickLine={false} axisLine={false} />
          <YAxis stroke="#64748b" tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{
              background: '#111720',
              border: '1px solid #1C2633',
              borderRadius: 12,
              color: '#e2e8f0',
            }}
          />
          <Legend />
          <Bar dataKey="Success" fill="#10B981" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Failed" fill="#EF4444" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
