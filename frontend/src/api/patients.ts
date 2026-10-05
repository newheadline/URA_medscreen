import { api } from './client'
import type { PatientCreate, PatientPage, PatientProfile, TriageFilter } from '@/types/api'

export interface PatientsQuery { search?: string; triage?: TriageFilter; limit?: number; offset?: number }

export const listPatients = (p: PatientsQuery) =>
  api.get<PatientPage>('/api/v1/patients', {
    params: { search: p.search || undefined, triage: p.triage ?? 'all', limit: p.limit ?? 20, offset: p.offset ?? 0 },
  }).then((r) => r.data)

export const getPatient = (id: string) =>
  api.get<PatientProfile>(`/api/v1/patients/${id}`).then((r) => r.data)

export const createPatient = (body: PatientCreate) =>
  api.post<PatientProfile>('/api/v1/patients', body).then((r) => r.data)
