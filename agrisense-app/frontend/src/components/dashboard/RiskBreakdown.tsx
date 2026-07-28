/**
 * Distribution of fields across the four USDA salinity classes.
 *
 * A stacked proportion bar rather than a pie: the question is "how much of my
 * land is in trouble", which is a part-to-whole comparison read along one axis.
 * Segments carry a 2px surface gap so adjacent fills never blend, and every
 * band is labelled — colour is never the only channel.
 */
import { RISK_META } from '../../lib/risk'
import type { RiskLevel } from '../../types/api'

const ORDER: RiskLevel[] = ['low', 'moderate', 'high', 'critical']

export default function RiskBreakdown({
  breakdown,
  total,
}: {
  breakdown: Record<string, number>
  total: number
}) {
  if (!total) return null

  const segments = ORDER.map((level) => ({
    level,
    meta: RISK_META[level],
    count: breakdown[level] ?? 0,
  })).filter((s) => s.count > 0)

  return (
    <div>
      <div className="flex h-2.5 w-full gap-[2px] overflow-hidden rounded-full">
        {segments.map((s) => (
          <div
            key={s.level}
            className="h-full rounded-full first:rounded-l-full last:rounded-r-full"
            style={{
              width: `${(s.count / total) * 100}%`,
              background: s.meta.colorVar,
            }}
            title={`${s.meta.label}: ${s.count} field${s.count === 1 ? '' : 's'}`}
          />
        ))}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-4">
        {ORDER.map((level) => {
          const meta = RISK_META[level]
          const count = breakdown[level] ?? 0
          return (
            <div key={level} className="flex items-center gap-2">
              <span
                className="size-2 shrink-0 rounded-full"
                style={{ background: meta.colorVar, opacity: count ? 1 : 0.3 }}
                aria-hidden
              />
              <div className="min-w-0">
                <p className="truncate text-[11px] font-medium text-ink-soft">
                  {meta.label}
                  <span className="tabular ml-1.5 text-ink-muted">{count}</span>
                </p>
                <p className="truncate text-[10px] text-ink-muted">{meta.range}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
