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
    // Estimated score: ~65% (at risk)
    // Drivers: 39-year runway is the whole story — tiny savings base but compounding time is enormous
    label: 'Just Starting Out',
    description: '26-year-old early in their career — not much saved yet, but time is the biggest asset.',
    age: 26,
    household_size: 1,
    income: 60_000,
    net_worth: -8_000,                 // student loans exceed small savings
    investable_savings: 10_000,
    home_equity: 0,
    debt: 22_000,                      // student loans
    planned_retirement_age: 65,
    life_expectancy: 88,
    annual_spending_retirement: 48_000,
    social_security_annual: 19_000,
    social_security_start_age: 67,
    pension_annual: 0,
    other_income_annual: 0,
    equity_fraction: 0.95,             // all stocks — 39-year horizon
    savings_rate: 0.12,
    employer_match_rate: 50,
    employer_match_ceiling: 6,
  },
  {
    // Estimated score: ~44% (critical/at-risk)
    // Drivers: low savings base, but 16 years + higher savings rate + SS at retirement softens the blow
    label: 'Late Bloomer',
    description: '51-year-old couple who prioritized family over savings — now catching up aggressively.',
    age: 51,
    household_size: 2,
    income: 76_000,
    net_worth: 185_000,
    investable_savings: 48_000,
    home_equity: 145_000,
    debt: 8_000,
    planned_retirement_age: 67,
    life_expectancy: 85,
    annual_spending_retirement: 55_000,
    social_security_annual: 23_000,
    social_security_start_age: 67,    // starts same year as retirement — no time-weighting penalty
    pension_annual: 0,
    other_income_annual: 0,
    equity_fraction: 0.70,
    savings_rate: 0.15,
    employer_match_rate: 50,
    employer_match_ceiling: 6,
  },
  {
    // Estimated score: ~63% (at risk)
    // Drivers: decent runway (28 yrs) and moderate savings base, but spending/income ratio is high
    label: 'Growing Family',
    description: '37-year-old with kids and a mortgage — income is solid but so are expenses.',
    age: 37,
    household_size: 3,
    income: 105_000,
    net_worth: 195_000,
    investable_savings: 78_000,
    home_equity: 110_000,
    debt: 35_000,
    planned_retirement_age: 65,
    life_expectancy: 86,
    annual_spending_retirement: 75_000,
    social_security_annual: 27_000,
    social_security_start_age: 67,
    pension_annual: 0,
    other_income_annual: 0,
    equity_fraction: 0.85,            // high stocks — long time horizon
    savings_rate: 0.10,
    employer_match_rate: 50,
    employer_match_ceiling: 6,
  },
  {
    // Estimated score: ~76% (borderline on track)
    // Drivers: nearly 2× savings-to-income, 21 years + 19% effective rate — close but not there yet
    label: 'Diligent Saver',
    description: '44-year-old who has been disciplined — strong habit, solid base, but not done yet.',
    age: 44,
    household_size: 2,
    income: 118_000,
    net_worth: 455_000,
    investable_savings: 230_000,
    home_equity: 210_000,
    debt: 15_000,
    planned_retirement_age: 65,
    life_expectancy: 88,
    annual_spending_retirement: 80_000,
    social_security_annual: 33_000,
    social_security_start_age: 67,
    pension_annual: 0,
    other_income_annual: 0,
    equity_fraction: 0.75,
    savings_rate: 0.15,
    employer_match_rate: 100,
    employer_match_ceiling: 4,
  },
  {
    // Estimated score: ~88% (on track)
    // Drivers: 6.5× savings-to-income, low net replacement rate, 9 years of additional compounding
    label: 'Near the Finish Line',
    description: '57-year-old couple with strong savings and 9 years left — in a great position.',
    age: 57,
    household_size: 2,
    income: 158_000,
    net_worth: 1_370_000,
    investable_savings: 1_020_000,
    home_equity: 340_000,
    debt: 0,
    planned_retirement_age: 66,
    life_expectancy: 90,
    annual_spending_retirement: 96_000,
    social_security_annual: 38_000,
    social_security_start_age: 67,    // SS starts 1 yr into retirement — minimal time-weighting
    pension_annual: 0,
    other_income_annual: 0,
    equity_fraction: 0.60,            // glide path shifting toward bonds
    savings_rate: 0.20,
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
