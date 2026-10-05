import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Info, ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react'
import { getMe } from '@/api/me'
import { errorMessage } from '@/api/client'
import { Card } from '@/components/ui/card'
import { ErrorNote } from '@/components/ui/notes'
import { ANEMIA_CLASS_RU, CAUSE_RU } from '@/lib/dictionary'
import { cn, fmtDate } from '@/lib/utils'
import type { ClinicalSummary } from '@/types/api'

const TONE_BG = {
  green: 'border-emerald-200 bg-emerald-50/60',
  amber: 'border-amber-200 bg-amber-50/60',
  red: 'border-red-200 bg-red-50/60',
  grey: 'border-border bg-muted/40',
}
const TONE_ICON = {
  green: 'bg-emerald-500',
  amber: 'bg-amber-500',
  red: 'bg-red-500',
  grey: 'bg-slate-400',
}


import { FileUp } from 'lucide-react'



function StatusCard({ s }: { s: ClinicalSummary }) {
  const last = s.last_analysis
  const cfg =
    s.triage_status === 'anemia'
      ? { tone: 'red' as const, icon: ShieldAlert, title: 'Обнаружены признаки анемии' }
      : s.triage_status === 'latent'
        ? { tone: 'amber' as const, icon: ShieldQuestion, title: 'Анемии нет, но есть признаки дефицита' }
        : s.triage_status === 'normal'
          ? { tone: 'green' as const, icon: ShieldCheck, title: 'Всё в порядке' }
          : { tone: 'grey' as const, icon: Info, title: 'Анализов пока нет' }

  const cls = last?.anemia_class ? ANEMIA_CLASS_RU[last.anemia_class] : null
  const cause = last?.deficiency_cause && last.deficiency_cause !== 'none' ? CAUSE_RU[last.deficiency_cause] : null
  const Icon = cfg.icon

  return (
    <Card className={cn('p-6', TONE_BG[cfg.tone])}>
      <div className="flex flex-wrap items-start gap-4">
        <span className={cn('grid size-14 shrink-0 place-items-center rounded-2xl text-white', TONE_ICON[cfg.tone])}>
          <Icon className="size-7" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-xl font-semibold leading-tight">{cfg.title}</h2>
          {cls && (
            <p className="mt-1 text-sm">
              {cls}
              {cause ? ` · ${cause}` : ''}
            </p>
          )}
          {last && <p className="mt-3 text-xs text-muted-foreground">Последний анализ: {fmtDate(last.created_at)}</p>}
          {!last && (
            <p className="mt-1 text-sm text-muted-foreground">
              Как только врач отправит ваш анализ на скрининг, результат появится здесь.
            </p>
          )}
        </div>
        {last && (
          <Link
            to={`/patient/analyses/${last.analysis_id}`}
            className="shrink-0 self-center text-sm font-medium text-primary hover:underline"
          >
            Подробнее →
          </Link>
        )}
      </div>
    </Card>
  )
}

export default function PatientHome() {
  const { data, isLoading, isError, error } = useQuery({ queryKey: ['me'], queryFn: getMe })
  const s = data?.clinical_summary

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Здравствуйте</h1>
        <p className="text-sm text-muted-foreground">
          {data?.full_name ?? 'Кабинет пациента'}
        </p>
      </div>

      {isLoading && <Card className="h-40 animate-pulse" />}
      {isError && <ErrorNote>{errorMessage(error)}</ErrorNote>}
        <Link
        to="/patient/upload"
        className="flex items-center justify-between rounded-xl border border-primary/40 bg-primary/5 p-4 transition-colors hover:bg-primary/10"
      >
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-lg bg-primary text-primary-foreground">
            <FileUp className="size-5" />
          </span>
          <div>
            <div className="font-medium">Загрузить анализ</div>
            <div className="text-xs text-muted-foreground">CSV из лаборатории или МИС</div>
          </div>
        </div>
        <span className="text-sm font-medium text-primary">Загрузить →</span>
      </Link>

      {s && <StatusCard s={s} />}
      {s && s.analyses_total > 0 && (
        <Card className="flex items-center justify-between p-5">
          <div>
            <h2 className="text-lg font-semibold">История анализов</h2>
            <p className="text-sm text-muted-foreground">
              Всего: {s.analyses_total}
              {s.analyses_in_progress > 0 ? ` · в обработке: ${s.analyses_in_progress}` : ''}
            </p>
          </div>
          <Link
            to="/patient/analyses"
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-muted"
          >
            Все анализы
          </Link>
        </Card>
      )}
    </div>
  )
}