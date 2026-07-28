/**
 * The four ML forecasts as premium stat tiles.
 *
 * Each carries model confidence and a plain-language caption — a number alone
 * tells you nothing; "4.5 dS/m, within wheat tolerance" is actionable.
 */
import { motion } from 'framer-motion'
import { Droplets, Leaf, TrendingDown, TrendingUp, Waves, Wind } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { healthColor, riskMeta, stressColor } from '../../lib/risk'
import type { Prediction } from '../../types/api'

function StatTile({
  icon: Icon,
  label,
  value,
  unit,
  accentColor,
  caption,
  delta,
  index,
}: {
  icon: LucideIcon
  label: string
  value: string
  unit: string
  accentColor?: string
  caption: string
  delta?: { value: number; goodWhenNegative?: boolean }
  index: number
}) {
  const showDelta = delta && Math.abs(delta.value) >= 0.01
  const improving = showDelta
    ? delta.goodWhenNegative
      ? delta.value < 0
      : delta.value > 0
    : false
  const DeltaIcon = showDelta && delta.value > 0 ? TrendingUp : TrendingDown

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.46, ease: [0.22, 1, 0.36, 1], delay: index * 0.07 }}
      className="overflow-hidden rounded-2xl bg-surface-1"
      style={{
        boxShadow: 'var(--shadow-card)',
        border: '1px solid var(--border)',
      }}
    >
      {/* Accent rule keyed to the metric's risk/status colour */}
      <div
        className="h-[3px]"
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
          <span className="ml-1.5 text-sm font-normal text-ink-muted">{unit}</span>
        </p>

        {showDelta && (
          <p
            className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium"
            style={{
              color: improving ? 'var(--status-good)' : 'var(--status-serious)',
            }}
          >
            <DeltaIcon size={11} aria-hidden />
            {delta.value > 0 ? '+' : ''}
            {delta.value.toFixed(2)} over 30 days
          </p>
        )}

        <p className="mt-2.5 text-[11px] leading-relaxed text-ink-muted">{caption}</p>
      </div>
    </motion.div>
  )
}

export default function PredictionCards({
  prediction,
  threshold,
  cropName,
}: {
  prediction: Prediction
  threshold: number
  cropName: string
}) {
  const meta = riskMeta(prediction.risk_level)
  const headroom = threshold - prediction.salinity_ec

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <StatTile
        index={0}
        icon={Waves}
        label={`Soil salinity · ${prediction.horizon_days}-day forecast`}
        value={prediction.salinity_ec.toFixed(1)}
        unit="dS/m"
        accentColor={meta.colorVar}
        delta={{ value: prediction.salinity_delta, goodWhenNegative: true }}
        caption={
          prediction.salinity_ec_p10 != null && prediction.salinity_ec_p90 != null
            ? `${prediction.salinity_ec_p10.toFixed(1)}–${prediction.salinity_ec_p90.toFixed(1)} dS/m 80% interval`
            : headroom >= 0
              ? `${headroom.toFixed(1)} dS/m below ${cropName} tolerance`
              : `${Math.abs(headroom).toFixed(1)} dS/m above ${cropName} tolerance`
        }
      />

      <StatTile
        index={1}
        icon={Wind}
        label="Crop water stress"
        value={Math.round(prediction.water_stress_index * 100).toString()}
        unit="%"
        accentColor={stressColor(prediction.water_stress_index)}
        caption={
          prediction.water_stress_index < 0.05
            ? 'Crop is fully supplied with water'
            : prediction.water_stress_index < 0.3
              ? 'Mild stress — still within tolerance'
              : 'Transpiration restricted — yield at risk'
        }
      />

      <StatTile
        index={2}
        icon={Droplets}
        label="Irrigation needed"
        value={Math.round(prediction.irrigation_need_mm).toString()}
        unit="mm"
        caption={
          prediction.irrigation_need_mm < 5
            ? 'Soil water is adequate — hold off'
            : 'Includes extra depth to carry salt below the roots'
        }
      />

      <StatTile
        index={3}
        icon={Leaf}
        label="Crop health"
        value={prediction.health_score.toFixed(0)}
        unit="/ 100"
        accentColor={healthColor(prediction.health_score)}
        caption={`Modelled relative yield · ${Math.round(prediction.confidence * 100)}% model confidence`}
      />
    </div>
  )
}
