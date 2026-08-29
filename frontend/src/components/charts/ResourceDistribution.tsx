import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from 'recharts'

const data = [
  { name: 'RDS Postgres', value: 3, color: '#3B82F6' },
  { name: 'EC2 Instances', value: 8, color: '#06B6D4' },
  { name: 'S3 Buckets', value: 15, color: '#10B981' },
  { name: 'IAM Roles', value: 24, color: '#F59E0B' },
  { name: 'Load Balancers', value: 2, color: '#EF4444' },
]

export function ResourceDistribution() {
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
            paddingAngle={3}
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
