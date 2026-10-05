// Типы зеркалят Pydantic-схемы бэкенда (intake/schemas.py, common/schemas.py). JSON — snake_case.
export type Role = 'doctor' | 'patient' | 'admin'
export type Sex = 'M' | 'F'
export type TriageStatus = 'anemia' | 'latent' | 'normal'
export type TriageFilter = 'all' | TriageStatus
export type AnalysisStatus = 'RECEIVED' | 'PROCESSING' | 'DONE' | 'FAILED'

export type Condition =
  | 'iron_deficiency' | 'B12_deficiency' | 'folate_deficiency' | 'B6_deficiency'
  | 'copper_deficiency' | 'inflammation_anemia' | 'mixed_deficiency'

export type AnemiaClass =
  | 'B12_deficiency_anemia' | 'B12_deficiency_no_anemia' | 'B6_deficiency' | 'copper_deficiency'
  | 'folate_deficiency_anemia' | 'folate_deficiency_no_anemia' | 'inflammation_anemia'
  | 'iron_deficiency_anemia' | 'latent_deficiency' | 'mixed_deficiency'
  | 'no_anemia_no_deficiency' | 'anemia_other'

export type DeficiencyCause =
  | 'B12_deficiency' | 'B12_folate' | 'B6_deficiency' | 'copper_deficiency' | 'folate_deficiency'
  | 'inflammation' | 'iron_B12' | 'iron_deficiency' | 'iron_folate' | 'none' | 'undetermined'

// ── аутентификация ──
export interface TokenResponse {
  access_token: string
  token_type: string
  role: Role
  auth_id: string
  expires_in: number
}

// ── пациенты ──
export interface Contacts { phone?: string | null; email?: string | null }

export interface PatientCreate {
  full_name: string
  age: number
  sex: Sex
  oms?: string
  contacts?: Contacts
}

export interface PatientListItem {
  patient_id: string
  full_name: string | null
  age: number
  sex: Sex
  oms: string | null
  triage_status: TriageStatus | null
  last_analysis_at: string | null
}

export interface Page<T> { items: T[]; total: number; limit: number; offset: number }
export type PatientPage = Page<PatientListItem>

export interface LastAnalysis {
  analysis_id: string
  created_at: string
  triage_status: TriageStatus | null
  anemia_class: AnemiaClass | null
  deficiency_cause: DeficiencyCause | null
}

export interface ClinicalSummary {
  triage_status: TriageStatus | null
  analyses_total: number
  analyses_in_progress: number
  last_analysis: LastAnalysis | null
}

export interface PatientProfile {
  patient_id: string
  full_name: string | null
  age: number
  sex: Sex
  oms: string | null
  contacts: Contacts | null
  created_at: string
  clinical_summary: ClinicalSummary
}

// ── анализы ──
export interface AnalysisRequest { biomarkers: Record<string, number>; pregnant: boolean }
export interface AnalysisAccepted { analysis_id: string; status: AnalysisStatus }

export interface AnalysisListItem {
  analysis_id: string
  status: AnalysisStatus
  created_at: string
  error_code: string | null
  triage_status: TriageStatus | null
  anemia_class: AnemiaClass | null
  deficiency_cause: DeficiencyCause | null
}
export type AnalysisPage = Page<AnalysisListItem>

// Результат ML.
// Поля помечены `?` там, где бэкенд-заглушка rules-0.1-draft их может не вернуть,
// а будущая ML-модель вернёт больше. Компоненты-потребители обязаны уметь
// работать с undefined (см. topFeatures, buildKeyFeatures, ResultView).
export interface FeatureContribution {
  feature: string
  value: number | string | null
  contribution: number
}
export interface KeyFeature {
  feature: string; label: string; unit: string; value: number | string | null
  contribution: number; importance: number; direction: 'supports' | 'opposes'
}
export interface ConditionPrediction {
  probability: number
  positive: boolean
  has_evidence?: boolean
  top_features?: FeatureContribution[]
}
export interface AnalysisResult {
  case_token?: string
  model_version?: string
  anemia_detected: boolean
  hemoglobin_threshold: number
  predictions: Partial<Record<Condition, ConditionPrediction>>
  anemia_class?: AnemiaClass
  deficiency_cause?: DeficiencyCause
  key_features?: KeyFeature[]
  missing_features?: string[]
}
export interface AnalysisStatusResponse {
  analysis_id: string; status: AnalysisStatus
  result: AnalysisResult | null; error_code: string | null; created_at: string | null
}