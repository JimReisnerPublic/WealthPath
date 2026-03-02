export type SuccessLabel = 'on track' | 'at risk' | 'critical'

export interface HouseholdProfile {
  age: number
  income: number
  net_worth: number
  investable_savings: number
  household_size: number
  home_equity: number
  debt: number
}

export interface EvaluationRequest {
  household: HouseholdProfile
  planned_retirement_age: number
  life_expectancy: number
  annual_spending_retirement: number
  social_security_annual: number
  equity_fraction: number
  savings_rate: number
}

export interface FeatureDriver {
  feature: string
  display_name: string
  shap_value: number
  direction: 'positive' | 'negative'
}

export interface EvaluationResponse {
  success_probability: number
  success_label: SuccessLabel
  top_drivers: FeatureDriver[]
  data_source: string
  model_metrics: Record<string, number> | null
}

// Cohort comparison — mirrors the Pydantic models in models/cohort.py
export interface CohortRequest {
  household: HouseholdProfile
  compare_fields: string[]
}

export interface CohortStats {
  field: string
  user_value: number
  cohort_median: number
  cohort_p25: number
  cohort_p75: number
  percentile_rank: number  // 0–100
}

export interface CohortResponse {
  cohort_size: number
  cohort_description: string
  stats: CohortStats[]
}
