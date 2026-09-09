import { useState, type FormEvent } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShieldCheck, AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // After login, redirect to the page the user was trying to reach, or /dashboard
  const from = (location.state as { from?: string })?.from || '/dashboard'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) return

    setError(null)
    setIsLoading(true)
    try {
      const result = await login(username.trim(), password)
      if (result.success) {
        navigate(from, { replace: true })
      } else {
        setError(result.error || 'Invalid username or password.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#05070A] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Ambient glow matching existing design */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(59,130,246,0.12),_transparent_60%)]" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative w-full max-w-sm"
      >
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#1C2633] bg-[#111720] text-primary shadow-lg">
              <ShieldCheck size={20} />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400 font-semibold">Regu</div>
              <div className="text-lg font-bold text-white leading-tight">Cloud</div>
            </div>
          </Link>
          <div className="text-center mt-1">
            <h1 className="text-xl font-semibold text-white tracking-tight">Sign in to RegulaCloud</h1>
            <p className="text-xs text-slate-500 mt-1">Regulation-Aware Cloud Compliance Platform</p>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-[#1C2633] bg-[#0B0F14]/90 p-7 shadow-2xl backdrop-blur">

          {/* Error Banner */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-5 flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-3 text-xs text-rose-300"
            >
              <AlertCircle size={14} className="shrink-0 mt-0.5 text-rose-400" />
              <span>{error}</span>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label
                htmlFor="rc-username"
                className="block text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400 mb-2"
              >
                Username
              </label>
              <input
                id="rc-username"
                type="text"
                autoComplete="username"
                autoFocus
                required
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value)
                  if (error) setError(null)
                }}
                placeholder="Enter your username"
                className="w-full rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-3 text-sm text-slate-200 placeholder-slate-600
                           focus:outline-none focus:border-primary/70 focus:ring-1 focus:ring-primary/20 transition"
              />
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="rc-password"
                className="block text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400 mb-2"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="rc-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    if (error) setError(null)
                  }}
                  placeholder="Enter your password"
                  className="w-full rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-3 pr-11 text-sm text-slate-200 placeholder-slate-600
                             focus:outline-none focus:border-primary/70 focus:ring-1 focus:ring-primary/20 transition"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading || !username.trim() || !password}
              className="mt-2 w-full rounded-xl bg-primary hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed
                         py-3 text-sm font-bold text-white transition flex items-center justify-center gap-2 shadow-lg shadow-blue-500/10"
            >
              {isLoading ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-[10px] text-slate-600">
          India DPDPA 2023 &amp; CERT-In 2022 Compliance Platform
        </p>
      </motion.div>
    </div>
  )
}
