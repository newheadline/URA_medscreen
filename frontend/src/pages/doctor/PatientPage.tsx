import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Mail, Phone } from 'lucide-react'
import { getPatient } from '@/api/patients'
import { errorMessage } from '@/api/client'
import { AnalysisIntake } from '@/components/labs/AnalysisIntake'
import { AnalysesHistory } from '@/components/patients/AnalysesHistory'
import { TriageBadge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { ErrorNote } from '@/components/ui/notes'
import { SEX_RU } from '@/lib/dictionary'

export default function PatientPage() {
  const { patientId = '' } = useParams()
  const { data: p, isLoading, isError, error } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => getPatient(patientId),
    // в профиле есть счётчик анализов в работе — обновляем, пока они есть
    refetchInterval: (q) => ((q.state.data?.clinical_summary.analyses_in_progress ?? 0) > 0 ? 2000 : false),
  })

  return (
    <div className="space-y-5">
      <Link to="/doctor/patients" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Пациенты
      </Link>

      {isError && <ErrorNote>{errorMessage(error)}</ErrorNote>}
      {isLoading && <div className="h-28 animate-pulse rounded-2xl bg-muted" />}

      {p && (
        <>
          <Card className="flex flex-wrap items-start justify-between gap-4 p-5">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">{p.full_name ?? 'Пациент'}</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {p.age} лет · {SEX_RU[p.sex]}{p.oms ? ` · ОМС ${p.oms}` : ''}
              </p>
              {(p.contacts?.phone || p.contacts?.email) && (
                <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                  {p.contacts.phone && <span className="flex items-center gap-1.5"><Phone className="size-3.5" />{p.contacts.phone}</span>}
                  {p.contacts.email && <span className="flex items-center gap-1.5"><Mail className="size-3.5" />{p.contacts.email}</span>}
                </p>
              )}
            </div>
            <div className="text-right">
              <TriageBadge status={p.clinical_summary.triage_status} />
              <p className="mt-2 text-xs text-muted-foreground">Анализов: {p.clinical_summary.analyses_total}</p>
            </div>
          </Card>

          <AnalysisIntake patient={p} />
          <AnalysesHistory patientId={p.patient_id} />
        </>
      )}
    </div>
  )
}
