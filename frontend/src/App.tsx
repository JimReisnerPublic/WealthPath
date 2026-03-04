import { useState } from 'react'
import { PlanForm } from '@/components/PlanForm'
import { ResultsCard } from '@/components/ResultsCard'
import { CohortCard } from '@/components/CohortCard'
import { ChatPanel } from '@/components/ChatPanel'
import type { EvaluationResponse, CohortResponse, HouseholdProfile, EvaluationRequest } from '@/types/api'

export default function App() {
  const [result, setResult] = useState<EvaluationResponse | null>(null)
  const [cohortResult, setCohortResult] = useState<CohortResponse | null>(null)
  const [household, setHousehold] = useState<HouseholdProfile | null>(null)
  const [evalRequest, setEvalRequest] = useState<EvaluationRequest | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formDirty, setFormDirty] = useState(false)

  const hasResult = result !== null || loading || error !== null

  function handleReset() {
    setResult(null)
    setCohortResult(null)
    setHousehold(null)
    setEvalRequest(null)
    setError(null)
    setFormDirty(false)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-baseline gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">WealthPath</h1>
          <span className="text-sm text-muted-foreground">Retirement Readiness Estimator</span>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/*
          Three-column layout on xl+ (≥1280px): Results | Form | Chat
          Two-column on lg (1024–1279px): Form | Results  (no chat sidebar)
          Mobile (<1024px): Form → Results → Chat (stacked)

          DOM order is Form→Results→Chat (best for mobile linear flow).
          xl:order-* repositions columns on large screens without touching the DOM.
        */}
        <div className="flex flex-col lg:flex-row xl:flex-row gap-6 items-start">

          {/* Form — first in DOM for mobile; center column on xl */}
          <div className="w-full lg:flex-1 lg:min-w-0 xl:order-2 xl:max-w-[440px]">
            <PlanForm
              onResult={setResult}
              onCohort={setCohortResult}
              onLoading={setLoading}
              onError={setError}
              onReset={handleReset}
              onDirty={setFormDirty}
              onHousehold={setHousehold}
              onEvalRequest={setEvalRequest}
            />
          </div>

          {/* Results — second in DOM; right sidebar on lg, left sidebar on xl */}
          <div className={`w-full lg:w-80 lg:shrink-0 lg:sticky lg:top-8 xl:w-60 xl:order-1 space-y-4 ${!hasResult ? 'hidden lg:block' : ''}`}>
            <ResultsCard result={result} loading={loading} error={error} stale={formDirty} />
            {cohortResult && !loading && <CohortCard result={cohortResult} />}
          </div>

          {/* Chat sidebar — xl+ only; always visible so the placeholder holds space.
               Below xl the chat renders outside the flex row (see block below). */}
          <div className="hidden xl:flex xl:flex-col xl:flex-1 xl:min-w-0 xl:sticky xl:top-8 xl:h-[calc(100vh-4rem)] xl:order-3">
            {result && household && evalRequest
              ? <ChatPanel household={household} result={result} evalRequest={evalRequest} />
              : (
                <div className="flex-1 flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-8 text-center gap-2">
                  <p className="text-sm font-medium text-muted-foreground">Ask About Your Results</p>
                  <p className="text-xs text-muted-foreground">Submit your plan above<br />to start chatting.</p>
                </div>
              )
            }
          </div>

        </div>

        {/* Chat panel — mobile and lg only (xl shows it in the sidebar above) */}
        {result && household && evalRequest && (
          <div className="mt-6 xl:hidden">
            <ChatPanel household={household} result={result} evalRequest={evalRequest} />
          </div>
        )}

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
              <p className="mt-2">
                <strong className="text-foreground">No data is stored.</strong>{' '}
                Your numbers are used only to compute your result and are never saved, logged,
                or transmitted beyond the calculation.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
