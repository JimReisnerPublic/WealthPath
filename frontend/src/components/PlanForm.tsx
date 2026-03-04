import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Separator } from '@/components/ui/separator'
import type { EvaluationRequest, EvaluationResponse, CohortRequest, CohortResponse } from '@/types/api'
import { SCENARIOS, scenarioToFormState } from '@/data/scenarios'

interface PlanFormProps {
  onResult: (result: EvaluationResponse) => void
  onCohort: (result: CohortResponse | null) => void
  onLoading: (loading: boolean) => void
  onError: (error: string | null) => void
  onReset: () => void
  onDirty: (dirty: boolean) => void
  onHousehold?: (household: import('@/types/api').HouseholdProfile) => void
  onEvalRequest?: (req: EvaluationRequest) => void
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function parseDollars(value: string): number {
  const cleaned = value.replace(/[^0-9.-]/g, '')
  return parseFloat(cleaned) || 0
}

function formatDollars(value: number): string {
  if (value === 0) return ''
  return value.toLocaleString('en-US', { maximumFractionDigits: 0 })
}

type IncomeFrequency = 'monthly' | 'annual'

export interface FormState {
  // About You
  age: string
  household_size: string
  // Your Finances
  income: string
  net_worth: string
  investable_savings: string
  home_equity: string
  debt: string
  // Retirement Plan
  planned_retirement_age: string
  life_expectancy: string
  annual_spending_retirement: string
  // Guaranteed Income
  income_frequency: IncomeFrequency
  social_security: string
  social_security_start_age: string
  pension: string
  other_income: string
  // Investment Strategy
  equity_fraction: number
  savings_rate: number
  // Employer Match (optional, frontend-only computation)
  employer_match_rate: string
  employer_match_ceiling: string
}

const DEFAULT_STATE: FormState = {
  age: '',
  household_size: '1',
  income: '',
  net_worth: '',
  investable_savings: '',
  home_equity: '',
  debt: '',
  planned_retirement_age: '',
  life_expectancy: '85',
  annual_spending_retirement: '',
  income_frequency: 'annual',
  social_security: '',
  social_security_start_age: '67',
  pension: '',
  other_income: '',
  equity_fraction: 0.70,
  savings_rate: 0.10,
  employer_match_rate: '',
  employer_match_ceiling: '',
}

function SectionCard({ title, children, action }: {
  title: string
  children: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <Card className="mb-4">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold text-foreground">{title}</CardTitle>
          {action}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  )
}

function FieldRow({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-2 gap-4 items-center">
      <div>
        <Label className="text-sm font-medium">{label}</Label>
        {hint && <p className="text-xs text-muted-foreground mt-0.5">{hint}</p>}
      </div>
      <div>{children}</div>
    </div>
  )
}

function DollarInput({
  value,
  onChange,
  placeholder,
  allowNegative = false,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  allowNegative?: boolean
}) {
  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value.replace(/[^0-9.-]/g, '')
    onChange(allowNegative ? raw : raw.replace(/-/g, ''))
  }

  const display = value === '' ? '' : formatDollars(parseFloat(value) || 0)

  return (
    <div className="relative">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
      <Input
        className="pl-7"
        value={display}
        onChange={handleChange}
        placeholder={placeholder ?? '0'}
        inputMode="numeric"
      />
    </div>
  )
}

// Monthly / Annual segmented toggle
function FrequencyToggle({
  value,
  onChange,
}: {
  value: IncomeFrequency
  onChange: (v: IncomeFrequency) => void
}) {
  return (
    <div className="flex rounded-md border border-border overflow-hidden text-xs font-medium">
      <button
        type="button"
        onClick={() => onChange('monthly')}
        className={`px-3 py-1 transition-colors ${
          value === 'monthly'
            ? 'bg-primary text-primary-foreground'
            : 'bg-background text-muted-foreground hover:bg-muted'
        }`}
      >
        Monthly
      </button>
      <button
        type="button"
        onClick={() => onChange('annual')}
        className={`px-3 py-1 transition-colors ${
          value === 'annual'
            ? 'bg-primary text-primary-foreground'
            : 'bg-background text-muted-foreground hover:bg-muted'
        }`}
      >
        Annual
      </button>
    </div>
  )
}

