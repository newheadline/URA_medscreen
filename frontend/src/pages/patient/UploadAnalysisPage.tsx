import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { createMyAnalysis } from '@/api/me'
import { errorMessage } from '@/api/client'
import { getMe } from '@/api/me'
import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/ui/card'
import { ErrorNote } from '@/components/ui/notes'
import { LabsCsvDrop } from '@/components/labs/LabsCsvDrop'
import { toBiomarkers, type RawLabs } from '@/lib/labs'

export default function UploadAnalysisPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const me = useQuery({ queryKey: ['me'], queryFn: getMe })
  const [pregnant, setPregnant] = useState(false)

  const mutation = useMutation({
    mutationFn: (raw: RawLabs) =>
      createMyAnalysis({
        biomarkers: toBiomarkers(raw),
        pregnant: me.data?.sex === 'F' && pregnant,
      }),
    onSuccess: (a) => {
      qc.invalidateQueries({ queryKey: ['me'] })
      qc.invalidateQueries({ queryKey: ['my-analyses'] })
      navigate(`/patient/analyses/${a.analysis_id}`)
    },
  })

  const submit = (raw: RawLabs) => mutation.mutate(raw)

  return (
    <div className="space-y-5">
      <Link
        to="/patient"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> На главную
      </Link>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Загрузить анализ</h1>
        <p className="text-sm text-muted-foreground">
          CSV-файл с показателями. Заголовки — названия показателей (hemoglobin, ferritin, …).
        </p>
      </div>

      <Card className="p-5">
        {me.data?.sex === 'F' && (
          <label className="mb-4 flex w-fit cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={pregnant}
              onChange={(e) => setPregnant(e.target.checked)}
              className="size-4 accent-[var(--primary)]"
            />
            Беременность
          </label>
        )}

        {mutation.isError && <ErrorNote>{errorMessage(mutation.error)}</ErrorNote>}

        <LabsCsvDrop
          submitting={mutation.isPending}
          onSubmit={submit}
          onEdit={() => {}}
        />
      </Card>
    </div>
  )
}