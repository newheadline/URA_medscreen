import type { AnalysisResult, ConditionPrediction, FeatureContribution } from '@/types/api'
import type { Scale } from '@/lib/config'

const feat = (feature: string, value: number | string, contribution: number): FeatureContribution =>
  ({ feature, value, contribution })

const mk = (probability: number, positive: boolean, top: FeatureContribution[], has_evidence = true): ConditionPrediction =>
  ({ probability, positive, has_evidence, top_features: top })

export function sampleResult(scale: Scale = 'logit'): AnalysisResult {
  const k = scale === 'logit' ? 1 : 0.17
  const f = (n: string, v: number | string, c: number) => feat(n, v, +(c * k).toFixed(3))
  return {
    case_token: 'demo', model_version: 'demo-0.1',
    anemia_detected: false, hemoglobin_threshold: 130,
    anemia_class: 'latent_deficiency', deficiency_cause: 'iron_deficiency',
    predictions: {
      iron_deficiency: mk(0.74, true, [
        f('MCH', 26.4, 0.85), f('RDW', 15.6, 0.72), f('MCV', 81.4, 0.64), f('RBC', 5.69, 0.3),
        f('hematocrit', 46.8, 0.18), f('sex', 0, -0.16), f('hemoglobin', 150.5, 0.11),
        f('WBC', 6.94, 0.05), f('platelets', 364, -0.03),
      ]),
      B12_deficiency: mk(0.18, false, [
        f('vitamin_B12', 410, -0.62), f('MCV', 81.4, -0.4), f('homocysteine', 9.8, -0.25),
        f('RDW', 15.6, 0.22), f('age_years', 28, -0.1), f('hemoglobin', 150.5, -0.06),
      ]),
      folate_deficiency: mk(0.09, false, [
        f('folate', 9.1, -0.8), f('MCV', 81.4, -0.35), f('RDW', 15.6, 0.18),
        f('hemoglobin', 150.5, -0.12), f('age_years', 28, -0.07),
      ], false),
      B6_deficiency: mk(0.41, true, [
        f('vitamin_B6', 21, 0.55), f('hemoglobin', 150.5, -0.3), f('MCH', 26.4, 0.28),
        f('albumin', 41, -0.2), f('CRP', 3.1, 0.14), f('age_years', 28, 0.05),
      ]),
      copper_deficiency: mk(0.05, false, [
        f('copper', 15.2, -0.9), f('ceruloplasmin', 0.31, -0.4), f('WBC', 6.94, -0.15),
        f('hemoglobin', 150.5, -0.1), f('sex', 0, 0.06),
      ]),
    },
    missing_features: ['ferritin', 'TSAT', 'MMA', 'reticulocytes'],
    key_features: [],
  }
}