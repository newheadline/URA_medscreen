import { AlertCircle } from 'lucide-react'

export const ErrorNote = ({ children }: { children: React.ReactNode }) => (
  <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
    <AlertCircle className="mt-0.5 size-4 shrink-0" />
    <span>{children}</span>
  </div>
)

export const FieldError = ({ message }: { message?: string }) =>
  message ? <p className="mt-1 text-xs text-destructive">{message}</p> : null
