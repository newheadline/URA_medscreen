import { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Info, ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { ConditionDetails } from './ConditionDetails'
import { ProbabilityChart, type Entry } from './ProbabilityChart'
import { ANEMIA_CLASS_RU, CAUSE_RU } from '@/lib/dictionary'
import { condMeta, condOrder } from '@/lib/conditions'
import { cn, fmtDate } from '@/lib/utils'
import type { AnalysisResult, ConditionPrediction } from '@/types/api'

interface Verdict {
  tone: 'green' | 'amber' | 'red'
  icon: typeof ShieldCheck
  title: string
  text: string
}

const TONE_BG = {
  green: 'border-emerald-200 bg-emerald-50/60',
  amber: 'border-amber-200 bg-amber-50/60',
  red: 'border-red-200 bg-red-50/60',
}
const TONE_ICON = {
  green: 'bg-emerald-500',
  amber: 'bg-amber-500',
  red: 'bg-red-500',
}

function verdict(result: AnalysisResult, positives: Entry[]): Verdict {
  if (result.anemia_detected) {
    const parts: string[] = []
    if (result.anemia_class) parts.push(`Класс: ${ANEMIA_CLASS_RU[result.anemia_class]}.`)
    if (result.deficiency_cause && result.deficiency_cause !== 'none')
      parts.push(`Вероятная причина: ${CAUSE_RU[result.deficiency_cause]}.`)
    parts.push('Рекомендуется консультация врача.')
    return { tone: 'red', icon: ShieldAlert, title: 'Обнаружены признаки анемии', text: parts.join(' ') }
  }
  if (positives.length > 0) {
    const names = positives.map((e) => e.meta.name.toLowerCase()).join(', ')
    return {
      tone: 'amber',
      icon: ShieldQuestion,
      title: 'Анемии нет, но есть признаки дефицита',
      text: `Модель считает вероятным: ${names}. Это не диагноз, но стоит обсудить результат с врачом.`,
    }
  }
  return {
    tone: 'green',
    icon: ShieldCheck,
    title: 'Всё в порядке',
    text: 'Анемии и признаков дефицитов не обнаружено. Рекомендуется профилактический осмотр.',
  }
}

export function PatientResultView({
  result,
  createdAt,
}: {
  result: AnalysisResult
  createdAt?: string | null
}) {
  const entries: Entry[] = useMemo(
    () =>
      (Object.entries(result.predictions) as [string, ConditionPrediction][])
        .sort(([a], [b]) => condOrder(a, b))
        .map(([key, pred]) => ({ key, meta: condMeta(key), pred })),
    [result.predictions],
  )
  const positives = entries.filter((e) => e.pred.positive)
  const [selected, setSelected] = useState<string | null>(
    () =>
      [...positives].sort((a, b) => b.pred.probability - a.pred.probability)[0]?.key ??
      null,
  )
  const sel = entries.find((e) => e.key === selected)
  const v = verdict(result, positives)
  const Icon = v.icon

  return (
    <div className="space-y-5">
      <Card className={cn('p-6', TONE_BG[v.tone])}>
        <div className="flex items-start gap-4">
          <span className={cn('grid size-14 shrink-0 place-items-center rounded-2xl text-white', TONE_ICON[v.tone])}>
            <Icon className="size-7" />
          </span>
          <div className="min-w-0">
            <h1 className="text-xl font-semibold leading-tight">{v.title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{v.text}</p>
            {createdAt && <p className="mt-3 text-xs text-muted-foreground">Анализ от {fmtDate(createdAt)}</p>}
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <h2 className="text-lg font-semibold">Оценка по вашим показателям</h2>
        <p className="text-sm text-muted-foreground">
          Вероятность каждого состояния по данным анализа. Нажмите на столбец — раскроются подробности.
        </p>
        <ProbabilityChart entries={entries} selected={selected} onSelect={setSelected} />
      </Card>

      <AnimatePresence mode="wait" initial={false}>
        {sel && (
          <motion.div
            key={sel.key}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
          >
          <ConditionDetails
              meta={sel.meta}
             pred={sel.pred}
             maxFeatures={4}
             showFootnotes={false}
          />
          </motion.div>
        )}
      </AnimatePresence>

      <Card className="p-5 text-sm text-muted-foreground">
        <p className="flex items-start gap-2">
          <Info className="mt-0.5 size-4 shrink-0 text-primary" />
          <span>
            Это предварительная оценка по данным анализа, а не диагноз.
            Результат следует обсудить с лечащим врачом.
          </span>
        </p>
      </Card>
    </div>
  )
}