import { CONTRIBUTION_SCALE } from '@/lib/config'
import { Card } from '@/components/ui/card'
import { BookOpen } from 'lucide-react'

const go = (n: number) => (e: React.MouseEvent) => {
  e.preventDefault()
  document.getElementById(`fn-${n}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

export function Fn({ n }: { n: number }) {
  return (
    <sup>
      <a href={`#fn-${n}`} onClick={go(n)} title="Пояснение внизу страницы"
        className="ml-0.5 rounded px-0.5 font-semibold text-primary hover:bg-primary/10">{n}</a>
    </sup>
  )
}

const ITEMS: { n: number; term: string; text: string }[] = [
  { n: 1, term: 'Вероятность',
    text: 'Оценка модели (0–100 %), что у пациента есть данный дефицит, по введённым показателям. Это вероятность, а не диагноз. Если ключевые маркеры дефицита не измерены, оценка помечается как априорная — такому выводу доверять нельзя.' },
  { n: 2, term: '«Вероятен» / «Маловероятен»',
    text: 'Метка «Вероятен» ставится, когда вероятность достигает порога, подобранного для этого дефицита при валидации модели. Он не обязан равняться 50 %.' },
  { n: 3, term: 'Вклад признака (SHAP)',
    text: 'Насколько значение конкретного показателя сдвинуло оценку модели у этого пациента относительно базового уровня. Красный — повышает вероятность дефицита, синий — понижает; длина столбика пропорциональна величине сдвига. Это объяснение работы модели, а не причинно-следственная связь.' },
  { n: 4, term: 'Базовый уровень и f(x)',
    text: 'Базовый уровень — оценка, которую модель выдала бы «в среднем», не зная показателей пациента. Идя снизу вверх, вклады прибавляются, и график приходит к итоговой вероятности f(x). Вклад признаков, не попавших на график, включён в стартовую точку.'
      + (CONTRIBUTION_SCALE === 'logit' ? ' Модель считает вклады в лог-шансах; по умолчанию они пересчитаны в вероятность, а переключатель «Лог-шансы» показывает исходные значения.' : '') },
  { n: 5, term: 'Почему 5–7 признаков',
    text: 'Для каждого вывода показаны от 5 до 7 наиболее значимых признаков — столько элементов человек способен удерживать в рабочей памяти. Остальные признаки модель учла, но на график они не выводятся.' },
]

export function Footnotes() {
  return (
    <Card className="p-5">
      <h2 className="mb-3 flex items-center gap-2 text-base font-semibold">
        <BookOpen className="size-4 text-primary" /> Как читать результат
      </h2>
      <ol className="space-y-2.5 text-sm text-muted-foreground">
        {ITEMS.map((i) => (
          <li key={i.n} id={`fn-${i.n}`} className="flex gap-3 scroll-mt-24">
            <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-primary/10 text-xs font-semibold text-primary">{i.n}</span>
            <span><b className="font-medium text-foreground">{i.term}.</b> {i.text}</span>
          </li>
        ))}
      </ol>
      <p className="mt-4 border-t border-border pt-3 text-xs text-muted-foreground">
        Результат — инструмент поддержки врачебного решения и не заменяет клиническую оценку.
      </p>
    </Card>
  )
}