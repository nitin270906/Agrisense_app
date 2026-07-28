/**
 * One field, summarised.
 *
 * The card leads with the action, not the measurement. Risk level anchors the
 * left border so urgency is scannable at a glance before reading a single word.
 */
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { ArrowRight, Droplets, TrendingDown, TrendingUp } from 'lucide-react'
import Sparkline from '../charts/Sparkline'
import { RiskBadge } from '../ui/primitives'
import { cx, titleCase } from '../../lib/format'
import { healthColor, riskMeta } from '../../lib/risk'
import type { FieldSummary } from '../../types/api'

export default function FieldCard({
  field,
  index = 0,
}: {
  field: FieldSummary
  index?: number
}) {
  const meta = riskMeta(field.risk_level)
  const rising = field.salinity_delta > 0.02
  const falling = field.salinity_delta < -0.02
  const TrendIcon = rising ? TrendingUp : falling ? TrendingDown : null

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.46,
        ease: [0.22, 1, 0.36, 1],
        delay: Math.min(index * 0.05, 0.4),
      }}
    >
      <Link
        to={`/fields/${field.field_id}`}
        className="group card-3d shimmer-effect block overflow-hidden rounded-2xl bg-surface-1 transition-all duration-200 hover:-translate-y-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        style={{
          border: '1px solid var(--border)',
          borderLeftColor: meta.colorVar,
          borderLeftWidth: '3px',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div className="p-4">
          {/* Header */}
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink">{field.field_name}</p>
              <p className="mt-0.5 truncate text-[11px] text-ink-muted">
                {titleCase(field.crop)} · {field.area_ha.toFixed(1)} ha · {field.farm_name}
              </p>
            </div>
            <RiskBadge level={field.risk_level} size="sm" />
          </div>

          {/* Metric row */}
          <div className="mt-4 flex items-end justify-between gap-3">
            <div>
              <div className="flex items-baseline gap-1.5">
                <span
                  className="text-2xl font-bold tracking-tight"
                  style={{ color: meta.colorVar }}
                >
                  {field.salinity_ec.toFixed(1)}
                </span>
                <span className="text-xs text-ink-muted">dS/m</span>
              </div>
              {TrendIcon && (
                <span
                  className={cx(
                    'mt-0.5 inline-flex items-center gap-1 text-[11px] font-medium',
                    rising ? 'text-serious' : 'text-good',
                  )}
                >
                  <TrendIcon size={11} aria-hidden />
                  {Math.abs(field.salinity_delta).toFixed(2)} in 30 d
                </span>
              )}
            </div>
            <Sparkline values={field.sparkline} color={meta.colorVar} width={100} height={32} />
          </div>

          {/* Footer stats */}
          <div
            className="mt-3 grid grid-cols-2 gap-2 pt-3 text-[11px]"
            style={{ borderTop: '1px solid var(--border)' }}
          >
            <div>
              <p className="text-ink-muted">Health</p>
              <p
                className="tabular font-semibold"
                style={{ color: healthColor(field.health_score) }}
              >
                {field.health_score.toFixed(0)}/100
              </p>
            </div>
            <div>
              <p className="text-ink-muted">Water need</p>
              <p className="tabular flex items-center gap-1 font-semibold text-ink">
                <Droplets size={10} aria-hidden />
                {Math.round(field.irrigation_need_mm)} mm
              </p>
            </div>
          </div>

          {/* Top action */}
          {field.top_action && (
            <div
              className="mt-3 flex items-center gap-1.5 rounded-xl px-2.5 py-2"
              style={{
                background: 'var(--accent-soft)',
                border: '1px solid rgba(212,175,55,0.15)',
              }}
            >
              <p className="min-w-0 flex-1 truncate text-[11px] font-medium"
                 style={{ color: 'var(--accent)' }}>
                {field.top_action}
              </p>
              <ArrowRight
                size={12}
                className="shrink-0 transition group-hover:translate-x-0.5"
                style={{ color: 'var(--accent)' }}
                aria-hidden
              />
            </div>
          )}
        </div>
      </Link>
    </motion.div>
  )
}
