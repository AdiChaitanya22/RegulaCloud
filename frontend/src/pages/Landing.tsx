import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  CheckCircle2,
  Cloud,
  FileCheck2,
  Lock,
  Shield,
  Sparkles,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import './Landing.css'

// Import Dashboard Sub-pages to stack them in a single-page parallax view
import { DeployPage } from './Deploy'
import { InfrastructurePage } from './Infrastructure'
import { AIAssistantPage } from './AIAssistant'
import { AuditLogsPage } from './AuditLogs'
import { ReportsPage } from './Reports'
import { SettingsPage } from './Settings'

const pipeline = [
  'USER',
  'AI REQUIREMENT ANALYSIS',
  'TERRAFORM',
  'OPA POLICY ENGINE',
  'SECURITY SCANNER',
  'CLOUD',
]

const features = [
  { title: 'AI Requirement Analysis', icon: Sparkles },
  { title: 'Policy-as-Code', icon: Shield },
  { title: 'Infrastructure-as-Code', icon: Cloud },
  { title: 'Security Scanning', icon: Lock },
  { title: 'Automated Compliance', icon: FileCheck2 },
  { title: 'Auditability', icon: CheckCircle2 },
]

const metrics = [
  { label: 'Policy Coverage', value: '98.4%' },
  { label: 'Threat Detection', value: '3.2s' },
  { label: 'Compliance Drift', value: '0.4%' },
]

