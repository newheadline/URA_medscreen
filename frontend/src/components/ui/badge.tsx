import { cn } from '@/lib/utils'
import type { TriageStatus } from '@/types/api'

export const Badge = ({ className, ...p }: React.HTMLAttributes<HTMLSpanElement>) => (
  <span className={cn('inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium', className)} {...p} />
)

const TRIAGE: Record<TriageStatus, { label: string; cls: string }> = {
  anemia: { label: 'Анемия', cls: 'bg-red-50 text-red-700 ring-1 ring-red-200' },
  latent: { label: 'Скрытый дефицит', cls: 'bg-amber-50 text-amber-800 ring-1 ring-amber-200' },
  normal: { label: 'Норма', cls: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200' },
}

export function TriageBadge({ status }: { status: TriageStatus | null | undefined }) {
  if (!status) return <Badge className="bg-muted text-muted-foreground">Нет анализов</Badge>
  const t = TRIAGE[status]
  return <Badge className={t.cls}>{t.label}</Badge>
}
