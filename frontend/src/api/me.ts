import { api } from './client'
import type { AnalysisPage, AnalysisStatusResponse, PatientProfile } from '@/types/api'

import type { AnalysisAccepted, AnalysisRequest } from '@/types/api'

export const createMyAnalysis = (body: AnalysisRequest) =>
  api.post<AnalysisAccepted>('/api/v1/me/analyses', body).then((r) => r.data)

export const getMe = () =>
  api.get<PatientProfile>('/api/v1/me').then((r) => r.data)

export const listMyAnalyses = (limit = 20, offset = 0) =>
  api.get<AnalysisPage>('/api/v1/me/analyses', { params: { limit, offset } }).then((r) => r.data)

export const getMyAnalysis = (analysisId: string) =>
  api.get<AnalysisStatusResponse>(`/api/v1/me/analyses/${analysisId}`).then((r) => r.data)