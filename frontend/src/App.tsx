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
      </main>
    </div>
  )
}
