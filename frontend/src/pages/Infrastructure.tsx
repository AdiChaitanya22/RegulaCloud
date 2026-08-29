import { useState, useRef } from 'react'
import type { MouseEvent } from 'react'
import {
  Activity,
  Cloud,
  Database,
  GitBranch,
  ShieldCheck,
  Users,
  Server,
  Lock,
  Compass,
  ArrowRight,
  Maximize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'

interface TopologyNode {
  id: string
  label: string
  type: string
  status: 'Healthy' | 'Warning' | 'Critical'
  score: number
  x: number
  y: number
  desc: string
  details: Record<string, string>
  connections: string[]
}

const initialNodes: TopologyNode[] = [
  {
    id: 'internet',
    label: 'Internet Gateway',
    type: 'Gateway',
    status: 'Healthy',
    score: 100,
    x: 400,
    y: 50,
    desc: 'Public entrance tunnel providing bi-directional IP translation.',
    details: { IP: '54.210.12.8', Bandwidth: '10 Gbps', IPv6: 'Enabled' },
    connections: ['waf'],
  },
  {
    id: 'waf',
    label: 'Web Application Firewall',
    type: 'Security',
    status: 'Healthy',
    score: 100,
    x: 400,
    y: 130,
    desc: 'AWS WAF protecting load balancers from SQL injections and cross-site scripting.',
    details: { RuleSet: 'OWASP Core', Mode: 'Blocking', Inspections: '2.4M today' },
    connections: ['alb'],
  },
  {
    id: 'alb',
    label: 'Application Load Balancer',
    type: 'Balancer',
    status: 'Healthy',
    score: 100,
    x: 400,
    y: 210,
    desc: 'Public-facing ALB routing HTTPS traffic into web server subnets.',
    details: { Protocol: 'HTTPS (TLS 1.3)', Targets: '2 active subnets', Stickiness: 'None' },
    connections: ['ec2_web', 'rds_postgres'],
  },
  {
    id: 'ec2_web',
    label: 'EC2 Web Instance',
    type: 'Compute',
    status: 'Warning',
    score: 92,
    x: 280,
    y: 310,
    desc: 'Linux API server processing client healthcare records requests.',
    details: { Type: 't3.medium', OS: 'Amazon Linux 2', CPU: '24%', Memory: '4.2 GB' },
    connections: ['rds_postgres', 's3_assets'],
  },
  {
    id: 'rds_postgres',
    label: 'RDS PostgreSQL',
    type: 'Database',
    status: 'Critical',
    score: 84,
    x: 520,
    y: 310,
    desc: 'Managed PostgreSQL cluster storing patient databases and transaction records.',
    details: { Version: 'Postgres 15.4', Storage: '20 GB (GP3)', Encryption: 'KMS Default' },
    connections: [],
  },
  {
    id: 's3_assets',
    label: 'S3 Asset Storage',
    type: 'Storage',
    status: 'Healthy',
    score: 100,
    x: 180,
    y: 410,
    desc: 'Private bucket storing encrypted static client documents and attachments.',
    details: { Encryption: 'SSE-KMS', Size: '1.2 TB', Versioning: 'Enabled' },
    connections: [],
  },
  {
    id: 'iam_roles',
    label: 'IAM Compliance Vault',
    type: 'Identity',
    status: 'Healthy',
    score: 100,
    x: 620,
    y: 210,
    desc: 'AWS Identity roles enforcing strict least-privilege policies.',
    details: { Roles: '12 active', Policies: 'OPA boundary managed', MFA: 'Enforced' },
    connections: ['rds_postgres'],
  },
  {
    id: 'cloudwatch',
    label: 'CloudWatch Metrics',
    type: 'Observability',
    status: 'Healthy',
    score: 100,
    x: 620,
    y: 110,
    desc: 'Central monitoring collector matching audit logs and threshold warnings.',
    details: { Alarms: '2 active', LogRetention: '90 days', Metrics: 'Detailed' },
    connections: [],
  },
]

const metrics = [
  { label: 'Availability', value: '99.98%', icon: Activity },
  { label: 'Latency', value: '142 ms', icon: GitBranch },
  { label: 'Policy coverage', value: '94%', icon: ShieldCheck },
  { label: 'Monitored Assets', value: '52 active', icon: Users },
]

export function InfrastructurePage() {
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(initialNodes[4]) // Default to RDS
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [isDragging, setIsDragging] = useState(false)
  const dragStart = useRef({ x: 0, y: 0 })

  const handleMouseDown = (e: MouseEvent) => {
    if ((e.target as HTMLElement).tagName === 'button' || (e.target as HTMLElement).closest('.node-element')) return
    setIsDragging(true)
    dragStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
  }

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return
    setPan({
      x: e.clientX - dragStart.current.x,
      y: e.clientY - dragStart.current.y,
    })
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const zoomIn = () => setZoom((z) => Math.min(z + 0.1, 1.8))
  const zoomOut = () => setZoom((z) => Math.max(z - 0.1, 0.6))
  const resetView = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }



  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-slate-400">Cloud topology</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white">Infrastructure map</h1>
        </div>
        <div className="inline-flex items-center gap-2 rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-2.5 text-sm text-slate-200">
          <Cloud size={16} className="text-primary" />
          AWS / us-east-1
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, icon: Icon }) => (
          <Card key={label} className="p-4 border border-[#1C2633] bg-[#0B0F14] rounded-2xl">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl border border-[#1C2633] bg-[#111720] text-primary">
              <Icon size={18} />
            </div>
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
            <div className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">{value}</div>
          </Card>
        ))}
      </div>

      {/* Viewport Grid layout */}
      <div className="grid gap-6 xl:grid-cols-[1.5fr_0.9fr]">
        {/* Interactive SVG Canvas */}
        <Card className="relative overflow-hidden h-[540px] border border-[#1C2633] bg-[#05070A] rounded-3xl select-none">
          <div className="absolute top-4 left-4 z-25 flex items-center gap-1.5 bg-[#0B0F14]/80 backdrop-blur border border-[#1C2633]/60 rounded-xl p-1 shadow-soft">
            <button
              onClick={zoomIn}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-[#111720] transition"
              title="Zoom In"
            >
              <ZoomIn size={16} />
            </button>
            <button
              onClick={zoomOut}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-[#111720] transition"
              title="Zoom Out"
            >
              <ZoomOut size={16} />
            </button>
            <button
              onClick={resetView}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-[#111720] transition"
              title="Reset View"
            >
              <RotateCcw size={16} />
            </button>
          </div>

          <div className="absolute top-4 right-4 z-25 flex items-center gap-2 bg-[#0B0F14]/60 backdrop-blur px-3 py-1.5 border border-[#1C2633]/40 rounded-xl text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
            <Compass size={12} className="animate-spin" style={{ animationDuration: '4s' }} /> Drag to Pan / Zoom
          </div>

          {/* SVG Map Container */}
          <div
            className="w-full h-full cursor-grab active:cursor-grabbing"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <svg className="w-full h-full">
              <defs>
                <linearGradient id="pathGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#06B6D4" stopOpacity={0.1} />
                </linearGradient>
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#1C2633" />
                </marker>
              </defs>

              {/* Pan & Zoom Transform wrapper */}
              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* 1. Connections / Relationship Paths */}
                {initialNodes.map((source) =>
                  source.connections.map((targetId) => {
                    const target = initialNodes.find((t) => t.id === targetId)
                    if (!target) return null

                    // Generate a curved bezier line path
                    const dx = target.x - source.x
                    const dy = target.y - source.y
                    const cx1 = source.x + dx * 0.1
                    const cy1 = source.y + dy * 0.9
                    const cx2 = source.x + dx * 0.9
                    const cy2 = source.y + dy * 0.1

                    const isHighlight =
                      selectedNode &&
                      (selectedNode.id === source.id || selectedNode.id === target.id)

                    return (
                      <path
                        key={`${source.id}-${targetId}`}
                        d={`M ${source.x} ${source.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${target.x} ${target.y}`}
                        fill="none"
                        stroke={isHighlight ? '#3B82F6' : '#1C2633'}
                        strokeWidth={isHighlight ? 2.5 : 1.5}
                        strokeDasharray={source.status !== 'Healthy' ? '4 4' : undefined}
                        className="transition-all duration-300"
                        markerEnd="url(#arrow)"
                      />
                    )
                  })
                )}

                {/* 2. Topology Nodes */}
                {initialNodes.map((node) => {
                  const isSelected = selectedNode && selectedNode.id === node.id
                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x}, ${node.y})`}
                      className="node-element cursor-pointer group"
                      onClick={() => setSelectedNode(node)}
                    >
                      {/* Active Selector Ring */}
                      {isSelected && (
                        <circle
                          r={34}
                          fill="none"
                          stroke="#3B82F6"
                          strokeWidth={2}
                          className="animate-ping"
                          style={{ animationDuration: '3s' }}
                        />
                      )}

                      {/* Node Shape */}
                      <circle
                        r={25}
                        className={`stroke-2 transition-all ${
                          node.status === 'Healthy'
                            ? 'fill-[#0B0F14] stroke-emerald-500 group-hover:stroke-emerald-400'
                            : node.status === 'Warning'
                              ? 'fill-[#0B0F14] stroke-amber-500 group-hover:stroke-amber-400'
                              : 'fill-[#0B0F14] stroke-rose-500 group-hover:stroke-rose-450'
                        }`}
                      />

                      {/* Inner Icon representation */}
                      <g transform="translate(-8, -8)" className="pointer-events-none text-slate-400">
                        {node.type === 'Storage' && <Database size={16} />}
                        {node.type === 'Compute' && <Server size={16} />}
                        {node.type === 'Security' && <Lock size={16} />}
                        {node.type === 'Identity' && <Lock size={16} />}
                        {node.type === 'Gateway' && <Maximize2 size={16} />}
                        {node.type === 'Balancer' && <GitBranch size={16} />}
                        {node.type === 'Observability' && <Activity size={16} />}
                      </g>

                      {/* Text Label */}
                      <text
                        y={42}
                        textAnchor="middle"
                        className="fill-slate-300 font-sans text-[10px] font-semibold tracking-wide pointer-events-none"
                      >
                        {node.label}
                      </text>
                    </g>
                  )
                })}
              </g>
            </svg>
          </div>
        </Card>

        {/* Node Inspector Side Panel */}
        <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl flex flex-col justify-between h-[540px] overflow-y-auto">
          {selectedNode ? (
            <div className="space-y-6">
              {/* Node Header */}
              <div className="border-b border-[#1C2633]/60 pb-4">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Asset Audit Scanner</span>
                  <Badge
                    variant={
                      selectedNode.status === 'Healthy'
                        ? 'success'
                        : selectedNode.status === 'Warning'
                          ? 'warning'
                          : 'error'
                    }
                  >
                    {selectedNode.status}
                  </Badge>
                </div>
                <h3 className="text-xl font-semibold text-white mt-2">{selectedNode.label}</h3>
                <span className="text-[11px] font-mono text-slate-500 block mt-0.5">Type: {selectedNode.type}</span>
              </div>

              {/* Description */}
              <p className="text-sm text-slate-400 leading-relaxed">{selectedNode.desc}</p>

              {/* Metadata Details */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Configuration variables</h4>
                <div className="space-y-2">
                  {Object.entries(selectedNode.details).map(([key, val]) => (
                    <div key={key} className="flex justify-between items-center rounded-xl border border-[#1C2633]/60 bg-[#111720]/40 px-3 py-2 text-xs">
                      <span className="text-slate-500 font-medium">{key}</span>
                      <span className="text-slate-300 font-mono font-semibold">{val}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Compliance score */}
              <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ShieldCheck size={20} className="text-primary" />
                  <div>
                    <span className="text-xs font-semibold text-slate-300">Policy Adherence</span>
                    <span className="block text-[9px] text-slate-500 mt-0.5">OPA scanned in us-east-1</span>
                  </div>
                </div>
                <span className="text-2xl font-black text-white tracking-tight">{selectedNode.score}%</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 text-sm">
              <Compass size={40} className="text-slate-600 mb-3" />
              Click a resource node in the topology mesh to inspect configurations.
            </div>
          )}

          {/* Action Trigger */}
          {selectedNode && (
            <a
              href="/policies"
              className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl bg-primary hover:bg-blue-600 py-3 text-sm font-bold text-white transition"
            >
              Verify OPA Rules <ArrowRight size={16} />
            </a>
          )}
        </Card>
      </div>

      {/* Grid Features summaries */}
      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="p-4 border border-[#1C2633] bg-[#0B0F14] rounded-2xl">
          <div className="mb-3 flex items-center gap-2 text-primary">
            <Database size={16} />
            <span className="text-sm font-medium text-white">Data plane isolation</span>
          </div>
          <ul className="space-y-2 text-sm text-slate-400">
            <li>• Private subnets restrict db access patterns</li>
            <li>• Encrypted static blocks locked in S3 storage</li>
            <li>• Zero-trust security groups</li>
          </ul>
        </Card>

        <Card className="p-4 border border-[#1C2633] bg-[#0B0F14] rounded-2xl">
          <div className="mb-3 flex items-center gap-2 text-primary">
            <ShieldCheck size={16} />
            <span className="text-sm font-medium text-white">Ingress boundaries</span>
          </div>
          <ul className="space-y-2 text-sm text-slate-400">
            <li>• WAF shield enforces ingress packet scans</li>
            <li>• Multi-zone API instance routing</li>
            <li>• Continuous GuardDuty behavior matching</li>
          </ul>
        </Card>

        <Card className="p-4 border border-[#1C2633] bg-[#0B0F14] rounded-2xl">
          <div className="mb-3 flex items-center gap-2 text-primary">
            <Activity size={16} />
            <span className="text-sm font-medium text-white">Health telemetry</span>
          </div>
          <ul className="space-y-2 text-sm text-slate-400">
            <li>• CloudWatch logs track parameter changes</li>
            <li>• Push-based alerting for configuration drift</li>
            <li>• 90-day compliance evidence trails</li>
          </ul>
        </Card>
      </div>
    </div>
  )
}
