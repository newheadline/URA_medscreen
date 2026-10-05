import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Plus, Search, Users } from 'lucide-react'
import { listPatients } from '@/api/patients'
import { errorMessage } from '@/api/client'
import { CreatePatientForm } from '@/components/patients/CreatePatientForm'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Collapse } from '@/components/ui/collapse'
import { Input } from '@/components/ui/input'
import { TriageBadge } from '@/components/ui/badge'
import { ErrorNote } from '@/components/ui/notes'
import { SEX_RU } from '@/lib/dictionary'
import { useDebounced } from '@/lib/hooks'
import { cn, fmtDate } from '@/lib/utils'
import type { TriageFilter } from '@/types/api'

const PAGE = 20
const FILTERS: { id: TriageFilter; label: string }[] = [
  { id: 'all', label: 'Все' },
  { id: 'anemia', label: 'Анемия' },
  { id: 'latent', label: 'Скрытый дефицит' },
  { id: 'normal', label: 'Норма' },
]

export default function PatientsPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [searchInput, setSearchInput] = useState('')
  const search = useDebounced(searchInput.trim())
  const [triage, setTriage] = useState<TriageFilter>('all')
  const [page, setPage] = useState(0)
  const [creating, setCreating] = useState(false)

  const { data, isLoading, isError, error, isPlaceholderData } = useQuery({
    queryKey: ['patients', { search, triage, page }],
    queryFn: () => listPatients({ search, triage, limit: PAGE, offset: page * PAGE }),
    placeholderData: keepPreviousData,
  })

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE)) : 1

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Пациенты</h1>
          <p className="text-sm text-muted-foreground">{data ? `Всего: ${data.total}` : 'Загрузка…'}</p>
        </div>
        <Button onClick={() => setCreating((v) => !v)}>
          <Plus className={cn('size-4 transition-transform', creating && 'rotate-45')} />
          {creating ? 'Свернуть' : 'Добавить пациента'}
        </Button>
      </div>

      <Collapse open={creating}>
        <CreatePatientForm
          onCancel={() => setCreating(false)}
          onCreated={(p) => {
            qc.invalidateQueries({ queryKey: ['patients'] })
            navigate(`/doctor/patients/${p.patient_id}`)
          }}
        />
      </Collapse>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center gap-3 border-b border-border p-3">
          <div className="relative min-w-56 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchInput}
              onChange={(e) => { setSearchInput(e.target.value); setPage(0) }}
              placeholder="Поиск по ФИО или номеру ОМС"
              className="pl-9"
              maxLength={100}
            />
          </div>
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Фильтр по статусу">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => { setTriage(f.id); setPage(0) }}
                aria-pressed={triage === f.id}
                className={cn(
                  'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                  triage === f.id ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-muted',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {isError && <div className="p-4"><ErrorNote>{errorMessage(error)}</ErrorNote></div>}

        {isLoading && (
          <div className="space-y-2 p-4">
            {[0, 1, 2, 3].map((i) => <div key={i} className="h-11 animate-pulse rounded-lg bg-muted" />)}
          </div>
        )}

        {data && data.items.length === 0 && (
          <div className="grid place-items-center gap-2 px-4 py-14 text-center text-muted-foreground">
            <Users className="size-8" />
            <p className="text-sm">
              {search || triage !== 'all' ? 'Никого не нашли — измените запрос или фильтр' : 'У вас пока нет пациентов. Добавьте первого'}
            </p>
          </div>
        )}

        {data && data.items.length > 0 && (
          <div className={cn('overflow-x-auto transition-opacity', isPlaceholderData && 'opacity-60')}>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="px-4 py-2.5 font-medium">ФИО</th>
                  <th className="px-4 py-2.5 font-medium">Возраст</th>
                  <th className="px-4 py-2.5 font-medium">Пол</th>
                  <th className="px-4 py-2.5 font-medium">ОМС</th>
                  <th className="px-4 py-2.5 font-medium">Статус</th>
                  <th className="px-4 py-2.5 font-medium">Последний анализ</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr
                    key={p.patient_id}
                    tabIndex={0}
                    onClick={() => navigate(`/doctor/patients/${p.patient_id}`)}
                    onKeyDown={(e) => e.key === 'Enter' && navigate(`/doctor/patients/${p.patient_id}`)}
                    className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/60 focus-visible:bg-muted/60 focus-visible:outline-none"
                  >
                    <td className="px-4 py-3 font-medium">{p.full_name ?? '—'}</td>
                    <td className="px-4 py-3">{p.age}</td>
                    <td className="px-4 py-3">{SEX_RU[p.sex]}</td>
                    <td className="px-4 py-3 text-muted-foreground">{p.oms ?? '—'}</td>
                    <td className="px-4 py-3"><TriageBadge status={p.triage_status} /></td>
                    <td className="px-4 py-3 text-muted-foreground">{fmtDate(p.last_analysis_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && data.total > PAGE && (
          <div className="flex items-center justify-between border-t border-border px-4 py-2.5 text-sm text-muted-foreground">
            <span>Страница {page + 1} из {pages}</span>
            <div className="flex gap-1">
              <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)} aria-label="Назад"><ChevronLeft className="size-4" /></Button>
              <Button variant="outline" size="sm" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)} aria-label="Вперёд"><ChevronRight className="size-4" /></Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
