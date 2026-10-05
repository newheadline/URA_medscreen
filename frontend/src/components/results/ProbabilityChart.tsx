import { motion } from 'motion/react'
import { ChevronDown } from 'lucide-react'
import { Fn } from './Footnotes'
import { cn } from '@/lib/utils'
import type { CondMeta } from '@/lib/conditions'
import type { ConditionPrediction } from '@/types/api'

export interface Entry { key: string; meta: CondMeta; pred: ConditionPrediction }

const PLOT_H = 240

export function ProbabilityChart({ entries, selected, onSelect }: {
  entries: Entry[]; selected: string | null; onSelect: (key: string | null) => void
}) {
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[520px] pt-10">
        <div className="relative">
          <div className="pointer-events-none absolute inset-x-0 top-0" style={{ height: PLOT_H }}>
            {[100, 75, 50, 25, 0].map((v) => (
              <div key={v} className="absolute inset-x-0 flex translate-y-1/2 items-center gap-2" style={{ bottom: `${v}%` }}>
                <span className="w-9 text-right text-[11px] tabular-nums text-muted-foreground">{v}%</span>
                <div className={cn('flex-1 border-t', v === 0 ? 'border-slate-300' : 'border-dashed border-border')} />
              </div>
            ))}
          </div>

          <div className="relative flex pl-11">
            {entries.map(({ key, meta, pred }, i) => {
              const Icon = meta.icon
              const isSel = selected === key
              const p = Math.min(1, Math.max(0, pred.probability))
              const pct = Math.round(p * 100)
              return (
                <button key={key} type="button" onClick={() => onSelect(isSel ? null : key)}
                  aria-expanded={isSel}
                  aria-label={`${meta.name}: ${pct}%. ${pred.positive ? 'Вероятен' : 'Маловероятен'}. Показать вклады признаков`}
                  style={{ '--c': meta.color, background: isSel ? 'color-mix(in oklab, var(--c) 9%, transparent)' : undefined } as React.CSSProperties}
                  className="group min-w-0 flex-1 rounded-xl px-1 pb-3 transition-colors hover:bg-[color-mix(in_oklab,var(--c)_6%,transparent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <div className="relative" style={{ height: PLOT_H }}>
                    <motion.div
                      className="absolute bottom-0 left-1/2 -ml-[34px] w-[52px]"
                      initial={{ height: '0%' }}
                      animate={{ height: `${Math.max(p * 100, 1.5)}%` }}
                      transition={{ type: 'spring', stiffness: 70, damping: 16, delay: 0.1 + i * 0.09 }}
                      whileHover={{ y: -3 }}>
                      <div className="col3d"
                        style={{
                          filter: pred.positive
                            ? 'drop-shadow(0 8px 12px color-mix(in oklab, var(--c) 40%, transparent))'
                            : 'saturate(0.55) opacity(0.7)',
                        }} />
                      <motion.span
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 + i * 0.09 }}
                        className={cn('absolute left-1/2 -translate-x-1/2 whitespace-nowrap text-lg font-bold tabular-nums', !pred.positive && 'opacity-70')}
                        style={{ bottom: 'calc(100% + 22px)', color: meta.color }}>
                        {pct === 0 && p > 0 ? '<1' : pct}%
                      </motion.span>
                    </motion.div>
                  </div>
                  <div className="mt-3 flex flex-col items-center gap-1.5 text-center">
                    <span className="grid size-9 place-items-center rounded-xl text-white shadow-sm" style={{ background: meta.color }}>
                      <Icon className="size-5" />
                    </span>
                    <span className="text-xs font-medium leading-tight">{meta.short}</span>
                    <span className={cn('rounded-full px-2 py-0.5 text-[11px] font-medium',
                      pred.positive ? 'bg-red-50 text-red-700 ring-1 ring-red-200' : 'bg-muted text-muted-foreground')}>
                      {pred.positive ? 'Вероятен' : 'Маловероятен'}
                    </span>
                    <ChevronDown className={cn('size-4 text-muted-foreground transition-transform', isSel && 'rotate-180')} />
                  </div>
                </button>
              )
            })}
          </div>
        </div>
        <p className="mt-2 pl-11 text-xs text-muted-foreground">
          Вероятность<Fn n={1} />, метки «вероятен / маловероятен»<Fn n={2} />. Нажмите на столбец — раскроются вклады признаков.
        </p>
      </div>
    </div>
  )
}