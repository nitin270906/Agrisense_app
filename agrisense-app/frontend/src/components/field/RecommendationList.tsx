/** Ranked, plain-language actions. Every card states a number and a deadline. */
import {
  Droplets,
  Layers,
  Leaf,
  ShowerHead,
  Sprout,
  Waves,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { SeverityBadge } from '../ui/primitives'
import { severityMeta } from '../../lib/risk'
import type { Recommendation, RecommendationCategory } from '../../types/api'

const CATEGORY_ICON: Record<RecommendationCategory, LucideIcon> = {
  irrigation: Droplets,
  leaching: ShowerHead,
  amendment: Layers,
  crop_choice: Sprout,
  drainage: Waves,
  monitoring: Leaf,
}

export default function RecommendationList({ items }: { items: Recommendation[] }) {
  if (!items.length) {
    return <p className="py-6 text-center text-xs text-ink-muted">No recommendations yet.</p>
  }

  return (
    <ul className="space-y-3">
      {items.map((rec, i) => {
        const Icon = CATEGORY_ICON[rec.category] ?? Leaf
        const meta = severityMeta(rec.severity)

        return (
          <li
            key={`${rec.category}-${rec.priority}-${i}`}
            className="rise-in rounded-lg border border-edge bg-surface-2 p-3.5"
            style={{
              animationDelay: `${i * 60}ms`,
              // A left rule keyed to severity, so urgency is scannable down the
              // list without relying on the badge alone.
              borderLeft: `3px solid ${meta.colorVar}`,
            }}
          >
            <div className="flex items-start gap-3">
              <span
                className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg"
                style={{
                  background: `color-mix(in srgb, ${meta.colorVar} 16%, transparent)`,
                  color: meta.colorVar,
                }}
              >
                <Icon size={14} aria-hidden />
              </span>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-ink">{rec.title}</p>
                  <SeverityBadge severity={rec.severity} />
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-ink-soft">{rec.message}</p>

                {rec.action_mm != null && rec.action_mm > 0 && (
                  <div className="mt-2.5 inline-flex items-center gap-1.5 rounded-md bg-surface-3 px-2.5 py-1">
                    <Droplets size={11} className="text-ink-muted" aria-hidden />
                    <span className="tabular text-[11px] font-medium text-ink">
                      Apply {Math.round(rec.action_mm)} mm
                    </span>
                  </div>
                )}
              </div>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
