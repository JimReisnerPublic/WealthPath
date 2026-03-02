import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { DriverBar } from '@/components/DriverBar'
import type { EvaluationResponse, SuccessLabel } from '@/types/api'

interface ResultsCardProps {
  result: EvaluationResponse | null
  loading: boolean
  error: string | null
  stale?: boolean
}

function labelConfig(label: SuccessLabel) {
  switch (label) {
    case 'on track':
      return {
        color: 'text-emerald-600',
        badgeClass: 'bg-emerald-100 text-emerald-700 border-emerald-200',
        progressClass: 'bg-emerald-500',
        dot: '🟢',
      }
    case 'at risk':
      return {
        color: 'text-amber-600',
        badgeClass: 'bg-amber-100 text-amber-700 border-amber-200',
        progressClass: 'bg-amber-400',
        dot: '🟡',
      }
    case 'critical':
      return {
        color: 'text-red-600',
        badgeClass: 'bg-red-100 text-red-700 border-red-200',
        progressClass: 'bg-red-500',
        dot: '🔴',
      }
  }
}

export function ResultsCard({ result, loading, error, stale }: ResultsCardProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="py-10 flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <p className="text-sm text-muted-foreground">Calculating...</p>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-red-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-base text-red-600">Error</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-500">{error}</p>
          <p className="text-xs text-muted-foreground mt-2">
            Make sure the API server is running at localhost:8000.
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!result) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-10 flex flex-col items-center gap-2 text-center">
          <p className="text-sm font-medium text-muted-foreground">Your results will appear here</p>
          <p className="text-xs text-muted-foreground">
            Fill in your details and click "Estimate My Plan"
          </p>
        </CardContent>
      </Card>
    )
  }

  const pct = Math.round(result.success_probability * 100)
  const cfg = labelConfig(result.success_label)
  const maxAbs = Math.max(...result.top_drivers.map(d => Math.abs(d.shap_value)), 0.01)

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">Your Result</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {stale && (
          <p className="text-xs text-muted-foreground bg-muted rounded px-2 py-1.5">
            Values changed — re-run to update this result.
          </p>
        )}
        {/* Big number */}
        <div className="flex items-end gap-3">
          <span className={`text-5xl font-bold tabular-nums ${cfg.color}`}>{pct}%</span>
          <Badge className={`mb-1 ${cfg.badgeClass}`} variant="outline">
            {cfg.dot} {result.success_label}
          </Badge>
        </div>

        {/* Progress bar */}
        <div className="space-y-1">
          <Progress value={pct} className="h-3" />
          <p className="text-xs text-muted-foreground">
            Probability of not running out of money in retirement
          </p>
        </div>

        <Separator />

        {/* SHAP drivers */}
        <div>
          <p className="text-sm font-semibold mb-2">Key Drivers</p>
          <div className="space-y-0.5">
            {result.top_drivers.map(driver => (
              <DriverBar key={driver.feature} driver={driver} maxAbs={maxAbs} />
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Green = raises your probability &nbsp;·&nbsp; Red = lowers it
          </p>
        </div>

        <Separator />

        {/* Footer: model source */}
        <div className="text-xs text-muted-foreground space-y-0.5">
          <p>
            Source:{' '}
            {result.data_source === 'surrogate_model'
              ? 'XGBoost surrogate model'
              : 'Monte Carlo simulation'}
          </p>
          {result.model_metrics && (
            <p>
              Model accuracy: R²={result.model_metrics['r2']?.toFixed(2)}, MAE=
              {(result.model_metrics['mae'] * 100).toFixed(1)}pp
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
