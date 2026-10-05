import { useState } from 'react'
import { useForm, type FieldErrors, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ChevronDown, Loader2, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Collapse } from '@/components/ui/collapse'
import { Input } from '@/components/ui/input'
import { FieldError } from '@/components/ui/notes'
import { LAB_FIELDS, LAB_GROUPS, emptyLabs, filledCount, labsSchema, normalizeNum, type LabGroupId, type RawLabs } from '@/lib/labs'
import { cn } from '@/lib/utils'

interface Props {
  initial?: RawLabs          // предзаполнение (например, из CSV)
  submitting: boolean
  onSubmit: (raw: RawLabs) => void
}

const groupHasValues = (raw: RawLabs, g: LabGroupId) =>
  LAB_FIELDS.some((f) => f.group === g && normalizeNum(raw[f.key] ?? '') !== '')

export function LabsForm({ initial, submitting, onSubmit }: Props) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<RawLabs>({
    defaultValues: initial ?? emptyLabs(),
    resolver: zodResolver(labsSchema) as unknown as Resolver<RawLabs>,
  })

  // Гемоглобин (обязательный) — в первой группе, она открыта всегда; остальные — по клику
  const [open, setOpen] = useState<Record<LabGroupId, boolean>>(() => ({
    cbc: true,
    iron: !!initial && groupHasValues(initial, 'iron'),
    b: !!initial && groupHasValues(initial, 'b'),
    copper: !!initial && groupHasValues(initial, 'copper'),
    other: !!initial && groupHasValues(initial, 'other'),
  }))

  const values = watch()

  // При ошибке разворачиваем группы, где она есть
  const onInvalid = (errs: FieldErrors<RawLabs>) => {
    setOpen((o) => {
      const next = { ...o }
      for (const f of LAB_FIELDS) if (errs[f.key]) next[f.group] = true
      return next
    })
  }

  return (
    <form onSubmit={handleSubmit(onSubmit, onInvalid)} noValidate className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Обязателен только гемоглобин. Остальные показатели можно пропустить — чем их больше, тем точнее скрининг.
      </p>

      {LAB_GROUPS.map((grp) => {
        const fields = LAB_FIELDS.filter((f) => f.group === grp.id)
        const filled = fields.filter((f) => normalizeNum(values[f.key] ?? '') !== '').length
        const hasErr = fields.some((f) => errors[f.key])
        return (
          <div key={grp.id} className={cn('rounded-xl border bg-card', hasErr ? 'border-destructive/50' : 'border-border')}>
            <button
              type="button"
              onClick={() => setOpen((o) => ({ ...o, [grp.id]: !o[grp.id] }))}
              aria-expanded={open[grp.id]}
              className="flex w-full items-center justify-between gap-3 rounded-xl px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span>
                <span className="block text-sm font-medium">{grp.title}</span>
                <span className="block text-xs text-muted-foreground">{grp.hint}</span>
              </span>
              <span className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">{filled}/{fields.length}</span>
                <ChevronDown className={cn('size-4 text-muted-foreground transition-transform', open[grp.id] && 'rotate-180')} />
              </span>
            </button>
            <Collapse open={open[grp.id]}>
              <div className="grid gap-x-4 gap-y-3 px-3 pb-4 pt-1 sm:grid-cols-2 lg:grid-cols-3">
                {fields.map((f) => (
                  <label key={f.key}>
                    <span className="mb-1 flex items-baseline justify-between gap-2 text-xs font-medium">
                      <span>{f.label}{f.required && ' *'}</span>
                      <span className="shrink-0 font-normal text-muted-foreground">{f.unit}</span>
                    </span>
                    <Input {...register(f.key)} inputMode="decimal" aria-invalid={!!errors[f.key]} autoComplete="off" />
                    <FieldError message={errors[f.key]?.message as string | undefined} />
                  </label>
                ))}
              </div>
            </Collapse>
          </div>
        )
      })}

      <div className="flex items-center gap-3 pt-1">
        <Button type="submit" size="lg" disabled={submitting}>
          {submitting ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
          Отправить на скрининг
        </Button>
        <span className="text-xs text-muted-foreground">Заполнено показателей: {filledCount(values)}</span>
      </div>
    </form>
  )
}
