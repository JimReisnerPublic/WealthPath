import type { FeatureDriver } from '@/types/api'

interface DriverBarProps {
  driver: FeatureDriver
  maxAbs: number  // largest |shap_value| in the set, for scaling
}

export function DriverBar({ driver, maxAbs }: DriverBarProps) {
  const pct = maxAbs > 0 ? Math.abs(driver.shap_value) / maxAbs : 0
  const barWidth = `${Math.round(pct * 100)}%`
  const pp = Math.round(Math.abs(driver.shap_value) * 100)
  const isPositive = driver.direction === 'positive'

  return (
    <div className="py-1 space-y-1">
      {/* Name + value on one row — name truncates, value pinned right */}
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-sm text-foreground truncate" title={driver.display_name}>
          {driver.display_name}
        </span>
        <span
          className={`text-sm font-semibold tabular-nums shrink-0 ${
            isPositive ? 'text-emerald-600' : 'text-red-500'
          }`}
        >
          {isPositive ? '+' : '−'}{pp}pp
        </span>
      </div>

      {/* Bar spans full column width */}
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${isPositive ? 'bg-emerald-500' : 'bg-red-400'}`}
          style={{ width: barWidth }}
        />
      </div>
    </div>
  )
}
