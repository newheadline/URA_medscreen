import { api } from './client'
import type { Role, TokenResponse } from '@/types/api'

// DEMO ONLY: на бэкенде эндпоинт включён флагом DEMO_LOGIN_ENABLED
export const demoLogin = (role: Exclude<Role, 'admin'>) =>
  api.post<TokenResponse>('/api/v1/auth/demo-login', { role }).then((r) => r.data)
