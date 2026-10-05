import { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { CheckCircle2, FlaskConical, ShieldAlert, ShieldCheck, TestTubes } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { ConditionDetails } from './ConditionDetails'
import { Footnotes } from './Footnotes'
import { ProbabilityChart, type Entry } from './ProbabilityChart'
import { ANEMIA_CLASS_RU, CAUSE_RU } from '@/lib/dictionary'
import { condMeta, condOrder, featureInfo } from '@/lib/conditions'
import type { AnalysisResult, ConditionPrediction } from '@/types/api'

export function ResultView({ result }: { result: AnalysisResult }) {
  const entries: Entry[] = useMemo(
    () => (Object.entries(result.predictions) as [string, ConditionPrediction][])
      .sort(([a], [b]) => condOrder(a, b))
      .map(([key, pred]) => ({ key, meta: condMeta(key), pred })),
    [result.predictions],
  )
  const [selected, setSelected] = useState<string | null>(
    () => [...entries].sort((a, b) => b.pred.probability - a.pred.probability)[0]?.key ?? null,
  )
  const sel = entries.find((e) => e.key === selected)
  const positives = entries.filter((e) => e.pred.positive)
  const missing = result.missing_features ?? []

  return (
    <div className="space-y-5">
      <Card className={result.anemia_detected ? 'border-red-200 bg-red-50/60 p-5' : 'border-emerald-200 bg-emerald-50/60 p-5'}>
        <div className="flex flex-wrap items-center gap-4">
          <span className={`grid size-12 place-items-center rounded-2xl text-white ${result.anemia_detected ? 'bg-red-500' : 'bg-emerald-500'}`}>
            {result.anemia_detected ? <ShieldAlert className="size-6" /> : <ShieldCheck className="size-6" />}
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold">{result.anemia_detected ? 'Анемия обнаружена' : 'Анемии нет'}</h2>
            <p className="text-sm text-muted-foreground">
              По критерию ВОЗ: гемоглобин {result.anemia_detected ? 'ниже' : 'не ниже'} порога {result.hemoglobin_threshold} г/л.
              {result.anemia_class && <> Класс: <b className="font-medium text-foreground">{ANEMIA_CLASS_RU[result.anemia_class]}</b>.</>}
              {result.deficiency_cause && result.deficiency_cause !== 'none' && <> Причина: <b className="font-medium text-foreground">{CAUSE_RU[result.deficiency_cause]}</b>.</>}
            </p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-black/5 pt-3 text-sm">
          <FlaskConical className="size-4 text-muted-foreground" />
          <span className="text-muted-foreground">Модель считает вероятными:</span>
          {positives.length === 0 && (
            <span className="inline-flex items-center gap-1 font-medium text-emerald-700">
              <CheckCircle2 className="size-4" /> дефициты не выявлены
            </span>
          )}
          {positives.map(({ key, meta, pred }) => (
            <button key={key} type="button" onClick={() => setSelected(key)}
              className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium text-white shadow-sm transition-transform hover:scale-105"
              style={{ background: meta.color }}>
              <meta.icon className="size-3.5" /> {meta.short} · {Math.round(pred.probability * 100)}%
            </button>
          ))}
        </div>
      </Card>

      <Card className="p-5">
        <h2 className="text-lg font-semibold">Вероятности дефицитов</h2>
        <p className="text-sm text-muted-foreground">Оценка ML-модели по введённым показателям</p>
        <ProbabilityChart entries={entries} selected={selected} onSelect={setSelected} />
      </Card>

      <AnimatePresence mode="wait" initial={false}>
        {sel && (
          <motion.div key={sel.key}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}>
            <ConditionDetails meta={sel.meta} pred={sel.pred} />
          </motion.div>
        )}
      </AnimatePresence>

      {missing.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-1 flex items-center gap-2 text-base font-semibold">
            <TestTubes className="size-4 text-primary" /> Для уточнения оценки не хватает
          </h2>
          <p className="mb-3 text-sm text-muted-foreground">
            Эти показатели использует модель, но они не были измерены — их стоит добавить при дообследовании.
          </p>
          <div className="flex flex-wrap gap-2">
            {missing.map((k) => (
              <span key={k} className="rounded-full border border-border bg-muted px-3 py-1 text-xs" title={featureInfo(k).unit}>
                {featureInfo(k).label}
              </span>
            ))}
          </div>
        </Card>
      )}

      <Footnotes />
      {result.model_version && <p className="text-center text-xs text-muted-foreground">Версия модели: {result.model_version}</p>}
    </div>
  )
}