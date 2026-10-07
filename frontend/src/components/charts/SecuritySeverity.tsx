import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from 'recharts'

export function SecuritySeverity({ data = [] }: { data?: any[] }) {
  if (!data || data.length === 0) {
    return <div className="h-64 w-full flex items-center justify-center text-slate-500">No data available</div>
  }
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={80}
            paddingAngle={4}
            dataKey="value"
          >
            {data.map((entry, index) => {
              let color = '#3B82F6'
              if (entry.name === 'Pass') color = '#10B981'
              else if (entry.name === 'Fail') color = '#EF4444'
              else if (entry.name === 'Unknown') color = '#F59E0B'
              else if (entry.name === 'Not Applicable') color = '#64748b'
              return <Cell key={`cell-${index}`} fill={color} />
            })}
          </Pie>
          <Tooltip
            contentStyle={{
              background: '#111720',
              border: '1px solid #1C2633',
              borderRadius: 12,
              color: '#e2e8f0',
            }}
          />
          <Legend verticalAlign="bottom" height={36} iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
