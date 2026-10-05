import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, ChevronRight, Clock, Loader2 } from 'lucide-react'
import { listAnalyses } from '@/api/analyses'
import { errorMessage } from '@/api/client'
import { Badge, TriageBadge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { ErrorNote } from '@/components/ui/notes'
import { ANEMIA_CLASS_RU, CAUSE_RU, STATUS_RU } from '@/lib/dictionary'
import { fmtDate } from '@/lib/utils'
import type { AnalysisListItem, AnalysisStatus } from '@/types/api'

const inProgress = (s: AnalysisStatus) => s === 'RECEIVED' || s === 'PROCESSING'

function StatusBadge({ s }: { s: AnalysisStatus }) {
  if (s === 'DONE') return <Badge className="bg-emerald-50 text-emerald-700"><CheckCircle2 className="size-3" />{STATUS_RU[s]}</Badge>
  if (s === 'FAILED') return <Badge className="bg-red-50 text-red-700"><AlertTriangle className="size-3" />{STATUS_RU[s]}</Badge>
  return (
    <Badge className="bg-sky-50 text-sky-700">
      {s === 'PROCESSING' ? <Loader2 className="size-3 animate-spin" /> : <Clock className="size-3" />}
      {STATUS_RU[s]}
    </Badge>
  )
}

function Row({ a, patientId }: { a: AnalysisListItem; patientId: string }) {
  return (
    <li>
      <Link
        to={`/doctor/patients/${patientId}/analyses/${a.analysis_id}`}
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
          {a.status === 'FAILED' && (
            <div className="text-xs text-red-600">Код ошибки: {a.error_code ?? 'неизвестно'}</div>
          )}
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

export function AnalysesHistory({ patientId }: { patientId: string }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['analyses', patientId],
    queryFn: () => listAnalyses(patientId),
    refetchInterval: (q) => (q.state.data?.items.some((a) => inProgress(a.status)) ? 2000 : false),
  })

  return (
    <Card>
      <div className="border-b border-border px-5 py-3.5">
        <h2 className="text-lg font-semibold">История анализов</h2>
      </div>
      {isError && <div className="p-4"><ErrorNote>{errorMessage(error)}</ErrorNote></div>}
      {isLoading && <div className="m-4 h-14 animate-pulse rounded-lg bg-muted" />}
      {data && data.items.length === 0 && (
        <p className="px-5 py-8 text-center text-sm text-muted-foreground">Анализов пока нет</p>
      )}
      {data && data.items.length > 0 && (
        <ul className="divide-y divide-border">
          {data.items.map((a) => <Row key={a.analysis_id} a={a} patientId={patientId} />)}
        </ul>
      )}
    </Card>
  )
}