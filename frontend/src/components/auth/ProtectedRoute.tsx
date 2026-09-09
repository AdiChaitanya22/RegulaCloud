import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import type { ReactNode } from 'react'

interface ProtectedRouteProps {
  children: ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    // Validate session — show minimal dark splash to avoid flash
    return (
      <div className="min-h-screen bg-[#05070A] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Verifying session...
          </span>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    // Preserve the intended destination so login can redirect back
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  return <>{children}</>
}
