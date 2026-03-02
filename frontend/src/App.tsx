import { useState } from 'react'
import { PlanForm } from '@/components/PlanForm'
import { ResultsCard } from '@/components/ResultsCard'
import { CohortCard } from '@/components/CohortCard'
import type { EvaluationResponse, CohortResponse } from '@/types/api'

export default function App() {
  const [result, setResult] = useState<EvaluationResponse | null>(null)
  const [cohortResult, setCohortResult] = useState<CohortResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formDirty, setFormDirty] = useState(false)

  const hasResult = result !== null || loading || error !== null

  function handleReset() {
    setResult(null)
    setCohortResult(null)
    setError(null)
    setFormDirty(false)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-baseline gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">WealthPath</h1>
          <span className="text-sm text-muted-foreground">Retirement Readiness Estimator</span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="flex flex-col lg:flex-row gap-6 lg:gap-8 items-start">

          {/* Form — full width on mobile, flex-1 on desktop */}
          <div className="w-full lg:flex-1 lg:min-w-0">
            <PlanForm
              onResult={setResult}
              onCohort={setCohortResult}
              onLoading={setLoading}
              onError={setError}
              onReset={handleReset}
              onDirty={setFormDirty}
            />
          </div>

          {/* Results — below form on mobile (only shown after submit),
                        sticky sidebar on desktop (always visible as placeholder) */}
          <div className={`w-full lg:w-80 lg:shrink-0 lg:sticky lg:top-8 space-y-4 ${!hasResult ? 'hidden lg:block' : ''}`}>
            <ResultsCard result={result} loading={loading} error={error} stale={formDirty} />
            {cohortResult && !loading && <CohortCard result={cohortResult} />}
          </div>

        </div>

        {/* About section */}
        <div className="mt-12 border-t border-border pt-8">
          <h2 className="text-base font-semibold text-foreground mb-4">About WealthPath</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm text-muted-foreground">
            <div>
              <h3 className="font-medium text-foreground mb-1">What this does</h3>
              <p>
                WealthPath estimates the probability that your current savings, income, and retirement
                plan will cover your spending through your expected lifetime. Enter your numbers, and
                the model scores your plan and shows which factors drive your result — so you can see
                exactly what to improve.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-foreground mb-1">Data sources</h3>
              <p>
                Projections are benchmarked against the{' '}
                <strong className="text-foreground">Federal Reserve Survey of Consumer Finances (SCF)</strong>
                {' '}— a nationally representative survey of U.S. household balance sheets conducted
                every three years. The most recent wave (2022) covers ~4,600 households and is the
                gold standard for wealth and income comparisons.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-foreground mb-1">How it works</h3>
              <p>
                A gradient-boosted machine learning model (XGBoost) was trained on hundreds of
                thousands of Monte Carlo retirement simulations anchored to real SCF household
                profiles. Each simulation models savings accumulation, market volatility, spending
                in retirement, and Social Security income. The model returns a success probability
                and SHAP-based explanations showing which inputs matter most for your household.
              </p>
              <p className="mt-2">
                <strong className="text-foreground">Not financial advice.</strong>{' '}
                WealthPath is an educational planning tool. Consult a financial advisor for
                personalized guidance.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
