import { api } from './client'
import type { AnalysisAccepted, AnalysisPage, AnalysisRequest, AnalysisStatusResponse } from '@/types/api'

export const listAnalyses = (patientId: string, limit = 20, offset = 0) =>
  api.get<AnalysisPage>(`/api/v1/patients/${patientId}/analyses`, { params: { limit, offset } }).then((r) => r.data)

export const createAnalysis = (patientId: string, body: AnalysisRequest) =>
  api.post<AnalysisAccepted>(`/api/v1/patients/${patientId}/analyses`, body).then((r) => r.data)

// Понадобится на шаге с результатом (поллинг статуса + вероятности + SHAP)
export const getAnalysis = (patientId: string, analysisId: string) =>
  api.get<AnalysisStatusResponse>(`/api/v1/patients/${patientId}/analyses/${analysisId}`).then((r) => r.data)
