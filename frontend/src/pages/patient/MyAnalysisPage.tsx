import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { AlertTriangle, ArrowLeft, Dna } from 'lucide-react'
import { getMyAnalysis } from '@/api/me'
import { errorMessage } from '@/api/client'
import { PatientResultView } from '@/components/results/PatientResultView'
import { Card } from '@/components/ui/card'
import { ErrorNote } from '@/components/ui/notes'
import { fmtDate } from '@/lib/utils'
import type { AnalysisStatus } from '@/types/api'

const inProgress = (s?: AnalysisStatus) => s === 'RECEIVED' || s === 'PROCESSING'

export default function MyAnalysisPage() {
  const { analysisId = '' } = useParams()
  const { data, isError, error } = useQuery({
    queryKey: ['my-analysis', analysisId],
    queryFn: () => getMyAnalysis(analysisId),
    refetchInterval: (q) => (inProgress(q.state.data?.status) ? 2000 : false),
  })

  return (
    <div className="space-y-5">
      <Link
        to="/patient/analyses"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Все анализы
      </Link>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Результат анализа</h1>
        {data?.created_at && (
          <p className="text-sm text-muted-foreground">от {fmtDate(data.created_at)}</p>
        )}
      </div>

      {isError && <ErrorNote>{errorMessage(error)}</ErrorNote>}

      {(!data && !isError) || inProgress(data?.status) ? (
        <Card className="grid place-items-center gap-5 px-6 py-16 text-center">
          <motion.span
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 6, ease: 'linear' }}
            className="grid size-16 place-items-center rounded-2xl bg-primary/10 text-primary"
          >
            <Dna className="size-8" />
          </motion.span>
          <div>
            <p className="text-lg font-medium">Анализ обрабатывается</p>
            <p className="text-sm text-muted-foreground">Страница обновится автоматически</p>
          </div>
        </Card>
      ) : null}

      {data?.status === 'FAILED' && (
        <Card className="flex items-start gap-3 border-red-200 bg-red-50 p-5 text-red-800">
          <AlertTriangle className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-medium">Не удалось обработать анализ</p>
            <p className="text-sm">Обратитесь к врачу, который направил анализ.</p>
          </div>
        </Card>
      )}

      {data?.status === 'DONE' && data.result && (
        <PatientResultView result={data.result} createdAt={data.created_at} />
      )}
      {data?.status === 'DONE' && !data.result && <ErrorNote>Не удалось получить результат</ErrorNote>}
    </div>
  )
}