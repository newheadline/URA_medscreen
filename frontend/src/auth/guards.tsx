import { Navigate, Outlet } from 'react-router-dom'
import { homeFor, useAuth } from './store'
import type { Role } from '@/types/api'

export function RequireRole({ role }: { role: Role }) {
  const { token, role: current } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  if (current !== role) return <Navigate to={homeFor(current)} replace />
  return <Outlet />
}
