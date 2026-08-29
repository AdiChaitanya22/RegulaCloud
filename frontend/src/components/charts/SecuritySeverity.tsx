import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from 'recharts'

const data = [
  { name: 'Critical', value: 3, color: '#EF4444' },
  { name: 'High', value: 7, color: '#F59E0B' },
  { name: 'Medium', value: 12, color: '#EAB308' },
  { name: 'Low', value: 18, color: '#3B82F6' },
]

export function SecuritySeverity() {
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
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
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
