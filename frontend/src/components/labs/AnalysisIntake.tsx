import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { ClipboardList, FileUp } from 'lucide-react'
import { createAnalysis } from '@/api/analyses'
import { errorMessage } from '@/api/client'
import { Card } from '@/components/ui/card'
import { Collapse } from '@/components/ui/collapse'
import { ErrorNote } from '@/components/ui/notes'
import { LabsCsvDrop } from './LabsCsvDrop'
import { LabsForm } from './LabsForm'
import { toBiomarkers, type RawLabs } from '@/lib/labs'
import { cn } from '@/lib/utils'
import type { PatientProfile } from '@/types/api'

type Mode = 'csv' | 'manual' | null

const MODES = [
  { id: 'csv' as const, title: 'Загрузить CSV', text: 'Выгрузка из лаборатории или МИС', icon: FileUp },
  { id: 'manual' as const, title: 'Ввести вручную', text: 'Показатели по группам, пропуски допустимы', icon: ClipboardList },
]

export function AnalysisIntake({ patient }: { patient: PatientProfile }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>(null)
  const [pregnant, setPregnant] = useState(false)
  const [prefill, setPrefill] = useState<{ key: number; raw: RawLabs } | null>(null)

  const mutation = useMutation({
    mutationFn: (raw: RawLabs) =>
      createAnalysis(patient.patient_id, {
        biomarkers: toBiomarkers(raw),
        pregnant: patient.sex === 'F' && pregnant,
      }),
    onSuccess: (a) => {
      qc.invalidateQueries({ queryKey: ['analyses', patient.patient_id] })
      qc.invalidateQueries({ queryKey: ['patient', patient.patient_id] })
      qc.invalidateQueries({ queryKey: ['patients'] })
      navigate(`/doctor/patients/${patient.patient_id}/analyses/${a.analysis_id}`)
    },
  })

  const choose = (m: Exclude<Mode, null>) => {
    mutation.reset()
    setPrefill(null)
    setMode((cur) => (cur === m ? null : m))
  }

  const submit = (raw: RawLabs) => mutation.mutate(raw)

  return (
    <Card className="p-5">
      <h2 className="text-lg font-semibold">Новый анализ</h2>
      <p className="mb-4 text-sm text-muted-foreground">Выберите способ ввода данных</p>

      <div className="grid gap-3 sm:grid-cols-2">
        {MODES.map(({ id, title, text, icon: Icon }) => {
          const active = mode === id
          return (
            <motion.button
              key={id}
              type="button"
              whileTap={{ scale: 0.985 }}
              onClick={() => choose(id)}
              aria-expanded={active}
              className={cn(
                'flex items-center gap-3 rounded-xl border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                active ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted',
              )}
            >
              <span className={cn('grid size-10 shrink-0 place-items-center rounded-lg',
                active ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground')}>
                <Icon className="size-5" />
              </span>
              <span>
                <span className="block font-medium">{title}</span>
                <span className="block text-xs text-muted-foreground">{text}</span>
              </span>
            </motion.button>
          )
        })}
      </div>

      <Collapse open={mode !== null}>
        <div className="space-y-4 pt-5">
          {patient.sex === 'F' && (
            <label className="flex w-fit cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={pregnant}
                onChange={(e) => setPregnant(e.target.checked)}
                className="size-4 accent-[var(--primary)]"
              />
              Пациентка беременна
            </label>
          )}

          {mutation.isError && <ErrorNote>{errorMessage(mutation.error)}</ErrorNote>}

          {mode === 'csv' && (
            <LabsCsvDrop
              submitting={mutation.isPending}
              onSubmit={submit}
              onEdit={(raw) => {
                setPrefill({ key: Date.now(), raw })
                setMode('manual')
              }}
            />
          )}
          {mode === 'manual' && (
            <LabsForm
              key={prefill?.key ?? 'blank'}
              initial={prefill?.raw}
              submitting={mutation.isPending}
              onSubmit={submit}
            />
          )}
        </div>
      </Collapse>
    </Card>
  )
}