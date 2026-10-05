import { useMemo } from 'react'
import { motion } from 'motion/react'
import { buildWaterfall } from '@/lib/shap'
import { featureInfo, fmtSigned, fmtValue } from '@/lib/conditions'
import type { Scale } from '@/lib/config'
import type { FeatureContribution } from '@/types/api'

const RED = '#d4505c'
const BLUE = '#5a86f0'
const W = 780, LW = 262, PX0 = 276, PX1 = 742, RH = 46, TOP = 38, BAR_H = 30

interface Props { features: FeatureContribution[]; probability: number; dataScale: Scale; view: Scale }

export function ShapWaterfall({ features, probability, dataScale, view }: Props) {
  const wf = useMemo(() => buildWaterfall(features, probability, dataScale, view), [features, probability, dataScale, view])
  const n = wf.rows.length
  const axisY = TOP + n * RH + 8
  const H = axisY + 52
  const x = (v: number) => PX0 + ((v - wf.d0) / (wf.d1 - wf.d0)) * (PX1 - PX0)
  const fmt = (v: number) => v.toFixed(2).replace('.', ',')
  const clampX = (v: number) => Math.min(W - 40, Math.max(PX0 - 10, v))

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full min-w-[640px]" role="img"
        aria-label="График вкладов признаков в итоговую вероятность">
        <line x1={x(wf.end)} x2={x(wf.end)} y1={TOP - 8} y2={axisY} stroke="#94a3b8" strokeDasharray="3 3" />
        <text x={clampX(x(wf.end))} y={TOP - 16} textAnchor="middle" fontSize="13" fill="currentColor" fontWeight="600">
          f(x) = {fmt(wf.end)}
        </text>
        <line x1={x(wf.start)} x2={x(wf.start)} y1={TOP + (n - 1) * RH + RH / 2 - 4} y2={axisY + 14} stroke="#94a3b8" strokeDasharray="3 3" />

        {wf.rows.map((r, i) => {
          const cy = TOP + i * RH + RH / 2
          const delta = r.to - r.from
          const up = r.raw >= 0
          const a = x(r.from)
          let b = x(r.to)
          if (Math.abs(b - a) < 2.5) b = a + (up ? 2.5 : -2.5)
          const w = Math.abs(b - a)
          const t = Math.min(9, w * 0.7)
          const dir = up ? 1 : -1
          const pts = [[a, cy - BAR_H / 2], [b - dir * t, cy - BAR_H / 2], [b, cy], [b - dir * t, cy + BAR_H / 2], [a, cy + BAR_H / 2]]
            .map((p) => p.join(',')).join(' ')
          const inside = w > 52
          const label = fmtSigned(wf.view === 'logit' ? r.raw : delta)
          const info = featureInfo(r.feature)
          const color = up ? RED : BLUE
          return (
            <motion.g key={r.feature}
              initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: (n - 1 - i) * 0.07, duration: 0.35 }}>
              <title>{`${info.label}: ${fmtValue(r.value)} ${info.unit}`.trim() + ` — вклад ${label}`}</title>
              <line x1={LW + 8} x2={PX1 + 10} y1={cy} y2={cy} stroke="#e2e8f0" strokeDasharray="1 4" />
              {i > 0 && <line x1={x(r.to)} x2={x(r.to)} y1={cy - RH + BAR_H / 2} y2={cy - BAR_H / 2} stroke="#cbd5e1" strokeDasharray="2 3" />}
              <polygon points={pts} fill={color} />
              <text x={inside ? (a + b) / 2 : b + dir * 8} y={cy + 5} fontSize="13" fontWeight="600"
                textAnchor={inside ? 'middle' : up ? 'start' : 'end'} fill={inside ? '#fff' : color}>{label}</text>
              <text x={LW} y={cy - 2} textAnchor="end" fontSize="14">
                <tspan fill="#94a3b8">{fmtValue(r.value)} = </tspan>
                <tspan fill="currentColor" fontWeight="600">{r.feature}</tspan>
              </text>
              <text x={LW} y={cy + 13} textAnchor="end" fontSize="11" fill="#94a3b8">
                {info.label}{info.unit ? ` · ${info.unit}` : ''}
              </text>
            </motion.g>
          )
        })}

        <line x1={PX0 - 10} x2={PX1 + 10} y1={axisY} y2={axisY} stroke="#334155" />
        {wf.ticks.map((tk) => (
          <g key={tk}>
            <line x1={x(tk)} x2={x(tk)} y1={axisY} y2={axisY + 5} stroke="#334155" />
            <text x={x(tk)} y={axisY + 20} textAnchor="middle" fontSize="12" fill="#475569">
              {String(tk).replace('.', ',')}
            </text>
          </g>
        ))}
        <text x={clampX(x(wf.start))} y={axisY + 42} textAnchor="middle" fontSize="12" fill="#475569">
          Базовый уровень = {fmt(wf.start)}
        </text>
      </svg>
    </div>
  )
}