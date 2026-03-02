/**
 * Example households for the "Load a scenario" feature.
 *
 * TO ADD OR EDIT A SCENARIO: only this file needs to change.
 * All dollar values are annual USD. Fractions (equity_fraction, savings_rate) are 0–1.
 * employer_match_rate and employer_match_ceiling are percentages (0–100).
 */

import type { FormState } from '@/components/PlanForm'

export interface ScenarioDefinition {
  label: string         // Short name on the pill button
  description: string   // One-sentence tooltip / subtitle
  // About You
  age: number
  household_size: number
  // Your Finances
  income: number
  net_worth: number
  investable_savings: number
  home_equity: number
  debt: number
  // Retirement Plan
  planned_retirement_age: number
  life_expectancy: number
  annual_spending_retirement: number
  // Guaranteed Income (annual)
  social_security_annual: number
  social_security_start_age: number
  pension_annual: number
  other_income_annual: number
  // Investment Strategy
  equity_fraction: number   // 0.0–1.0
  savings_rate: number      // 0.0–0.80
  employer_match_rate: number    // 0–100 (percent)
  employer_match_ceiling: number // 0–20 (percent of income)
}

/** Convert a ScenarioDefinition into the PlanForm internal state. */
export function scenarioToFormState(s: ScenarioDefinition): FormState {
  return {
    age: String(s.age),
    household_size: String(s.household_size),
    income: String(s.income),
    net_worth: String(s.net_worth),
    investable_savings: String(s.investable_savings),
    home_equity: String(s.home_equity),
    debt: String(s.debt),
    planned_retirement_age: String(s.planned_retirement_age),
    life_expectancy: String(s.life_expectancy),
    annual_spending_retirement: String(s.annual_spending_retirement),
    income_frequency: 'annual',
    social_security: s.social_security_annual > 0 ? String(s.social_security_annual) : '',
    social_security_start_age: String(s.social_security_start_age),
    pension: s.pension_annual > 0 ? String(s.pension_annual) : '',
    other_income: s.other_income_annual > 0 ? String(s.other_income_annual) : '',
    equity_fraction: s.equity_fraction,
    savings_rate: s.savings_rate,
    employer_match_rate: s.employer_match_rate > 0 ? String(s.employer_match_rate) : '',
    employer_match_ceiling: s.employer_match_ceiling > 0 ? String(s.employer_match_ceiling) : '',
  }
}

export const SCENARIOS: ScenarioDefinition[] = [
  {
    label: 'Just Starting Out',
    description: '28-year-old with $65k income, early in their savings journey.',
    age: 28,
    household_size: 1,
    income: 65_000,
    net_worth: 5_000,
    investable_savings: 8_000,
    home_equity: 0,
    debt: 18_000,
    planned_retirement_age: 65,
    life_expectancy: 88,
    annual_spending_retirement: 50_000,
    social_security_annual: 20_000,
    social_security_start_age: 67,
    pension_annual: 0,
    other_income_annual: 0,
    equity_fraction: 0.90,   // high stocks — long time horizon
    savings_rate: 0.12,
    employer_match_rate: 50,
    employer_match_ceiling: 6,
  },
  {
    label: 'Mid-Career Family',
    description: '42-year-old with a family, solid income, building equity.',
    age: 42,
    household_size: 4,
    income: 130_000,
    net_worth: 380_000,
    investable_savings: 210_000,
    home_equity: 150_000,
    debt: 25_000,
    planned_retirement_age: 65,
    life_expectancy: 87,
    annual_spending_retirement: 85_000,
    social_security_annual: 30_000,
    social_security_start_age: 67,
    pension_annual: 0,
    other_income_annual: 0,
    equity_fraction: 0.75,
    savings_rate: 0.15,
    employer_match_rate: 100,
    employer_match_ceiling: 4,
  },
  {
    label: 'Late Starter',
    description: '50-year-old who prioritized other goals and is now catching up.',
    age: 50,
    household_size: 2,
    income: 80_000,
    net_worth: 160_000,
    investable_savings: 35_000,
    home_equity: 120_000,
    debt: 8_000,
    planned_retirement_age: 67,
    life_expectancy: 85,
    annual_spending_retirement: 55_000,
    social_security_annual: 22_000,
    social_security_start_age: 67,
    pension_annual: 0,
    other_income_annual: 0,
    equity_fraction: 0.70,
    savings_rate: 0.18,
    employer_match_rate: 50,
    employer_match_ceiling: 6,
  },
  {
    label: 'Pre-Retiree',
    description: '57-year-old on track with strong savings and 8 years to go.',
    age: 57,
    household_size: 2,
    income: 165_000,
    net_worth: 1_300_000,
    investable_savings: 980_000,
    home_equity: 300_000,
    debt: 0,
    planned_retirement_age: 65,
    life_expectancy: 90,
    annual_spending_retirement: 100_000,
    social_security_annual: 38_000,
    social_security_start_age: 67,
    pension_annual: 0,
    other_income_annual: 0,
    equity_fraction: 0.60,   // glide path shifting toward bonds
    savings_rate: 0.22,
    employer_match_rate: 0,
    employer_match_ceiling: 0,
  },
  {
    label: 'Comfortable & Diversified',
    description: '62-year-old with pension + Social Security covering most spending.',
    age: 62,
    household_size: 2,
    income: 210_000,
    net_worth: 2_200_000,
    investable_savings: 1_700_000,
    home_equity: 450_000,
    debt: 0,
    planned_retirement_age: 68,
    life_expectancy: 92,
    annual_spending_retirement: 130_000,
    social_security_annual: 44_000,
    social_security_start_age: 70,   // delaying to 70 maximizes benefit at this income level
    pension_annual: 24_000,
    other_income_annual: 0,
    equity_fraction: 0.50,
    savings_rate: 0.25,
    employer_match_rate: 0,
    employer_match_ceiling: 0,
  },
  {
    label: 'Early Retiree & High Saver',
    description: '55-year-old couple targeting retirement at 60 with a pension and aggressive dual-income savings.',
    age: 55,
    household_size: 2,
    income: 180_000,
    net_worth: 1_580_000,
    investable_savings: 1_300_000,   // 403b + Roth + after-tax accounts
    home_equity: 280_000,
    debt: 0,
    planned_retirement_age: 60,
    life_expectancy: 90,
    annual_spending_retirement: 85_000,  // Boldin recurring $54k + blended healthcare ~$19k + misc ~$12k (real 2026 dollars)
    social_security_annual: 57_500,  // combined (~$3,294 + $1,500/mo)
    social_security_start_age: 67,   // matches Boldin: James collects Dec 2037
    pension_annual: 56_000,          // $4,666/mo pension starting at retirement
    other_income_annual: 0,
    equity_fraction: 0.75,
    savings_rate: 0.25,              // ~24.5% of combined household income ($44k employee ÷ $180k)
    employer_match_rate: 50,         // employer contributes ~8.5% of income total
    employer_match_ceiling: 17,      // (50% × 17% ≈ 8.5%)
  },
]
