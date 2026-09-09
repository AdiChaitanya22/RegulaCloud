import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertTriangle,
  CloudCog,
  Database,
  FileText,
  LayoutGrid,
  Lock,
  LogOut,
  Rocket,
  Settings,
  ShieldCheck,
  Sparkles,
  Bell,
  Search,
  X,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { CommandPalette } from '../ui/command-palette'
import { useAuth } from '../../context/AuthContext'

interface AppShellProps {
  children: ReactNode
}

const navigation = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutGrid },
  { label: 'Projects', to: '/projects', icon: CloudCog },
  { label: 'Deployments', to: '/deployments', icon: Rocket },
  { label: 'Infrastructure', to: '/infrastructure', icon: Database },
  { label: 'Compliance', to: '/compliance', icon: ShieldCheck },
  { label: 'Policies', to: '/policies', icon: FileText },
  { label: 'Security Scanner', to: '/security', icon: Lock },
  { label: 'AI Assistant', to: '/ai-assistant', icon: Sparkles },
  { label: 'Audit Logs', to: '/audit', icon: AlertTriangle },
  { label: 'Reports', to: '/reports', icon: FileText },
  { label: 'Settings', to: '/settings', icon: Settings },
]

export function AppShell({ children }: AppShellProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [showNotifications, setShowNotifications] = useState(false)
  const [notifications, setNotifications] = useState([
    { id: 'not-1', text: 'Security drift on rds-postgres-01: publicly_accessible set to true', type: 'error', time: '10m ago' },
    { id: 'not-2', text: 'ISO 27001 ISMS Report completed compilation', type: 'info', time: '1h ago' },
  ])

  const clearNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  // Derive initials from username (up to 2 chars, uppercase)
  const initials = user?.username
    ? user.username.slice(0, 2).toUpperCase()
    : '?'
  const displayName = user?.username ?? 'Unknown'
  const displayRole = user?.role ?? ''

  return (
    <div className="min-h-screen bg-[#05070A] text-slate-100 relative">
      <CommandPalette />
      <div className="flex min-h-screen bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.15),_transparent_25%)]">
        <aside className="hidden w-72 border-r border-[#1C2633] bg-[#0B0F14]/90 p-5 lg:flex lg:flex-col">
          <Link to="/dashboard" className="mb-8 flex items-center gap-3 px-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#1C2633] bg-[#111720] text-primary">
              <ShieldCheck size={18} />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-[0.18em] text-slate-400 uppercase">Regu</div>
              <div className="text-lg font-semibold text-white">Cloud</div>
            </div>
          </Link>

          <nav className="space-y-1">
            {navigation.map(({ label, to, icon: Icon }) => (
              <NavLink
                key={label}
                to={to}
                className={({ isActive }) =>
                  `flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition ${
                    isActive
                      ? 'border-primary/30 bg-[#111720] text-white'
                      : 'border-transparent text-slate-300 hover:border-[#1C2633] hover:bg-[#111720]'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon size={16} className={isActive ? 'text-primary' : 'text-slate-400'} />
                    {label}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto rounded-xl border border-[#1C2633] bg-[#111720] p-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-bold">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-white truncate">{displayName}</div>
                <div className="text-xs text-slate-400 uppercase tracking-wide">{displayRole}</div>
              </div>
              <button
                onClick={handleLogout}
                title="Sign out"
                className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-500 hover:bg-[#1C2633] hover:text-rose-400 transition shrink-0"
              >
                <LogOut size={14} />
              </button>
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="border-b border-[#1C2633] bg-[#0B0F14]/80 backdrop-blur relative z-30">
            <div className="flex items-center justify-between px-4 py-3 sm:px-6">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#1C2633] bg-[#111720] lg:hidden">
                  <LayoutGrid size={18} className="text-primary" />
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
                    Overview
                  </div>
                  <div className="text-sm text-slate-300">Production Environment</div>
                </div>
              </div>

              <div className="flex items-center gap-3 relative">
                {/* Search Trigger */}
                <button
                  onClick={() => window.dispatchEvent(new CustomEvent('open-command-palette'))}
                  className="inline-flex items-center gap-2 rounded-xl border border-[#1C2633] bg-[#111720] px-3.5 py-2 text-xs font-semibold text-slate-300 hover:bg-[#1C2633] transition"
                  title="Search commands (Ctrl+K)"
                >
                  <Search size={14} className="text-slate-500" />
                  <span className="hidden sm:inline">Search (Ctrl+K)</span>
                </button>

                {/* Notifications Bell */}
                <div className="relative">
                  <button
                    onClick={() => setShowNotifications(!showNotifications)}
                    className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-[#1C2633] bg-[#111720] text-slate-300 hover:bg-[#1C2633] transition"
                  >
                    <Bell size={16} />
                    {notifications.length > 0 && (
                      <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[8px] font-bold text-white animate-pulse">
                        {notifications.length}
                      </span>
                    )}
                  </button>

                  {/* Dropdown panel */}
                  <AnimatePresence>
                    {showNotifications && (
                      <>
                        <div className="fixed inset-0 z-40" onClick={() => setShowNotifications(false)} />
                        <motion.div
                          initial={{ opacity: 0, y: 10, scale: 0.95 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: 10, scale: 0.95 }}
                          transition={{ duration: 0.15 }}
                          className="absolute right-0 mt-2 w-80 rounded-2xl border border-[#1C2633] bg-[#0B0F14] p-4 shadow-soft z-50 space-y-3"
                        >
                          <div className="flex items-center justify-between border-b border-[#1C2633]/60 pb-2">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                              System Notifications
                            </span>
                            {notifications.length > 0 && (
                              <button
                                onClick={() => setNotifications([])}
                                className="text-[10px] font-semibold text-primary hover:underline"
                              >
                                Clear all
                              </button>
                            )}
                          </div>

                          {notifications.length === 0 ? (
                            <div className="py-4 text-center text-xs text-slate-500 font-medium">
                              All alerts verified green.
                            </div>
                          ) : (
                            <div className="space-y-2 max-h-60 overflow-y-auto">
                              {notifications.map((not) => (
                                <div
                                  key={not.id}
                                  className="flex items-start gap-2.5 rounded-xl border border-[#1C2633]/60 bg-[#111720]/40 p-2.5 hover:bg-[#111720]/80 transition relative group"
                                >
                                  <div
                                    className={`mt-0.5 h-2 w-2 rounded-full shrink-0 ${
                                      not.type === 'error' ? 'bg-rose-500' : 'bg-primary'
                                    }`}
                                  />
                                  <div className="flex-1 text-[11px] text-slate-350 pr-4 leading-4">
                                    {not.text}
                                    <span className="block text-[9px] text-slate-500 mt-1">{not.time}</span>
                                  </div>
                                  <button
                                    onClick={() => clearNotification(not.id)}
                                    className="absolute top-2 right-2 text-slate-500 hover:text-white"
                                  >
                                    <X size={12} />
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}
                        </motion.div>
                      </>
                    )}
                  </AnimatePresence>
                </div>

                <div className="h-9 w-9 rounded-full border border-primary/20 bg-primary/10 flex items-center justify-center text-xs font-bold text-primary cursor-default uppercase">
                  {initials}
                </div>
              </div>
            </div>
          </header>

          <motion.main
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
            className="flex-1 p-4 sm:p-6"
          >
            {children}
          </motion.main>
        </div>
      </div>
    </div>
  )
}
