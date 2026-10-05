import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { z } from 'zod'
import { createPatient } from '@/api/patients'
import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ErrorNote, FieldError } from '@/components/ui/notes'
import type { PatientCreate, PatientProfile } from '@/types/api'

// Правила зеркалят PatientCreate / Contacts на бэкенде (intake/schemas.py)
const schema = z.object({
  full_name: z.string().trim().min(2, 'Минимум 2 символа').max(200),
  age: z.string().regex(/^\d{1,3}$/, 'Введите возраст').refine((v) => +v >= 18 && +v <= 120, 'Допустимо 18–120 лет'),
  sex: z.enum(['M', 'F'], { errorMap: () => ({ message: 'Укажите пол' }) }),
  oms: z.string().trim().refine((v) => v === '' || /^[0-9A-Za-z]{6,32}$/.test(v.replace(/[\s-]/g, '')), 'ОМС: 6–32 буквы/цифры'),
  phone: z.string().trim().refine((v) => v === '' || /^[+0-9()\-\s]{5,32}$/.test(v), 'Некорректный телефон'),
  email: z.string().trim().refine((v) => v === '' || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v), 'Некорректный email'),
})
type FormValues = z.infer<typeof schema>

export function CreatePatientForm({ onCreated, onCancel }: { onCreated: (p: PatientProfile) => void; onCancel: () => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: '', age: '', oms: '', phone: '', email: '' },
  })

  const mutation = useMutation({ mutationFn: createPatient, onSuccess: onCreated })

  const onSubmit = (v: FormValues) => {
    const contacts = { ...(v.phone && { phone: v.phone }), ...(v.email && { email: v.email }) }
    const body: PatientCreate = {
      full_name: v.full_name,
      age: Number(v.age),
      sex: v.sex,
      ...(v.oms && { oms: v.oms }),
      ...(Object.keys(contacts).length && { contacts }),
    }
    mutation.mutate(body)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="rounded-xl border border-border bg-muted/40 p-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-6">
        <label className="sm:col-span-3">
          <span className="mb-1 block text-xs font-medium">ФИО *</span>
          <Input {...register('full_name')} aria-invalid={!!errors.full_name} placeholder="Иванова Мария Сергеевна" autoFocus />
          <FieldError message={errors.full_name?.message} />
        </label>
        <label className="sm:col-span-1">
          <span className="mb-1 block text-xs font-medium">Возраст *</span>
          <Input {...register('age')} aria-invalid={!!errors.age} inputMode="numeric" placeholder="42" />
          <FieldError message={errors.age?.message} />
        </label>
        <fieldset className="sm:col-span-2">
          <legend className="mb-1 text-xs font-medium">Пол *</legend>
          <div className="grid grid-cols-2 gap-2">
            {(['M', 'F'] as const).map((s) => (
              <label key={s}>
                <input type="radio" value={s} {...register('sex')} className="peer sr-only" />
                <span className="flex h-10 cursor-pointer items-center justify-center rounded-lg border border-border bg-card text-sm peer-checked:border-primary peer-checked:bg-primary/5 peer-checked:font-medium peer-focus-visible:ring-2 peer-focus-visible:ring-ring">
                  {s === 'M' ? 'Мужской' : 'Женский'}
                </span>
              </label>
            ))}
          </div>
          <FieldError message={errors.sex?.message} />
        </fieldset>
        <label className="sm:col-span-2">
          <span className="mb-1 block text-xs font-medium">Полис ОМС</span>
          <Input {...register('oms')} aria-invalid={!!errors.oms} placeholder="необязательно" />
          <FieldError message={errors.oms?.message} />
        </label>
        <label className="sm:col-span-2">
          <span className="mb-1 block text-xs font-medium">Телефон</span>
          <Input {...register('phone')} aria-invalid={!!errors.phone} placeholder="+7 900 000-00-00" />
          <FieldError message={errors.phone?.message} />
        </label>
        <label className="sm:col-span-2">
          <span className="mb-1 block text-xs font-medium">Email</span>
          <Input {...register('email')} aria-invalid={!!errors.email} placeholder="name@example.com" />
          <FieldError message={errors.email?.message} />
        </label>
      </div>

      {mutation.isError && <div className="mt-4"><ErrorNote>{errorMessage(mutation.error)}</ErrorNote></div>}

      <div className="mt-4 flex gap-2">
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending && <Loader2 className="size-4 animate-spin" />} Создать и открыть
        </Button>
        <Button variant="ghost" onClick={onCancel}>Отмена</Button>
      </div>
    </form>
  )
}
