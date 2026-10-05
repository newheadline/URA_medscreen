import { useMemo, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import Papa from 'papaparse'
import { Download, FileSpreadsheet, Loader2, PencilLine, Send, UploadCloud } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErrorNote } from '@/components/ui/notes'
import { LAB_FIELDS, LAB_KEYS, emptyLabs, labsSchema, normalizeNum, type RawLabs } from '@/lib/labs'
import { cn } from '@/lib/utils'

interface Props {
  submitting: boolean
  onSubmit: (raw: RawLabs) => void
  onEdit: (raw: RawLabs) => void     // открыть строку в ручной форме для правки
}

interface Parsed { fileName: string; rows: RawLabs[]; ignored: string[]; hasHemoglobin: boolean }

// Регистр и пробелы в заголовках не важны, имена столбцов = ключи API (hemoglobin, RBC, ferritin…)
const KEYMAP = Object.fromEntries(LAB_KEYS.map((k) => [k.toLowerCase(), k]))
const MAX_ROWS = 200

function downloadTemplate() {
  const csv = LAB_KEYS.join(',') + '\n' + LAB_KEYS.map(() => '').join(',') + '\n'
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: 'labs_template.csv' })
  a.click()
  URL.revokeObjectURL(url)
}

export function LabsCsvDrop({ submitting, onSubmit, onEdit }: Props) {
  const [parsed, setParsed] = useState<Parsed | null>(null)
  const [rowIdx, setRowIdx] = useState(0)
  const [parseError, setParseError] = useState<string | null>(null)

  const onDrop = (files: File[]) => {
    const file = files[0]
    if (!file) return
    setParseError(null)
    Papa.parse<Record<string, string>>(file, {
      header: true,
      skipEmptyLines: 'greedy',
      preview: MAX_ROWS,
      transformHeader: (h) => h.replace(/^\ufeff/, '').trim(),
      complete: (res) => {
        const headers = res.meta.fields ?? []
        const ignored = headers.filter((h) => !KEYMAP[h.toLowerCase()])
        const rows = res.data.map((r) => {
          const out = emptyLabs()
          for (const [h, v] of Object.entries(r)) {
            const key = KEYMAP[h.toLowerCase()]
            if (key) out[key] = String(v ?? '').trim()
          }
          return out
        })
        if (!rows.length) return setParseError('В файле нет строк с данными')
        setParsed({ fileName: file.name, rows, ignored, hasHemoglobin: headers.some((h) => h.toLowerCase() === 'hemoglobin') })
        setRowIdx(0)
      },
      error: (e) => setParseError(`Не удалось прочитать файл: ${e.message}`),
    })
  }

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    multiple: false,
    maxSize: 2 * 1024 * 1024,
    accept: { 'text/csv': ['.csv'], 'text/plain': ['.csv', '.txt'], 'application/vnd.ms-excel': ['.csv'] },
  })

  const raw = parsed?.rows[rowIdx]
  const issues = useMemo(() => {
    if (!raw) return {} as Record<string, string>
    const res = labsSchema.safeParse(raw)
    const out: Record<string, string> = {}
    if (!res.success) for (const i of res.error.issues) out[String(i.path[0])] = i.message
    return out
  }, [raw])

  const filled = raw ? LAB_FIELDS.filter((f) => normalizeNum(raw[f.key]) !== '') : []
  const invalid = Object.keys(issues).length > 0

  return (
    <div className="space-y-4">
      {!parsed && (
        <>
          <div
            {...getRootProps()}
            className={cn(
              'grid cursor-pointer place-items-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors',
              isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/60',
            )}
          >
            <input {...getInputProps()} />
            <UploadCloud className="size-8 text-muted-foreground" />
            <p className="text-sm font-medium">Перетащите CSV сюда или нажмите для выбора</p>
            <p className="text-xs text-muted-foreground">
              Одна строка — один пациент; заголовки — названия показателей (hemoglobin, ferritin, …). До 2 МБ
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={downloadTemplate}>
            <Download className="size-4" /> Скачать шаблон CSV
          </Button>
        </>
      )}

      {parseError && <ErrorNote>{parseError}</ErrorNote>}
      {fileRejections.length > 0 && !parsed && <ErrorNote>Подходит только файл .csv размером до 2 МБ</ErrorNote>}

      {parsed && raw && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted px-3 py-2 text-sm">
            <span className="flex items-center gap-2 font-medium">
              <FileSpreadsheet className="size-4 text-primary" /> {parsed.fileName}
            </span>
            <button type="button" onClick={() => { setParsed(null); setParseError(null) }} className="text-xs text-primary hover:underline">
              Выбрать другой файл
            </button>
          </div>

          {parsed.rows.length > 1 && (
            <label className="flex items-center gap-2 text-sm">
              В файле строк: {parsed.rows.length}. Использовать строку
              <select
                value={rowIdx}
                onChange={(e) => setRowIdx(Number(e.target.value))}
                className="h-9 rounded-lg border border-border bg-card px-2"
              >
                {parsed.rows.map((_, i) => <option key={i} value={i}>{i + 1}</option>)}
              </select>
            </label>
          )}

          {!parsed.hasHemoglobin && <ErrorNote>В файле нет столбца hemoglobin — без гемоглобина скрининг невозможен</ErrorNote>}
          {parsed.ignored.length > 0 && (
            <p className="text-xs text-muted-foreground">Столбцы не распознаны и будут проигнорированы: {parsed.ignored.join(', ')}</p>
          )}

          <div>
            <p className="mb-2 text-sm font-medium">Распознано показателей: {filled.length} из {LAB_FIELDS.length}</p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {filled.map((f) => (
                <div key={f.key} className={cn('rounded-lg border px-3 py-2 text-sm', issues[f.key] ? 'border-destructive/50 bg-red-50' : 'border-border bg-card')}>
                  <div className="text-xs text-muted-foreground">{f.label}</div>
                  <div className="font-medium">{raw[f.key]} <span className="text-xs font-normal text-muted-foreground">{f.unit}</span></div>
                  {issues[f.key] && <div className="text-xs text-destructive">{issues[f.key]}</div>}
                </div>
              ))}
            </div>
            {issues.hemoglobin && !filled.some((f) => f.key === 'hemoglobin') && (
              <div className="mt-2"><ErrorNote>Гемоглобин в выбранной строке не заполнен</ErrorNote></div>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button size="lg" disabled={invalid || submitting} onClick={() => onSubmit(raw)}>
              {submitting ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              Отправить на скрининг
            </Button>
            <Button size="lg" variant="outline" onClick={() => onEdit(raw)}>
              <PencilLine className="size-4" /> Править вручную
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
