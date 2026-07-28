/** Cross-field actions, most urgent first. */
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { SeverityBadge } from '../ui/primitives'
import type { FieldSummary, Recommendation } from '../../types/api'

export default function AlertsPanel({
  alerts,
  fields,
}: {
  alerts: Recommendation[]
  fields: FieldSummary[]
}) {
  const nameFor = (fieldId: number) =>
    fields.find((f) => f.field_id === fieldId)?.field_name ?? `Field ${fieldId}`

  const actionable = alerts
    .filter((a) => a.severity !== 'info')
    .sort((a, b) => a.priority - b.priority)
    .slice(0, 6)

  if (!actionable.length) {
    return (
      <p className="py-6 text-center text-xs text-ink-muted">
        No urgent actions. Every field is inside its salt tolerance.
      </p>
    )
  }

  return (
    <ul className="divide-y divide-[var(--border)]">
      {actionable.map((alert) => (
        <li key={`${alert.field_id}-${alert.priority}-${alert.title}`}>
          <Link
            to={`/fields/${alert.field_id}`}
            className="group flex items-start gap-3 py-3 transition hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <SeverityBadge severity={alert.severity} />
                <span className="truncate text-[11px] text-ink-muted">
                  {nameFor(alert.field_id)}
                </span>
              </div>
              <p className="mt-1.5 text-xs font-medium text-ink">{alert.title}</p>
              {alert.action_mm != null && alert.action_mm > 0 && (
                <p className="mt-0.5 text-[11px] text-ink-muted">
                  Apply {Math.round(alert.action_mm)} mm
                </p>
              )}
            </div>
            <ArrowRight
              size={13}
              className="mt-1 shrink-0 text-ink-muted transition group-hover:translate-x-0.5"
              aria-hidden
            />
          </Link>
        </li>
      ))}
    </ul>
  )
}
