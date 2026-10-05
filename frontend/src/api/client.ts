import axios from 'axios'
import { useAuth } from '@/auth/store'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  timeout: 20_000,
})

api.interceptors.request.use((config) => {
  const token = useAuth.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (error) => {
    // Токен истёк / недействителен → на экран входа
    if (axios.isAxiosError(error) && error.response?.status === 401 && useAuth.getState().token) {
      useAuth.getState().logout()
      window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)

const CODES: Record<string, string> = {
  duplicate_oms: 'Пациент с таким номером ОМС уже зарегистрирован',
  pregnancy_requires_female: 'Беременность можно указать только для пола «Ж»',
}

/** Человекочитаемое сообщение из ошибки API. */
export function errorMessage(e: unknown): string {
  if (axios.isAxiosError(e)) {
    if (!e.response) return 'Нет связи с сервером. Проверьте, что бэкенд запущен'
    const { status, data } = e.response
    if (status === 403) return 'Доступ запрещён'
    if (status === 404) return 'Не найдено'
    const detail = data?.detail
    if (typeof detail === 'string') return CODES[detail] ?? detail
    if (status === 422 && Array.isArray(detail))
      return 'Сервер отклонил данные: ' + detail.map((d: { loc: (string | number)[]; msg: string }) => `${d.loc.slice(1).join('.')} — ${d.msg}`).join('; ')
  }
  return 'Что-то пошло не так. Попробуйте ещё раз'
}
