import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import type { CohortResponse } from '@/types/api'

const FIELD_LABELS: Record<string, string> = {
  income: 'Annual Income',
  net_worth: 'Net Worth',
  home_equity: 'Home Equity',
  debt: 'Outstanding Debt',
}

function ordinal(n: number): string {
  const r = n % 100
  if (r >= 11 && r <= 13) return `${n}th`
  switch (n % 10) {
    case 1: return `${n}st`
    case 2: return `${n}nd`
    case 3: return `${n}rd`
    default: return `${n}th`
  }
}

function fmt(v: number): string {
  if (Math.abs(v) >= 1_000_000)
    return v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
  return v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export function CohortCard({ result }: { result: CohortResponse }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">Peer Comparison</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground -mt-1">
          Compared against{' '}
          <span className="font-medium text-foreground">
            {result.cohort_size.toLocaleString()}
          </span>{' '}
          similar households from Federal Reserve survey data.
        </p>

        {result.stats.map((stat, i) => {
          const pct = Math.round(stat.percentile_rank)
          const label = FIELD_LABELS[stat.field] ?? stat.field

          return (
            <div key={stat.field}>
              {i > 0 && <Separator className="mb-4" />}
              <div className="space-y-1.5">
                {/* Label + user value */}
                <div className="flex justify-between items-baseline">
                  <span className="text-sm font-medium">{label}</span>
                  <span className="text-sm font-semibold tabular-nums">{fmt(stat.user_value)}</span>
                </div>

                {/* Percentile bar */}
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold tabular-nums w-10 text-right shrink-0">
                    {ordinal(pct)}
                  </span>
                </div>

                {/* Contextual text */}
                <p className="text-xs text-muted-foreground">
                  Higher than {pct}% of similar households
                  &nbsp;·&nbsp;
                  Median: {fmt(stat.cohort_median)}
                </p>
              </div>
            </div>
          )
        })}

        <p className="text-xs text-muted-foreground border-t border-border pt-3">
          Cohort: {result.cohort_description}
        </p>
      </CardContent>
    </Card>
  )
}