export function LandingPage() {
  // Preloading States
  const [isLoading, setIsLoading] = useState(true)
  const [loadedCount, setLoadedCount] = useState(0)
  const [statusMessage, setStatusMessage] = useState('Initializing sequence matrix...')
  
  // Element Refs
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const imagesRef = useRef<HTMLImageElement[]>([])
  const currentFrameRef = useRef(0)
  const targetFrameRef = useRef(0)
  const isLoadedRef = useRef(false)
  
  const totalFrames = 300
  const circleRadius = 70
  const circumference = 2 * Math.PI * circleRadius // ~439.82

  // Loader Subtitles depending on progress
  const getStatusMessage = (percent: number) => {
    if (percent < 20) return 'Initializing sequence matrix...'
    if (percent < 45) return 'Extracting frame vectors...'
    if (percent < 70) return 'Caching buffer allocations...'
    if (percent < 95) return 'Calibrating inertial scroll sensors...'
    return 'Synchronization complete!'
  }

  // Preload Images Effect
  useEffect(() => {
    document.body.classList.add('loading')
    let localLoaded = 0
    const images: HTMLImageElement[] = []

    const handleSingleLoaded = () => {
      localLoaded++
      setLoadedCount(localLoaded)
      
      const percent = Math.floor((localLoaded / totalFrames) * 100)
      setStatusMessage(getStatusMessage(percent))

      if (localLoaded === totalFrames) {
        imagesRef.current = images
        isLoadedRef.current = true
        setIsLoading(false)
        document.body.classList.remove('loading')
      }
    }

    const frameIndexFunc = (index: number) => 
      `/frames/frame_${index.toString().padStart(4, '0')}.png`

    for (let i = 1; i <= totalFrames; i++) {
      const img = new Image()
      img.onload = handleSingleLoaded
      img.onerror = () => {
        console.warn(`Frame ${i} could not be loaded. Substituting...`)
        handleSingleLoaded()
      }
      img.src = frameIndexFunc(i)
      images.push(img)
    }

    // Clean up
    return () => {
      document.body.classList.remove('loading')
    }
  }, [])

  // Canvas Sizing and Render Loop Effect
  useEffect(() => {
    if (isLoading || !isLoadedRef.current) return

    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationFrameId: number

    // Sizing Function
    const resizeCanvas = () => {
      const w = window.innerWidth
      const h = window.innerHeight
      const dpr = window.devicePixelRatio || 1

      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.scale(dpr, dpr)

      // Initial redraw on resize
      const frameIndex = Math.min(totalFrames - 1, Math.max(0, Math.round(currentFrameRef.current)))
      const img = imagesRef.current[frameIndex]
      if (img) {
        drawImageCover(img, ctx, w, h)
      }
    }

    // Centered Cover Sizing Drawing Routine - Upscaled to 2.6x
    const drawImageCover = (
      img: HTMLImageElement, 
      context: CanvasRenderingContext2D, 
      w: number, 
      h: number
    ) => {
      if (!img.complete || img.naturalWidth === 0) return

      const imgWidth = img.naturalWidth
      const imgHeight = img.naturalHeight
      const imgRatio = imgWidth / imgHeight
      const screenRatio = w / h

      let drawWidth, drawHeight, x, y
      const zoomFactor = 2.6 // Upscaled scroll animation to cover full page dynamically

      if (screenRatio > imgRatio) {
        drawWidth = w * zoomFactor
        drawHeight = (w / imgRatio) * zoomFactor
      } else {
        drawHeight = h * zoomFactor
        drawWidth = (h * imgRatio) * zoomFactor
      }

      x = (w - drawWidth) / 2
      y = (h - drawHeight) / 2

      context.clearRect(0, 0, w, h)
      context.drawImage(img, x, y, drawWidth, drawHeight)
    }

    // Scroll Map Callback
    const handleScroll = () => {
      const scrollTop = window.scrollY
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight
      const scrollPercent = maxScroll <= 0 ? 0 : scrollTop / maxScroll
      targetFrameRef.current = scrollPercent * (totalFrames - 1)
    }

    // Easing Animation Frame Loop
    const updateLoop = () => {
      const ease = 0.08
      const diff = targetFrameRef.current - currentFrameRef.current

      if (Math.abs(diff) > 0.001) {
        currentFrameRef.current += diff * ease
      } else {
        currentFrameRef.current = targetFrameRef.current
      }

      const frameIndex = Math.min(totalFrames - 1, Math.max(0, Math.round(currentFrameRef.current)))
      const activeImg = imagesRef.current[frameIndex]

      if (activeImg) {
        drawImageCover(activeImg, ctx, window.innerWidth, window.innerHeight)
      }

      animationFrameId = requestAnimationFrame(updateLoop)
    }

    // Setup Listeners
    window.addEventListener('resize', resizeCanvas)
    window.addEventListener('scroll', handleScroll)

    // Run Initializations
    resizeCanvas()
    animationFrameId = requestAnimationFrame(updateLoop)

    // Cleanup
    return () => {
      window.removeEventListener('resize', resizeCanvas)
      window.removeEventListener('scroll', handleScroll)
      cancelAnimationFrame(animationFrameId)
    }
  }, [isLoading])

  // Loader Ring Dash Offset math
  const percent = Math.floor((loadedCount / totalFrames) * 100)
  const strokeOffset = circumference - (percent / 100) * circumference

  return (
    <div className="min-h-screen bg-transparent text-slate-900 scroll-wrapper">
      
      {/* Premium Cinematic Loader Overlay */}
      <div id="loader" className={`loader-overlay ${!isLoading ? 'loaded' : ''}`}>
        <div className="loader-content">
          <div className="spinner-container">
            <svg className="progress-ring" width="160" height="160">
              <circle className="progress-ring-bg" strokeWidth="6" fill="transparent" r="70" cx="80" cy="80" />
              <circle 
                className="progress-ring-fg" 
                stroke="url(#loaderGradient)" 
                strokeWidth="8" 
                fill="transparent" 
                r="70" 
                cx="80" 
                cy="80" 
                style={{ strokeDashoffset: strokeOffset }}
              />
              <defs>
                <linearGradient id="loaderGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#3b82f6" />
                  <stop offset="50%" stopColor="#8b5cf6" />
                  <stop offset="100%" stopColor="#ec4899" />
                </linearGradient>
              </defs>
            </svg>
            <div className="progress-text">{percent}%</div>
          </div>
          <div className="loader-details">
            <h2 className="loader-title">SYNCHRONIZING TIMELINE</h2>
            <p className="loader-subtitle">{statusMessage}</p>
            <div className="loader-counter">
              <span id="loaded-count">{loadedCount}</span> <span className="divider">/</span> <span>{totalFrames}</span>
            </div>
          </div>
        </div>
      </div>

      {/* The Fixed Drawing Canvas */}
      <canvas ref={canvasRef} id="animation-canvas" />

      {/* Scroll container content - Expands to full screen width */}
      <div className="w-full">
        
        {/* Floating Capsule Header - Centered inside container */}
        <div className="w-full max-w-[1440px] mx-auto px-6 sm:px-8 lg:px-10 pt-4">
          <header className="mb-0 flex items-center justify-between main-header">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-primary logo-icon">
                <Shield size={20} />
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.22em] text-slate-400 logo-prefix">Regu</div>
                <div className="text-xl font-bold text-white logo-suffix">Cloud</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Link 
                to="/login" 
                className="rounded-xl border border-white/15 bg-white/5 px-5 py-2.5 text-sm font-semibold transition duration-200 btn-signin"
              >
                Sign in
              </Link>
            </div>
          </header>
        </div>

        {/* Hero Section - Full bleed glass card */}
        <section className="relative overflow-hidden border-b border-slate-200/90 hero-section-wrapper glass-card w-full bg-white/75 backdrop-blur-md">
          <div className="max-w-[1440px] mx-auto px-6 sm:px-8 lg:px-10 relative z-10">
            <div className="radial-glow" />

            <div className="relative z-10 max-w-3xl">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-100 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-slate-700 badge">
                <CheckCircle2 size={15} className="text-emerald-500" />
                Regulation-aware deployment
              </div>
              <h1 className="max-w-4xl text-5xl font-extrabold tracking-[-0.04em] text-slate-900 sm:text-6xl lg:text-7xl leading-tight hero-title">
                Deploy Cloud Infrastructure.
                <span className="mt-3 block text-slate-950 font-extrabold highlight">Stay Regulation-Aware.</span>
              </h1>
              <p className="mt-8 max-w-2xl text-lg text-slate-955 sm:text-xl font-semibold leading-relaxed hero-subtitle">
                AI-assisted infrastructure deployment with automated security, policy, and regulatory validation.
              </p>

              <div className="mt-10 flex flex-wrap gap-4 hero-buttons">
                <a
                  href="#deploy"
                  className="inline-flex items-center gap-2 rounded-xl bg-primary hover:bg-blue-600 px-6 py-4 text-base font-bold text-white transition hover:shadow-lg hover:shadow-blue-500/20 btn"
                >
                  START DEPLOYMENT <ArrowRight size={18} />
                </a>
                <a
                  href="#infrastructure"
                  className="rounded-xl border border-slate-200 bg-slate-100 px-6 py-4 text-base font-bold text-slate-700 hover:bg-slate-200 hover:text-slate-900 transition btn btn-secondary"
                >
                  EXPLORE ARCHITECTURE
                </a>
              </div>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.15 }}
              className="relative z-10 mt-14 border-t border-slate-200 pt-8 pipeline-wrapper"
            >
              <div className="flex flex-wrap items-center justify-between gap-4 text-xs font-semibold uppercase tracking-[0.18em] text-slate-600 pipeline-container">
                {pipeline.map((step, index) => (
                  <div key={step} className="flex items-center gap-3 pipeline-step">
                    <span className="rounded-lg border border-slate-200 bg-slate-100 px-3 py-2 text-[10px] text-slate-700 font-bold step-tag">
                      {step}
                    </span>
                    {index < pipeline.length - 1 && <span className="text-slate-400 text-sm font-bold pipeline-arrow">&rarr;</span>}
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </section>

        {/* Features Section - Full bleed glass card */}
        <section className="features-section-wrapper relative overflow-hidden border-b border-slate-200/90 glass-card w-full bg-white/80 backdrop-blur-md">
          <div className="max-w-[1440px] mx-auto px-6 sm:px-8 lg:px-10">
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {features.map(({ title, icon: Icon }) => (
                <motion.div
                  key={title}
                  whileHover={{ y: -4 }}
                  className="rounded-3xl border border-slate-200/90 bg-white/95 p-8 shadow-md hover:border-blue-400/30 hover:shadow-lg transition duration-200 feature-card"
                >
                  <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-blue-600 feature-icon">
                    <Icon size={20} />
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 feature-title">{title}</h3>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Compliance Stats Section - Full bleed glass card */}
        <section className="compliance-section-wrapper relative overflow-hidden border-b border-slate-200/90 glass-card w-full bg-white/75 backdrop-blur-md">
          <div className="max-w-[1440px] mx-auto px-6 sm:px-8 lg:px-10 compliance-card">
            <div className="flex items-center justify-between compliance-header">
              <h2 className="text-2xl font-extrabold text-slate-900 section-title">Live compliance overview</h2>
              <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-emerald-700 bg-emerald-50 border border-emerald-100 px-3 py-1 rounded-full status-badge">
                Healthy
              </span>
            </div>

            <div className="grid gap-6 md:grid-cols-3 mt-8 metrics-grid">
              {metrics.map(({ label, value }) => (
                <div key={label} className="rounded-2xl border border-slate-200 bg-slate-50 p-5 metric-card">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500 font-semibold metric-label">{label}</div>
                  <div className="mt-3 text-3xl font-extrabold tracking-[-0.04em] text-slate-900 metric-value">{value}</div>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5 progress-bar-wrapper">
              <div className="mb-3 flex items-center justify-between text-sm font-semibold text-slate-700 progress-labels">
                <span>Regional policy alignment</span>
                <span className="font-bold text-emerald-600 progress-percentage-label">94%</span>
              </div>
              <div className="h-3 rounded-full bg-slate-200 overflow-hidden alignment-bar-track">
                <div 
                  className="h-3 rounded-full bg-gradient-to-r from-primary to-emerald-500 alignment-bar-fill" 
                  style={{ width: '94%' }} 
                />
              </div>
            </div>
          </div>
        </section>

        {/* Deploy Section - Full bleed glass card */}
        <section id="deploy" className="deploy-section-wrapper relative overflow-hidden border-b border-slate-200/90 glass-card w-full bg-white/80 backdrop-blur-md">
          <div className="max-w-[1440px] mx-auto px-6 sm:px-8 lg:px-10">
            <DeployPage />
          </div>
        </section>

        {/* Infrastructure Section - Full bleed glass card */}
        <section id="infrastructure" className="features-section-wrapper relative overflow-hidden border-b border-slate-200/90 glass-card w-full bg-white/75 backdrop-blur-md">
          <div className="max-w-[1440px] mx-auto px-6 sm:px-8 lg:px-10">
            <InfrastructurePage />
          </div>
        </section>

        {/* AI Assistant Section - Full bleed glass card */}
        <section id="ai-assistant" className="features-section-wrapper relative overflow-hidden border-b border-slate-200/90 glass-card w-full bg-white/80 backdrop-blur-md">
          <div className="max-w-[1440px] mx-auto px-6 sm:px-8 lg:px-10">
            <AIAssistantPage />
          </div>
        </section>

        {/* Audit Logs Section - Full bleed glass card */}
        <section id="audit" className="features-section-wrapper relative overflow-hidden border-b border-slate-200/90 glass-card w-full bg-white/75 backdrop-blur-md">
          <div className="max-w-[1440px] mx-auto px-6 sm:px-8 lg:px-10">
            <AuditLogsPage />
          </div>
        </section>

        {/* Reports Section - Full bleed glass card */}
        <section id="reports" className="features-section-wrapper relative overflow-hidden border-b border-slate-200/90 glass-card w-full bg-white/80 backdrop-blur-md">
          <div className="max-w-[1440px] mx-auto px-6 sm:px-8 lg:px-10">
            <ReportsPage />
          </div>
        </section>

        {/* Settings Section - Full bleed glass card */}
        <section id="settings" className="compliance-section-wrapper relative overflow-hidden border-b border-slate-200/90 glass-card w-full bg-white/75 backdrop-blur-md">
          <div className="max-w-[1440px] mx-auto px-6 sm:px-8 lg:px-10">
            <SettingsPage />
          </div>
        </section>
        
      </div>
    </div>
  )
}
