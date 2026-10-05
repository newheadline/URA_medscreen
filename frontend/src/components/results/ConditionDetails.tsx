import { useMemo, useState } from 'react'
import { AlertTriangle, Brain, Layers } from 'lucide-react'
import { Fn } from './Footnotes'
import { ShapWaterfall } from './ShapWaterfall'
import { CONTRIBUTION_SCALE, type Scale } from '@/lib/config'
import { topFeatures } from '@/lib/shap'
import { cn } from '@/lib/utils'
import type { CondMeta } from '@/lib/conditions'
import type { ConditionPrediction } from '@/types/api'

interface Props {
  meta: CondMeta
  pred: ConditionPrediction
  /** Сколько признаков показать. Врач — 7, пациент — 3–4. */
  maxFeatures?: number
  /** Для страницы врача — сноски <sup>1..5</sup>; для пациента — без них. */
  showFootnotes?: boolean
  /** Короткая подсказка для пациента. Если не задана — стандартная врачебная. */
  hintText?: string
}

export function ConditionDetails({
  meta,
  pred,
  maxFeatures = 7,
  showFootnotes = true,
  hintText,
}: Props) {
  const features = useMemo(
    () => topFeatures(pred.top_features).slice(0, maxFeatures),
    [pred.top_features, maxFeatures],
  )
  const [view, setView] = useState<Scale>('prob')
  const Icon = meta.icon
  const noEvidence = pred.has_evidence === false

  const fn = (n: number) => (showFootnotes ? <Fn n={n} /> : null)
  const hint =
    hintText ??
    (showFootnotes
      ? `Показаны ${features.length} наиболее значимых признаков${' '}`
      : `На оценку сильнее всего повлияли эти показатели. `)

  return (
    <div
      className="rounded-2xl border bg-card p-5 shadow-sm"
      style={{ borderColor: `color-mix(in oklab, ${meta.color} 35%, white)` }}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl text-white" style={{ background: meta.color }}>
            <Icon className="size-6" />
          </span>
          <div>
            <h3 className="text-lg font-semibold leading-tight">{meta.name}</h3>
            <p className="text-sm text-muted-foreground">
              Вероятность{fn(1)} {Math.round(pred.probability * 100)}% ·{' '}
              <span className={pred.positive ? 'font-medium text-red-700' : ''}>
                {pred.positive ? 'вероятен' : 'маловероятен'}
              </span>
              {fn(2)}
            </p>
          </div>
        </div>

        {CONTRIBUTION_SCALE === 'logit' && features.length > 0 && (
          <div className="inline-flex rounded-lg border border-border bg-muted p-0.5 text-xs" role="group" aria-label="Шкала вкладов">
            {([['prob', 'Вероятность'], ['logit', 'Лог-шансы']] as const).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setView(id)}
                aria-pressed={view === id}
                className={cn(
                  'rounded-md px-3 py-1.5 font-medium transition-colors',
                  view === id ? 'bg-card shadow-sm' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      {noEvidence && (
        <div role="alert" className="mt-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          Ключевые маркеры этого дефицита не измерены: вероятность априорная, выводу доверять нельзя. Рекомендуется дообследование.
        </div>
      )}

      {features.length > 0 ? (
        <>
          <div className="mt-4 flex items-start gap-2 rounded-lg bg-sky-50 px-3 py-2 text-sm text-sky-900">
            <Brain className="mt-0.5 size-4 shrink-0" />
            <span>
              {hint}
              {showFootnotes && (
                <>
                  {fn(5)}
                  {': так не нужно держать в голове корреляции остальных показателей. '}
                </>
              )}
              Красные столбики {showFootnotes ? '' : '— '}повышают вероятность дефицита, синие — понижают{fn(3)}.
            </span>
          </div>
          <div className="mt-3">
            <ShapWaterfall
              features={features}
              probability={pred.probability}
              dataScale={CONTRIBUTION_SCALE}
              view={view}
            />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {showFootnotes
              ? <>Базовый уровень и итог f(x){fn(4)}</>
              : 'Базовый уровень — оценка «среднего» пациента. Столбики показывают, как ваши показатели сдвинули её к итоговой вероятности.'}
          </p>
        </>
      ) : (
        <p className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
          <Layers className="size-4" /> Для этого дефицита модель не вернула вклады признаков.
        </p>
      )}
    </div>
  )
}