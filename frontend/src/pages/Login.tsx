import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { Activity, ArrowRight, Loader2, Stethoscope, UserRound } from 'lucide-react'
import { demoLogin } from '@/api/auth'
import { errorMessage } from '@/api/client'
import { homeFor, useAuth } from '@/auth/store'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ErrorNote } from '@/components/ui/notes'
import { cn } from '@/lib/utils'

type DemoRole = 'doctor' | 'patient'

const ROLES: { id: DemoRole; title: string; text: string; icon: typeof Stethoscope }[] = [
  { id: 'doctor', title: 'Врач', text: 'Пациенты, загрузка анализов, результаты скрининга', icon: Stethoscope },
  { id: 'patient', title: 'Пациент', text: 'Мои анализы и понятное заключение', icon: UserRound },
]

export default function Login() {
  const { token, role: current, login } = useAuth()
  const navigate = useNavigate()
  const [role, setRole] = useState<DemoRole>('doctor')

  const mutation = useMutation({
    mutationFn: () => demoLogin(role),
    onSuccess: (t) => {
      login(t.access_token, t.role)
      navigate(homeFor(t.role), { replace: true })
    },
  })

  if (token) return <Navigate to={homeFor(current)} replace />

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 grid size-12 place-items-center rounded-2xl bg-primary text-primary-foreground">
            <Activity className="size-6" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">MedScreen</h1>
          <p className="mt-1 text-sm text-muted-foreground">ИИ-скрининг латентных дефицитных состояний</p>
        </div>

        <Card className="p-6">
          <p className="mb-3 text-sm font-medium">Войти как</p>
          <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label="Роль">
            {ROLES.map(({ id, title, text, icon: Icon }) => {
              const active = role === id
              return (
                <motion.button
                  key={id}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setRole(id)}
                  className={cn(
                    'rounded-xl border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    active ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted',
                  )}
                >
                  <Icon className={cn('mb-2 size-5', active ? 'text-primary' : 'text-muted-foreground')} />
                  <div className="font-medium">{title}</div>
                  <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{text}</div>
                </motion.button>
              )
            })}
          </div>

          {mutation.isError && (
            <div className="mt-4">
              <ErrorNote>{errorMessage(mutation.error)}</ErrorNote>
            </div>
          )}

          <Button size="lg" className="mt-5 w-full" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
            Войти в кабинет {role === 'doctor' ? 'врача' : 'пациента'}
            {!mutation.isPending && <ArrowRight className="size-4" />}
          </Button>
          <p className="mt-3 text-center text-xs text-muted-foreground">Демо-режим: вход без пароля</p>
        </Card>
      </motion.div>
    </div>
  )
}
