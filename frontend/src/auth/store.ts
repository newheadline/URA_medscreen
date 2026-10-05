import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { Role } from '@/types/api'

interface AuthState {
  token: string | null
  role: Role | null
  login: (token: string, role: Role) => void
  logout: () => void
}

// sessionStorage: токен живёт до закрытия вкладки — для медданных безопаснее localStorage
export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      login: (token, role) => set({ token, role }),
      logout: () => set({ token: null, role: null }),
    }),
    { name: 'medscreen-auth', storage: createJSONStorage(() => sessionStorage) },
  ),
)

export const homeFor = (role: Role | null) =>
  role === 'doctor' ? '/doctor' : role === 'patient' ? '/patient' : '/login'
