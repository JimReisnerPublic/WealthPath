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
    <div className="flex items-center gap-3 py-1">
      {/* Feature name */}
      <span className="text-sm text-foreground w-44 shrink-0 truncate" title={driver.display_name}>
        {driver.display_name}
      </span>

      {/* Bar */}
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${isPositive ? 'bg-emerald-500' : 'bg-red-400'}`}
          style={{ width: barWidth }}
        />
      </div>

      {/* Value */}
      <span
        className={`text-sm font-semibold tabular-nums w-14 text-right shrink-0 ${
          isPositive ? 'text-emerald-600' : 'text-red-500'
        }`}
      >
        {isPositive ? '+' : '−'}{pp}pp
      </span>
    </div>
  )
}