export function PlanForm({ onResult, onCohort, onLoading, onError, onReset, onDirty, onHousehold, onEvalRequest }: PlanFormProps) {
  const [form, setForm] = useState<FormState>(DEFAULT_STATE)
  const [submittedOnce, setSubmittedOnce] = useState(false)
  const [scenarioLoaded, setScenarioLoaded] = useState(false)

  function markDirty(dirty: boolean) {
    onDirty(dirty)
  }

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm(prev => ({ ...prev, [key]: value }))
    if (submittedOnce) markDirty(true)
  }

  // Compute guaranteed income components in annual terms
  const multiplier = form.income_frequency === 'monthly' ? 12 : 1
  const ssRawAnnual = parseDollars(form.social_security) * multiplier
  const pensionAnnual = parseDollars(form.pension) * multiplier
  const otherAnnual = parseDollars(form.other_income) * multiplier
  const guaranteedIncomeAnnual = ssRawAnnual + pensionAnnual + otherAnnual

  // Adjust SS for delayed start: weight by the fraction of retirement spent receiving it.
  // e.g. retire at 60, SS at 67, live to 90 → 23/30 years = 76.7% → effective SS is 76.7% of full amount.
  const retirementAge = parseInt(form.planned_retirement_age) || 65
  const lifeExpectancy = parseInt(form.life_expectancy) || 85
  const ssStartAge = parseInt(form.social_security_start_age) || retirementAge
  const yearsInRetirement = Math.max(1, lifeExpectancy - retirementAge)
  const yearsReceivingSS = Math.max(0, lifeExpectancy - ssStartAge)
  const ssEffectiveAnnual =
    ssStartAge > retirementAge && ssRawAnnual > 0
      ? ssRawAnnual * (yearsReceivingSS / yearsInRetirement)
      : ssRawAnnual
  const ssDelayYears = Math.max(0, ssStartAge - retirementAge)

  // Compute effective savings rate including employer 401(k) match
  // effective = employee% + min(employee%, ceiling%) × match%
  const employerMatchRate = parseFloat(form.employer_match_rate) / 100 || 0
  const employerMatchCeiling = parseFloat(form.employer_match_ceiling) / 100 || 0
  const employerContribution =
    employerMatchRate > 0
      ? Math.min(form.savings_rate, employerMatchCeiling) * employerMatchRate
      : 0
  const effectiveSavingsRate = Math.min(form.savings_rate + employerContribution, 0.80)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onError(null)
    onLoading(true)
    setSubmittedOnce(true)
    markDirty(false)

    const payload: EvaluationRequest = {
      household: {
        age: parseInt(form.age) || 0,
        income: parseDollars(form.income),
        net_worth: parseDollars(form.net_worth),
        investable_savings: parseDollars(form.investable_savings),
        household_size: parseInt(form.household_size) || 1,
        home_equity: parseDollars(form.home_equity),
        debt: parseDollars(form.debt),
      },
      planned_retirement_age: parseInt(form.planned_retirement_age) || 65,
      life_expectancy: parseInt(form.life_expectancy) || 85,
      annual_spending_retirement: parseDollars(form.annual_spending_retirement),
      // Guaranteed income: SS is time-weighted for delayed start; pension/other unaffected
      social_security_annual: ssEffectiveAnnual + pensionAnnual + otherAnnual,
      equity_fraction: form.equity_fraction,
      // Employee savings + employer match contribution
      savings_rate: effectiveSavingsRate,
    }

    const cohortPayload: CohortRequest = {
      household: payload.household,
      compare_fields: ['income', 'net_worth'],
    }

    const post = (path: string, body: unknown) =>
      fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

    try {
      const [evalSettled, cohortSettled] = await Promise.allSettled([
        post('/api/v1/plan/evaluate', payload),
        post('/api/v1/cohort/compare', cohortPayload),
      ])

      // Evaluation result — required; surface errors to the user
      if (evalSettled.status === 'rejected') throw evalSettled.reason
      if (!evalSettled.value.ok) {
        const detail = await evalSettled.value.json().catch(() => ({}))
        throw new Error(detail?.detail ?? `Server error ${evalSettled.value.status}`)
      }
      const data: EvaluationResponse = await evalSettled.value.json()
      onResult(data)
      onHousehold?.(payload.household)
      onEvalRequest?.(payload)

      // Cohort result — optional; silently ignored on failure
      if (cohortSettled.status === 'fulfilled' && cohortSettled.value.ok) {
        const cohortData: CohortResponse = await cohortSettled.value.json()
        onCohort(cohortData)
      } else {
        onCohort(null)
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      onLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {/* Scenario picker */}
      <div className="mb-4">
        <p className="text-xs font-medium text-muted-foreground mb-2">Load an example household:</p>
        <div className="flex flex-wrap gap-2">
          {SCENARIOS.map(s => (
            <button
              key={s.label}
              type="button"
              title={s.description}
              onClick={() => { setForm(scenarioToFormState(s)); onReset(); markDirty(false); setSubmittedOnce(false); setScenarioLoaded(true) }}
              className="px-3 py-1 rounded-full border border-border text-xs font-medium bg-background text-foreground hover:bg-muted hover:border-primary transition-colors"
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Top shortcut button — appears after first submission or scenario load */}
      {(submittedOnce || scenarioLoaded) && (
        <Button type="submit" className="w-full mb-4" size="lg">
          Estimate My Plan
        </Button>
      )}

      {/* 1. About You */}
      <SectionCard title="About You">
        <FieldRow label="Age">
          <Input
            type="number"
            min={18}
            max={100}
            value={form.age}
            onChange={e => set('age', e.target.value)}
            placeholder="e.g. 45"
            required
          />
        </FieldRow>
        <FieldRow label="Household Size">
          <Input
            type="number"
            min={1}
            max={20}
            value={form.household_size}
            onChange={e => set('household_size', e.target.value)}
            placeholder="1"
          />
        </FieldRow>
      </SectionCard>

      {/* 2. Your Finances */}
      <SectionCard title="Your Finances">
        <FieldRow label="Annual Income" hint="Combined household, before tax">
          <DollarInput
            value={form.income}
            onChange={v => set('income', v)}
            placeholder="e.g. 85,000"
          />
        </FieldRow>
        <FieldRow label="Current Net Worth" hint="Assets minus liabilities">
          <DollarInput
            value={form.net_worth}
            onChange={v => set('net_worth', v)}
            placeholder="e.g. 150,000"
            allowNegative
          />
        </FieldRow>
        <FieldRow label="Investable Savings" hint="401(k), IRA, brokerage — excludes home equity">
          <DollarInput
            value={form.investable_savings}
            onChange={v => set('investable_savings', v)}
            placeholder="e.g. 75,000"
          />
        </FieldRow>
        <FieldRow label="Home Equity">
          <DollarInput
            value={form.home_equity}
            onChange={v => set('home_equity', v)}
            placeholder="0"
          />
        </FieldRow>
        <FieldRow label="Outstanding Debt" hint="Mortgage, loans, credit cards, etc.">
          <DollarInput
            value={form.debt}
            onChange={v => set('debt', v)}
            placeholder="0"
          />
        </FieldRow>
      </SectionCard>

      {/* 3. Retirement Plan */}
      <SectionCard title="Retirement Plan">
        <FieldRow label="Planned Retirement Age">
          <Input
            type="number"
            min={45}
            max={80}
            value={form.planned_retirement_age}
            onChange={e => set('planned_retirement_age', e.target.value)}
            placeholder="e.g. 65"
            required
          />
        </FieldRow>
        <FieldRow label="Life Expectancy">
          <Input
            type="number"
            min={70}
            max={100}
            value={form.life_expectancy}
            onChange={e => set('life_expectancy', e.target.value)}
            placeholder="85"
          />
        </FieldRow>
        <FieldRow label="Retirement Spending" hint="Lifestyle, healthcare, and taxes on pension/401k withdrawals. Today's dollars.">
          <DollarInput
            value={form.annual_spending_retirement}
            onChange={v => set('annual_spending_retirement', v)}
            placeholder="e.g. 60,000"
          />
        </FieldRow>
      </SectionCard>

      {/* 4. Guaranteed Income — with monthly/annual toggle */}
      <SectionCard
        title="Guaranteed Income in Retirement"
        action={
          <FrequencyToggle
            value={form.income_frequency}
            onChange={v => set('income_frequency', v)}
          />
        }
      >
        <FieldRow label="Social Security" hint="Combined for both spouses">
          <DollarInput
            value={form.social_security}
            onChange={v => set('social_security', v)}
            placeholder="0"
          />
        </FieldRow>
        <FieldRow label="SS Start Age" hint="Age when you'll start collecting (62–70)">
          <Input
            type="number"
            min={62}
            max={70}
            value={form.social_security_start_age}
            onChange={e => set('social_security_start_age', e.target.value)}
            placeholder="67"
          />
        </FieldRow>
        <FieldRow label="Pension">
          <DollarInput
            value={form.pension}
            onChange={v => set('pension', v)}
            placeholder="0"
          />
        </FieldRow>
        <FieldRow label="Other Income" hint="Rental, annuity, etc.">
          <DollarInput
            value={form.other_income}
            onChange={v => set('other_income', v)}
            placeholder="0"
          />
        </FieldRow>

        {guaranteedIncomeAnnual > 0 && (
          <>
            <Separator />
            <div className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground">Total guaranteed income (annual)</span>
              <span className="font-semibold tabular-nums">
                ${guaranteedIncomeAnnual.toLocaleString('en-US', { maximumFractionDigits: 0 })}
              </span>
            </div>
            {ssDelayYears > 0 && ssRawAnnual > 0 && (
              <p className="text-xs text-muted-foreground">
                SS delayed {ssDelayYears} yr{ssDelayYears !== 1 ? 's' : ''} past retirement —
                model uses{' '}
                <span className="font-medium text-foreground">
                  ~${Math.round(ssEffectiveAnnual).toLocaleString('en-US', { maximumFractionDigits: 0 })}/yr
                </span>
                {' '}effective SS (time-weighted over retirement).
              </p>
            )}
          </>
        )}
      </SectionCard>

      {/* 5. Investment Strategy */}
      <SectionCard title="Investment Strategy">
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <Label className="text-sm font-medium">Stock Allocation</Label>
            <span className="text-sm font-semibold tabular-nums">
              {Math.round(form.equity_fraction * 100)}% stocks
              / {Math.round((1 - form.equity_fraction) * 100)}% bonds
            </span>
          </div>
          <Slider
            min={0}
            max={100}
            step={5}
            value={[Math.round(form.equity_fraction * 100)]}
            onValueChange={([v]) => set('equity_fraction', v / 100)}
            className="mt-2"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>All Bonds</span>
            <span>All Stocks</span>
          </div>
          {/* Return rate transparency note — real (inflation-adjusted) returns */}
          <p className="text-xs text-muted-foreground pt-1">
            Model assumes{' '}
            <span className="font-medium text-foreground">7% stocks · 2% bonds</span>
            {' '}per year, after inflation — the same "today's dollars" as your spending target above.
            Your current blend:{' '}
            <span className="font-medium text-foreground">
              ~{(form.equity_fraction * 7 + (1 - form.equity_fraction) * 2).toFixed(1)}%/yr
            </span>
            {' '}expected return.
          </p>
        </div>

        <div className="space-y-2 pt-2">
          <div className="flex justify-between items-center">
            <Label className="text-sm font-medium">Your Savings Rate</Label>
            <span className="text-sm font-semibold tabular-nums">
              {Math.round(form.savings_rate * 100)}% of income
            </span>
          </div>
          <Slider
            min={0}
            max={80}
            step={1}
            value={[Math.round(form.savings_rate * 100)]}
            onValueChange={([v]) => set('savings_rate', v / 100)}
            className="mt-2"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>0%</span>
            <span>80%</span>
          </div>
        </div>

        {/* Employer match — optional, purely a frontend computation */}
        <div className="space-y-3 pt-2 border-t border-border">
          <p className="text-xs text-muted-foreground pt-1">
            Employer 401(k) match (optional) — added on top of your savings rate.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs font-medium text-muted-foreground">Match rate</Label>
              <div className="relative">
                <Input
                  type="number"
                  min={0}
                  max={100}
                  step={1}
                  value={form.employer_match_rate}
                  onChange={e => set('employer_match_rate', e.target.value)}
                  placeholder="50"
                  className="pr-6"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">%</span>
              </div>
              <p className="text-xs text-muted-foreground">e.g. 50 = 50¢ per $1</p>
            </div>
            <div className="space-y-1">
              <Label className="text-xs font-medium text-muted-foreground">Up to (% of income)</Label>
              <div className="relative">
                <Input
                  type="number"
                  min={0}
                  max={20}
                  step={1}
                  value={form.employer_match_ceiling}
                  onChange={e => set('employer_match_ceiling', e.target.value)}
                  placeholder="6"
                  className="pr-6"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">%</span>
              </div>
              <p className="text-xs text-muted-foreground">e.g. 6 = first 6%</p>
            </div>
          </div>
          {employerContribution > 0 && (
            <div className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground">Effective savings rate (your + employer)</span>
              <span className="font-semibold tabular-nums text-green-700">
                {Math.round(effectiveSavingsRate * 100)}%
              </span>
            </div>
          )}
          {parseDollars(form.income) > 0 && effectiveSavingsRate > 0 && (
            <div className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground">Est. annual contributions</span>
              <span className="font-semibold tabular-nums">
                ${Math.round(effectiveSavingsRate * parseDollars(form.income)).toLocaleString('en-US', { maximumFractionDigits: 0 })}
              </span>
            </div>
          )}
        </div>
      </SectionCard>

      <Button type="submit" className="w-full" size="lg">
        Estimate My Plan
      </Button>
    </form>
  )
}
