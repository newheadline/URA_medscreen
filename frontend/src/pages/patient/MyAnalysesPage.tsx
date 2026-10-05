import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ArrowLeft, CheckCircle2, ChevronRight, Clock, Loader2 } from 'lucide-react'
import { listMyAnalyses } from '@/api/me'
import { errorMessage } from '@/api/client'
import { Badge, TriageBadge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { ErrorNote } from '@/components/ui/notes'
import { ANEMIA_CLASS_RU, CAUSE_RU, STATUS_RU } from '@/lib/dictionary'
import { fmtDate } from '@/lib/utils'
import type { AnalysisListItem, AnalysisStatus } from '@/types/api'

const inProgress = (s: AnalysisStatus) => s === 'RECEIVED' || s === 'PROCESSING'

function StatusBadge({ s }: { s: AnalysisStatus }) {
  if (s === 'DONE')
    return (
      <Badge className="bg-emerald-50 text-emerald-700">
        <CheckCircle2 className="size-3" />
        {STATUS_RU[s]}
      </Badge>
    )
  if (s === 'FAILED')
    return (
      <Badge className="bg-red-50 text-red-700">
        <AlertTriangle className="size-3" />
        {STATUS_RU[s]}
      </Badge>
    )
  return (
    <Badge className="bg-sky-50 text-sky-700">
      {s === 'PROCESSING' ? <Loader2 className="size-3 animate-spin" /> : <Clock className="size-3" />}
      {STATUS_RU[s]}
    </Badge>
  )
}

function Row({ a }: { a: AnalysisListItem }) {
  return (
    <li>
      <Link
        to={`/patient/analyses/${a.analysis_id}`}
        className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 px-5 py-3 transition-colors hover:bg-muted/60 focus-visible:bg-muted/60 focus-visible:outline-none"
      >
        <div>
          <div className="text-sm font-medium">{fmtDate(a.created_at)}</div>
          {a.status === 'DONE' && a.anemia_class && (
            <div className="text-xs text-muted-foreground">
              {ANEMIA_CLASS_RU[a.anemia_class]}
              {a.deficiency_cause && a.deficiency_cause !== 'none' ? ` · ${CAUSE_RU[a.deficiency_cause]}` : ''}
            </div>
          )}
          {a.status === 'FAILED' && <div className="text-xs text-red-600">Не удалось обработать</div>}
        </div>
        <div className="flex items-center gap-2">
          {a.status === 'DONE' && <TriageBadge status={a.triage_status} />}
          <StatusBadge s={a.status} />
          <ChevronRight className="size-4 text-muted-foreground" />
        </div>
      </Link>
    </li>
  )
}

export default function MyAnalysesPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['my-analyses'],
    queryFn: () => listMyAnalyses(),
    refetchInterval: (q) => (q.state.data?.items.some((a) => inProgress(a.status)) ? 2000 : false),
  })

  return (
    <div className="space-y-5">
      <Link
        to="/patient"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> На главную
      </Link>

      <h1 className="text-2xl font-semibold tracking-tight">Мои анализы</h1>

      {isError && <ErrorNote>{errorMessage(error)}</ErrorNote>}
      {isLoading && <Card className="m-0 h-24 animate-pulse" />}
      {data && data.items.length === 0 && (
        <Card className="p-8 text-center text-sm text-muted-foreground">
          Анализов пока нет. Анализы создаёт ваш лечащий врач.
        </Card>
      )}
      {data && data.items.length > 0 && (
        <Card>
          <ul className="divide-y divide-border">
            {data.items.map((a) => (
              <Row key={a.analysis_id} a={a} />
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}