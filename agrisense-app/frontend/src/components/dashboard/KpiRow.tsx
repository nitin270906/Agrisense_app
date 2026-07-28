/**
 * Portfolio headline figures.
 *
 * Each tile leads with one number — the number that tells the farmer
 * whether today is a problem or not. A coloured top rule reinforces the
 * meaning: gold for informational, status colour for risk-keyed metrics.
 */
import { motion } from 'framer-motion'
import { Droplets, Gauge as GaugeIcon, Leaf, TriangleAlert } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Skeleton } from '../ui/primitives'
import { healthColor } from '../../lib/risk'
import type { DashboardSummary } from '../../types/api'

function Tile({
  icon: Icon,
  label,
  value,
  unit,
  hint,
  accentColor,
  index,
}: {
  icon: LucideIcon
  label: string
  value: string
  unit?: string
  hint?: string
  accentColor?: string
  index: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1], delay: index * 0.06 }}
      className="overflow-hidden rounded-2xl bg-surface-1"
      style={{
        boxShadow: 'var(--shadow-card)',
        border: '1px solid var(--border)',
      }}
    >
      {/* Coloured top rule */}
      <div
        className="h-[3px] w-full"
        style={{ background: accentColor ?? 'var(--accent-fill)' }}
      />

      <div className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs font-medium leading-tight text-ink-muted">{label}</p>
          <Icon size={14} className="mt-0.5 shrink-0 text-ink-muted" aria-hidden />
        </div>

        <p
          className="mt-3 text-3xl font-bold tracking-tight"
          style={{ color: accentColor ?? 'var(--text-primary)' }}
        >
          {value}
          {unit && (
            <span className="ml-1.5 text-sm font-normal text-ink-muted">{unit}</span>
          )}
        </p>

        {hint && (
          <p className="mt-1.5 text-[11px] leading-relaxed text-ink-muted">{hint}</p>
        )}
      </div>
    </motion.div>
  )
}

export default function KpiRow({
  data,
  loading,
}: {
  data?: DashboardSummary
  loading: boolean
}) {
  if (loading || !data) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[116px] rounded-2xl" />
        ))}
      </div>
    )
  }

  const atRiskColor =
    data.fields_at_risk > 0 ? 'var(--status-serious)' : 'var(--status-good)'

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Tile
        index={0}
        icon={TriangleAlert}
        label="Fields at risk"
        value={String(data.fields_at_risk)}
        unit={`of ${data.total_fields}`}
        hint={
          data.critical_alerts > 0
            ? `${data.critical_alerts} critical alert${data.critical_alerts > 1 ? 's' : ''}`
            : 'No critical fields'
        }
        accentColor={atRiskColor}
      />
      <Tile
        index={1}
        icon={GaugeIcon}
        label="Average salinity"
        value={data.avg_salinity_ec.toFixed(1)}
        unit="dS/m"
        hint="Across all monitored plots"
      />
      <Tile
        index={2}
        icon={Leaf}
        label="Average crop health"
        value={data.avg_health_score.toFixed(0)}
        unit="/ 100"
        hint="Modelled relative yield"
        accentColor={healthColor(data.avg_health_score)}
      />
      <Tile
        index={3}
        icon={Droplets}
        label="Irrigation needed"
        value={Math.round(data.total_irrigation_need_mm).toLocaleString()}
        unit="mm"
        hint={`Over ${data.total_area_ha.toFixed(0)} ha`}
      />
    </div>
  )
}
