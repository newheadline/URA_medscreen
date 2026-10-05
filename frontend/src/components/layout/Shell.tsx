import { Link, Outlet, useNavigate } from 'react-router-dom'
import { Activity, LogOut } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/auth/store'
import { Button } from '@/components/ui/button'

export function Shell({ title, home }: { title: string; home: string }) {
  const logout = useAuth((s) => s.logout)
  const navigate = useNavigate()
  const qc = useQueryClient()

  const onLogout = () => {
    logout()
    qc.clear() // медицинские данные не должны оставаться в кэше после выхода
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-border bg-card/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Link to={home} className="flex items-center gap-2 font-semibold">
            <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
              <Activity className="size-4" />
            </span>
            MedScreen
            <span className="ml-2 hidden rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground sm:inline">
              {title}
            </span>
          </Link>
          <Button variant="ghost" size="sm" onClick={onLogout}>
            <LogOut className="size-4" /> Выйти
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
