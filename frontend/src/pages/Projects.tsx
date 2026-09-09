import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Cloud,
  Plus,
  Search,
  SlidersHorizontal,
  Trash2,
  X,
  ShieldCheck,
  User,
  MapPin,
  Calendar,
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { Dialog, DialogContent } from '../components/ui/dialog'
import { Select } from '../components/ui/select'
import { projectService } from '../services/projectService'
import type { Project, CloudProvider } from '../types'

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)

  // Filter/Sort State
  const [search, setSearch] = useState('')
  const [providerFilter, setProviderFilter] = useState('All')
  const [sortBy, setSortBy] = useState('score') // 'score' | 'name'

  // Create Project State
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newProvider, setNewProvider] = useState<CloudProvider>('AWS')
  const [newRegion, setNewRegion] = useState('')
  const [newOwner, setNewOwner] = useState('')
  const [newRegScope, setNewRegScope] = useState<string[]>([])
  const [infraFile, setInfraFile] = useState<File | null>(null)
  const [infraHcl, setInfraHcl] = useState('')
  const [appFile, setAppFile] = useState<File | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  // Details Drawer State
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)

  // Load Projects
  useEffect(() => {
    async function load() {
      setIsLoading(true)
      const data = await projectService.getProjects()
      setProjects(data)
      setIsLoading(false)
    }
    load()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName || !newRegion || !newOwner) return

    setIsCreating(true)
    try {
      const newProj = await projectService.createProject({
        name: newName,
        cloudProvider: newProvider,
        region: newRegion,
        complianceScore: 100, // New projects start clean
        lastDeployment: 'Never deployed',
        status: 'Protected',
        owner: newOwner,
      })

      if (newRegScope.length > 0) {
        await projectService.updateProject(newProj.id, { regulatory_scope: newRegScope })
      }

      if (infraFile || infraHcl) {
        await projectService.uploadInfrastructure(newProj.id, infraFile || undefined, infraHcl)
      }

      if (appFile) {
        await projectService.uploadApplication(newProj.id, appFile)
      }

      setProjects((prev) => [...prev, newProj])
      setIsCreateOpen(false)

      // Reset Form
      setNewName('')
      setNewRegion('')
      setNewOwner('')
      setNewRegScope([])
      setInfraFile(null)
      setInfraHcl('')
      setAppFile(null)
    } finally {
      setIsCreating(false)
    }
  }

  const handleDelete = async (id: string) => {
    const confirmed = window.confirm('Are you sure you want to delete this project?')
    if (!confirmed) return

    const success = await projectService.deleteProject(id)
    if (success) {
      setProjects((prev) => prev.filter((p) => p.id !== id))
      setSelectedProject(null)
    }
  }

  // Filter & Sort logic
  const filteredProjects = projects
    .filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
    .filter((p) => (providerFilter === 'All' ? true : p.cloudProvider === providerFilter))
    .sort((a, b) => {
      if (sortBy === 'score') {
        return b.complianceScore - a.complianceScore
      }
      return a.name.localeCompare(b.name)
    })

  return (
    <div className="space-y-6 relative min-h-[80vh]">
      {/* Page Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-slate-400">Environment Registry</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white">Projects</h1>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="inline-flex items-center gap-2 rounded-xl bg-primary hover:bg-blue-600 px-5 py-3 text-sm font-bold text-white transition self-start"
        >
          <Plus size={16} /> Create project
        </button>
      </div>

      {/* Filters Toolbar */}
      <Card className="p-4 flex flex-col md:flex-row gap-4 items-center justify-between border border-[#1C2633] bg-[#0B0F14]">
        {/* Search */}
        <div className="relative w-full md:max-w-xs">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects..."
            className="w-full rounded-xl border border-[#1C2633] bg-[#111720] pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
            <SlidersHorizontal size={14} /> Filter:
          </div>

          {/* Cloud Provider Select */}
          <Select
            className="w-32"
            value={providerFilter}
            onChange={(val) => setProviderFilter(val)}
            options={[
              { label: 'All Clouds', value: 'All' },
              { label: 'AWS', value: 'AWS' },
              { label: 'Azure', value: 'Azure' },
              { label: 'GCP', value: 'GCP' },
            ]}
          />

          {/* Sort By Select */}
          <Select
            className="w-40"
            value={sortBy}
            onChange={(val) => setSortBy(val)}
            options={[
              { label: 'Sort by Score', value: 'score' },
              { label: 'Sort by Name', value: 'name' },
            ]}
          />
        </div>
      </Card>

      {/* Projects Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3].map((n) => (
            <Card key={n} className="p-5 h-44 border border-[#1C2633] bg-[#0B0F14] animate-pulse">
              <div className="w-full h-full bg-[#111720]/45 rounded-xl" />
            </Card>
          ))}
        </div>
      ) : filteredProjects.length === 0 ? (
        <Card className="p-12 text-center border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
          <p className="text-slate-400 font-medium">No projects found matching the filter criteria.</p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <AnimatePresence>
            {filteredProjects.map((project) => (
              <motion.div
                key={project.id}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                onClick={() => setSelectedProject(project)}
                className="cursor-pointer"
              >
                <Card className="p-5 h-full hover:border-primary/50 transition flex flex-col justify-between border border-[#1C2633] bg-[#0B0F14] hover:shadow-soft">
                  <div>
                    <div className="mb-4 flex items-start justify-between">
                      <h2 className="text-lg font-medium text-white line-clamp-1">{project.name}</h2>
                      <span
                        className={`rounded-full border px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                          project.status === 'Protected'
                            ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-600'
                            : project.status === 'Review'
                              ? 'border-amber-500/25 bg-amber-500/10 text-amber-600'
                              : 'border-rose-500/25 bg-rose-500/10 text-rose-500'
                        }`}
                      >
                        {project.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-xs text-slate-400 mb-4">
                      <div>
                        <span className="block text-slate-500">Provider</span>
                        <span className="font-semibold text-slate-200 mt-0.5 block">{project.cloudProvider}</span>
                      </div>
                      <div>
                        <span className="block text-slate-500">Region</span>
                        <span className="font-semibold text-slate-200 mt-0.5 block">{project.region}</span>
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-[#1C2633]/60 pt-4 flex items-center justify-between">
                    <div>
                      <span className="block text-[10px] text-slate-500 uppercase tracking-wider">Compliance</span>
                      <span className="text-2xl font-bold text-white tracking-tight">{project.complianceScore}%</span>
                    </div>
                    <span className="text-xs text-slate-500 font-medium">{project.lastDeployment}</span>
                  </div>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Create Project Modal */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent title="Create Project">
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Project Name</label>
              <input
                type="text"
                required
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Healthcare Platform"
                className="w-full rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Cloud Provider</label>
                <Select
                  value={newProvider}
                  onChange={(val) => setNewProvider(val as CloudProvider)}
                  options={[
                    { label: 'AWS', value: 'AWS' },
                    { label: 'Azure', value: 'Azure' },
                    { label: 'GCP', value: 'GCP' },
                  ]}
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Region</label>
                <input
                  type="text"
                  required
                  value={newRegion}
                  onChange={(e) => setNewRegion(e.target.value)}
                  placeholder="e.g. us-east-1"
                  className="w-full rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Owner Team</label>
              <input
                type="text"
                required
                value={newOwner}
                onChange={(e) => setNewOwner(e.target.value)}
                placeholder="e.g. Security Lead"
                className="w-full rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Regulatory Scope</label>
              <Select
                value={newRegScope[0] || ''}
                onChange={(val) => setNewRegScope([val])}
                options={[
                  { label: 'None', value: '' },
                  { label: 'DPDPA 2023', value: 'DPDPA-2023' },
                  { label: 'DPDP Rules 2025', value: 'DPDPR-2025' },
                  { label: 'CERT-In Directions 2022', value: 'CERTIN-2022' },
                ]}
              />
            </div>

            <div className="border-t border-[#1C2633] pt-4 mt-4">
              <h3 className="text-sm font-bold text-white mb-3">Workload Artifacts (Optional)</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">Infrastructure (Terraform .tf or .zip)</label>
                  <input type="file" onChange={(e) => setInfraFile(e.target.files?.[0] || null)} className="text-xs text-slate-400 mb-2 w-full" accept=".tf,.zip" />
                  <span className="block text-[10px] text-slate-500 mb-1">OR paste HCL code:</span>
                  <textarea
                    value={infraHcl}
                    onChange={(e) => setInfraHcl(e.target.value)}
                    placeholder="paste terraform code here..."
                    rows={3}
                    className="w-full rounded-xl border border-[#1C2633] bg-[#111720] px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-primary"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">Application Source (.zip)</label>
                  <input type="file" onChange={(e) => setAppFile(e.target.files?.[0] || null)} className="text-xs text-slate-400 w-full" accept=".zip" />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isCreating}
              className="w-full rounded-xl bg-primary hover:bg-blue-600 py-3 text-sm font-bold text-white transition mt-2 disabled:opacity-50"
            >
              {isCreating ? 'Creating & Uploading...' : 'Create Project'}
            </button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Project Details Sidebar Drawer */}
      <AnimatePresence>
        {selectedProject && (
          <div className="fixed inset-0 z-50 flex justify-end">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedProject(null)}
              className="absolute inset-0 bg-black"
            />

            {/* Drawer */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="relative w-full max-w-md h-full bg-[#0B0F14] border-l border-[#1C2633] shadow-soft z-10 flex flex-col justify-between"
            >
              <div className="p-6 overflow-y-auto space-y-6">
                {/* Drawer Header */}
                <div className="flex items-start justify-between border-b border-[#1C2633]/60 pb-4">
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Project Audit View</span>
                    <h2 className="text-xl font-semibold text-white mt-1">{selectedProject.name}</h2>
                  </div>
                  <button
                    onClick={() => setSelectedProject(null)}
                    className="rounded-lg border border-[#1C2633] bg-[#111720] p-1.5 text-slate-400 hover:text-white"
                  >
                    <X size={16} />
                  </button>
                </div>

                {/* Framework Score */}
                <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <ShieldCheck size={24} className="text-primary" />
                    <div>
                      <span className="text-xs font-semibold text-slate-300">Continuous Compliance</span>
                      <span className="block text-[10px] text-slate-500 mt-0.5">Scanned against 184 OPA rules</span>
                    </div>
                  </div>
                  <span className="text-3xl font-black text-white tracking-tight">{selectedProject.complianceScore}%</span>
                </div>

                {/* Metadata List */}
                <div className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Asset Parameters</h3>

                  <div className="space-y-2">
                    <div className="flex items-center gap-3 rounded-xl border border-[#1C2633] bg-[#111720]/40 px-3 py-2.5 text-sm">
                      <Cloud size={16} className="text-slate-500" />
                      <div className="flex-1 flex justify-between">
                        <span className="text-slate-400">Cloud Provider</span>
                        <span className="font-semibold text-slate-200">{selectedProject.cloudProvider}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 rounded-xl border border-[#1C2633] bg-[#111720]/40 px-3 py-2.5 text-sm">
                      <MapPin size={16} className="text-slate-500" />
                      <div className="flex-1 flex justify-between">
                        <span className="text-slate-400">Region Zone</span>
                        <span className="font-semibold text-slate-200">{selectedProject.region}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 rounded-xl border border-[#1C2633] bg-[#111720]/40 px-3 py-2.5 text-sm">
                      <User size={16} className="text-slate-500" />
                      <div className="flex-1 flex justify-between">
                        <span className="text-slate-400">Owner Team</span>
                        <span className="font-semibold text-slate-200">{selectedProject.owner}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 rounded-xl border border-[#1C2633] bg-[#111720]/40 px-3 py-2.5 text-sm">
                      <Calendar size={16} className="text-slate-500" />
                      <div className="flex-1 flex justify-between">
                        <span className="text-slate-400">Last Rollout</span>
                        <span className="font-semibold text-slate-200 text-xs">{selectedProject.lastDeployment}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="p-6 border-t border-[#1C2633]/60 bg-[#111720]/20 flex gap-3">
                <button
                  onClick={() => handleDelete(selectedProject.id)}
                  className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm font-bold text-rose-500 hover:bg-rose-500/20 transition"
                >
                  <Trash2 size={16} /> Delete Project
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
