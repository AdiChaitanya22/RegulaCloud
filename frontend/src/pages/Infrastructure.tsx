import { useState, useEffect } from 'react'
import {
  Activity, Cloud, Database, Users, Server, Lock, AlertTriangle
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { request } from '../services/api'
import { useProject } from '../context/ProjectContext'

interface TopologyNode {
  id: string
  address: string
  type: string
  name: string
  provider: string
  module: string | null
  category: string
  region: string
  compliance_status: 'PASS' | 'FAIL' | 'UNKNOWN' | 'NOT_APPLICABLE' | 'UNSUPPORTED'
  supported: boolean
  control_count: number
  failed_control_count: number
  attributes: Record<string, any>
  controls: any[]
}

interface TopologyData {
  project_id: string
  stale: boolean
  status?: string
  message?: string
  resources: TopologyNode[]
  edges: { source: string; target: string; type: string }[]
  coverage: {
    total_resources: number
    supported_resources: number
    unsupported_resources: number
    resource_coverage_percent: number
    resources_passed: number
    resources_failed: number
  }
}

export function InfrastructurePage() {
  const { activeProject } = useProject()
  const [data, setData] = useState<TopologyData | null>(null)
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!activeProject) {
      setData(null)
      setSelectedNode(null)
      return
    }

    const loadTopology = async () => {
      setLoading(true)
      try {
        const res = await request<TopologyData>(`/projects/${activeProject.id}/infrastructure/topology`)
        if (res.data) {
          setData(res.data)
          if (res.data.resources && res.data.resources.length > 0) {
            setSelectedNode(res.data.resources[0])
          }
        }
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    loadTopology()
  }, [activeProject])

  if (!activeProject) {
    return (
      <div className="flex h-[500px] items-center justify-center rounded-3xl border border-[#1C2633] bg-[#0B0F14]">
        <div className="text-center">
          <Cloud size={48} className="mx-auto mb-4 text-slate-600" />
          <h2 className="text-lg font-semibold text-white">Select a Project</h2>
          <p className="mt-2 text-sm text-slate-400">Please select an active project to view its infrastructure topology.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return <div className="text-slate-400">Loading infrastructure native plan...</div>
  }

  if (data?.status === 'NO_EVALUATION' || !data?.resources) {
    return (
      <div className="flex h-[500px] items-center justify-center rounded-3xl border border-[#1C2633] bg-[#0B0F14]">
        <div className="text-center max-w-md">
          <AlertTriangle size={48} className="mx-auto mb-4 text-amber-500" />
          <h2 className="text-lg font-semibold text-white">No Evaluation Found</h2>
          <p className="mt-2 text-sm text-slate-400">{data?.message || 'Run a compliance evaluation first to generate the native infrastructure model.'}</p>
          <a href="/deploy" className="mt-6 inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-bold text-white hover:bg-blue-600">
            Go to Deploy
          </a>
        </div>
      </div>
    )
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PASS': return 'bg-emerald-500/20 text-emerald-500 border-emerald-500/40'
      case 'FAIL': return 'bg-rose-500/20 text-rose-500 border-rose-500/40'
      case 'UNKNOWN': return 'bg-amber-500/20 text-amber-500 border-amber-500/40'
      case 'UNSUPPORTED': return 'bg-slate-700/20 text-slate-400 border-slate-700/40'
      default: return 'bg-[#111720] text-slate-300 border-[#1C2633]'
    }
  }

  const getIcon = (category: string) => {
    switch (category) {
      case 'DATABASE': return <Database size={16} />
      case 'STORAGE': return <Database size={16} />
      case 'COMPUTE': return <Server size={16} />
      case 'SECURITY': return <Lock size={16} />
      case 'IDENTITY': return <Users size={16} />
      default: return <Cloud size={16} />
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-slate-400">Native Plan Intelligence</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white">Infrastructure map</h1>
        </div>
        <div className="flex gap-2">
          {data.stale && (
            <div className="inline-flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-sm font-semibold text-rose-500">
              <AlertTriangle size={16} />
              Evaluation Stale - Artifacts Changed
            </div>
          )}
          <div className="inline-flex items-center gap-2 rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-2.5 text-sm text-slate-200">
            <Cloud size={16} className="text-primary" />
            AWS Native Plan
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="p-4 border border-[#1C2633] bg-[#0B0F14] rounded-2xl">
          <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Total Resources</div>
          <div className="mt-2 text-2xl font-semibold text-white">{data.coverage.total_resources}</div>
        </Card>
        <Card className="p-4 border border-[#1C2633] bg-[#0B0F14] rounded-2xl">
          <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Policy Coverage</div>
          <div className="mt-2 text-2xl font-semibold text-white">{data.coverage.resource_coverage_percent}%</div>
        </Card>
        <Card className="p-4 border border-[#1C2633] bg-[#0B0F14] rounded-2xl">
          <div className="text-xs uppercase tracking-[0.18em] text-emerald-500">Passed Resources</div>
          <div className="mt-2 text-2xl font-semibold text-white">{data.coverage.resources_passed}</div>
        </Card>
        <Card className="p-4 border border-[#1C2633] bg-[#0B0F14] rounded-2xl">
          <div className="text-xs uppercase tracking-[0.18em] text-rose-500">Failed Resources</div>
          <div className="mt-2 text-2xl font-semibold text-white">{data.coverage.resources_failed}</div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl min-h-[500px]">
          <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-wider text-slate-400">Native Infrastructure List</h3>
          <div className="space-y-2">
            {data.resources.map(node => (
              <div 
                key={node.id} 
                onClick={() => setSelectedNode(node)}
                className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition ${
                  selectedNode?.id === node.id 
                    ? 'border-primary bg-[#111720]' 
                    : 'border-[#1C2633] bg-[#0B0F14] hover:bg-[#111720]/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg border ${getStatusColor(node.compliance_status)}`}>
                    {getIcon(node.category)}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">{node.name || node.type}</div>
                    <div className="text-[10px] text-slate-500 font-mono">{node.address}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={node.supported ? (node.compliance_status === 'PASS' ? 'success' : node.compliance_status === 'FAIL' ? 'error' : 'warning') : 'default'}>
                    {node.compliance_status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl flex flex-col justify-between overflow-y-auto">
          {selectedNode ? (
            <div className="space-y-6">
              <div className="border-b border-[#1C2633]/60 pb-4">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{selectedNode.category}</span>
                  <Badge variant={selectedNode.compliance_status === 'PASS' ? 'success' : selectedNode.compliance_status === 'FAIL' ? 'error' : 'default'}>
                    {selectedNode.compliance_status}
                  </Badge>
                </div>
                <h3 className="text-xl font-semibold text-white mt-2">{selectedNode.address}</h3>
                <span className="text-[11px] font-mono text-slate-500 block mt-0.5">Type: {selectedNode.type}</span>
              </div>

              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Resource Attributes</h4>
                <div className="space-y-2 bg-[#111720] rounded-xl p-3 max-h-48 overflow-y-auto border border-[#1C2633]">
                  <pre className="text-[10px] text-slate-300 font-mono">
                    {JSON.stringify(selectedNode.attributes, null, 2)}
                  </pre>
                </div>
              </div>
              
              {selectedNode.supported && (
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">OPA Controls</h4>
                  {selectedNode.controls.length > 0 ? (
                    selectedNode.controls.map((c, i) => (
                      <div key={i} className="flex justify-between items-center bg-[#111720] p-2 rounded border border-[#1C2633]">
                        <span className="text-xs font-mono text-slate-300">{c.control_id}</span>
                        <Badge variant={c.status === 'PASS' ? 'success' : 'error'}>{c.status}</Badge>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-500">No applicable controls evaluated.</div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 text-sm">
              <Activity size={40} className="text-slate-600 mb-3" />
              Click a resource node to view details
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
