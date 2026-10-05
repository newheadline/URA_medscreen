import { ResultView } from '@/components/results/ResultView'
import { CONTRIBUTION_SCALE } from '@/lib/config'
import { sampleResult } from '@/mocks/SampleResult'

export default function DemoResult() {
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold tracking-tight">
        Результат скрининга <span className="text-sm font-normal text-muted-foreground">(демо-данные)</span>
      </h1>
      <ResultView result={sampleResult(CONTRIBUTION_SCALE)} />
    </div>
  )
}