import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { AlertTriangle, ArrowLeft, Dna } from 'lucide-react'
import { getAnalysis } from '@/api/analyses'
import { getPatient } from '@/api/patients'
import { errorMessage } from '@/api/client'
import { ResultView } from '@/components/results/ResultView'
import { Card } from '@/components/ui/card'
import { ErrorNote } from '@/components/ui/notes'
import { SEX_RU } from '@/lib/dictionary'
import { cn, fmtDate } from '@/lib/utils'
import type { AnalysisStatus } from '@/types/api'

const inProgress = (s?: AnalysisStatus) => s === 'RECEIVED' || s === 'PROCESSING'
const STEPS: { id: AnalysisStatus[]; label: string }[] = [
  { id: ['RECEIVED'], label: 'Принят' },
  { id: ['PROCESSING'], label: 'ML-анализ' },
  { id: ['DONE'], label: 'Готово' },
]

export default function AnalysisResultPage() {
  const { patientId = '', analysisId = '' } = useParams()
  const patient = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId) })
  const { data, isError, error } = useQuery({
    queryKey: ['analysis', patientId, analysisId],
    queryFn: () => getAnalysis(patientId, analysisId),
    refetchInterval: (q) => (inProgress(q.state.data?.status) ? 2000 : false),
  })
  const p = patient.data
  const idx = STEPS.findIndex((s) => data && s.id.includes(data.status))

  return (
    <div className="space-y-5">
      <Link to={`/doctor/patients/${patientId}`}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> {p?.full_name ?? 'Пациент'}
      </Link>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Результат скрининга</h1>
        <p className="text-sm text-muted-foreground">
          {p ? `${p.full_name ?? 'Пациент'}, ${p.age} лет, ${SEX_RU[p.sex]}` : ''}
          {data?.created_at ? ` · анализ от ${fmtDate(data.created_at)}` : ''}
        </p>
      </div>

      {isError && <ErrorNote>{errorMessage(error)}</ErrorNote>}

      {(!data && !isError || inProgress(data?.status)) && (
        <Card className="grid place-items-center gap-5 px-6 py-16 text-center">
          <motion.span animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 6, ease: 'linear' }}
            className="grid size-16 place-items-center rounded-2xl bg-primary/10 text-primary">
            <Dna className="size-8" />
          </motion.span>
          <div>
            <p className="text-lg font-medium">Модель анализирует показатели…</p>
            <p className="text-sm text-muted-foreground">Страница обновится автоматически</p>
          </div>
          <ol className="flex items-center gap-2 text-xs">
            {STEPS.map((s, i) => (
              <li key={s.label} className={cn('rounded-full px-3 py-1 font-medium',
                i <= idx ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground')}>
                {s.label}
              </li>
            ))}
          </ol>
        </Card>
      )}

      {data?.status === 'FAILED' && (
        <Card className="flex items-start gap-3 border-red-200 bg-red-50 p-5 text-red-800">
          <AlertTriangle className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-medium">Не удалось обработать анализ</p>
            <p className="text-sm">Код ошибки: {data.error_code ?? 'неизвестно'}. Проверьте показатели и отправьте анализ повторно.</p>
          </div>
        </Card>
      )}

      {data?.status === 'DONE' && data.result && <ResultView result={data.result} />}
      {data?.status === 'DONE' && !data.result && <ErrorNote>Анализ готов, но модель не вернула результат</ErrorNote>}
    </div>
  )
}