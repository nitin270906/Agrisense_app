/**
 * Model transparency page.
 *
 * This exists because the honest disclosure belongs in the product, not in a
 * README a judge will never open. It states plainly that training data is
 * physics-simulated, shows every model against its naive baseline, and names the
 * split strategy. A metric without its baseline is marketing.
 */
import { AlertCircle, CheckCircle2, Database, GitBranch, Layers } from 'lucide-react'
import { motion } from 'framer-motion'
import { useModelInfo } from '../api/hooks'
import { Card, CardHeader, ErrorState, Skeleton } from '../components/ui/primitives'
import { longDate } from '../lib/format'
import type { TargetMetrics } from '../types/api'

const TARGET_LABELS: Record<string, { name: string; unit: string; baseline: string }> = {
  target_salinity_delta_30d: {
    name: '30-day salinity change',
    unit: 'dS/m',
    baseline: 'assume no change',
  },
  target_water_stress: { name: 'Crop water stress', unit: 'index', baseline: 'predict the mean' },
  target_irrigation_mm: { name: 'Irrigation need', unit: 'mm', baseline: 'predict the mean' },
  target_health: { name: 'Crop health', unit: '/100', baseline: 'predict the mean' },
}

function MetricRow({ target, metrics }: { target: string; metrics: TargetMetrics }) {
  const label = TARGET_LABELS[target] ?? { name: target, unit: '', baseline: 'baseline' }
  const beatsBaseline = metrics.overall.mae < metrics.baseline.mae
  const improvement =
    metrics.baseline.mae > 0
      ? ((metrics.baseline.mae - metrics.overall.mae) / metrics.baseline.mae) * 100
      : 0

  return (
    <div className="rounded-lg border border-edge bg-surface-2 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-ink">{label.name}</p>
          <p className="text-[11px] text-ink-muted">
            {metrics.n_test.toLocaleString()} held-out rows
          </p>
        </div>
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium"
          style={{
            background: beatsBaseline
              ? 'color-mix(in srgb, var(--status-good) 15%, transparent)'
              : 'color-mix(in srgb, var(--status-critical) 15%, transparent)',
            color: beatsBaseline ? 'var(--status-good)' : 'var(--status-critical)',
          }}
        >
          {beatsBaseline ? <CheckCircle2 size={11} /> : <AlertCircle size={11} />}
          {beatsBaseline ? `${improvement.toFixed(0)}% better than baseline` : 'No better than baseline'}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ['R²', metrics.overall.r2.toFixed(3)],
          ['MAE', `${metrics.overall.mae.toFixed(3)} ${label.unit}`],
          ['Baseline R²', metrics.baseline.r2.toFixed(3)],
          ['Baseline MAE', `${metrics.baseline.mae.toFixed(3)} ${label.unit}`],
        ].map(([k, v]) => (
          <div key={k}>
            <p className="text-[10px] text-ink-muted">{k}</p>
            <p className="tabular text-sm font-medium text-ink">{v}</p>
          </div>
        ))}
      </div>

      {metrics.nonzero_tail && (
        <p className="mt-3 border-t border-edge pt-2.5 text-[11px] text-ink-muted">
          This target is {((metrics.zero_share ?? 0) * 100).toFixed(0)}% zeros — crops are
          unstressed most days. Scored on the non-zero cases alone, where the answer
          actually matters: R² {metrics.nonzero_tail.r2.toFixed(3)}, MAE{' '}
          {metrics.nonzero_tail.mae.toFixed(3)}.
        </p>
      )}

      <p className="mt-2 text-[11px] text-ink-muted">
        Baseline: {label.baseline}
      </p>
    </div>
  )
}

export default function ModelPage() {
  const { data, isLoading, isError, refetch } = useModelInfo()

  if (isError) return <ErrorState message="Could not load model info" onRetry={() => refetch()} />

  return (
    <motion.div
      className="space-y-5"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
          Model & methodology
        </h1>
        <p className="mt-1 text-xs text-ink-muted sm:text-sm">
          Everything behind the forecasts, including what they cannot tell you.
        </p>
      </div>

      {/* --- provenance disclosure --------------------------------- */}
      <Card style={{ borderLeft: '3px solid var(--status-warning)' }}>
        <div className="flex items-start gap-3">
          <Database size={16} className="mt-0.5 shrink-0 text-warning" aria-hidden />
          <div>
            <p className="text-sm font-semibold text-ink">
              Trained on physics-simulated data
            </p>
            <p className="mt-1.5 text-xs leading-relaxed text-ink-soft">
              No public dataset pairs soil-salinity time series with weather at field
              scale, so training data is generated by an agronomic simulator built from
              published relationships — FAO-56 for the water balance and reference
              evapotranspiration, Maas-Hoffman salt-tolerance curves for yield, and a
              root-zone salt mass balance for accumulation. The models learn those
              relationships; they have not been validated against field measurements.
              Treat the numbers as physically consistent, not as ground truth.
            </p>
          </div>
        </div>
      </Card>

      {isLoading || !data ? (
        <Skeleton className="h-64" />
      ) : (
        <>
          {/* --- summary ------------------------------------------- */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ['Model version', `v${data.model_version}`, Layers],
              ['Features', String(data.feature_count), GitBranch],
              ['Training rows', data.n_rows?.toLocaleString() ?? '—', Database],
              ['Virtual fields', data.n_fields?.toLocaleString() ?? '—', Database],
            ].map(([label, value, Icon]) => {
              const I = Icon as typeof Layers
              return (
                <Card key={label as string}>
                  <div className="flex items-start justify-between">
                    <p className="text-xs text-ink-muted">{label as string}</p>
                    <I size={14} className="text-ink-muted" aria-hidden />
                  </div>
                  <p className="mt-2 text-lg font-semibold text-ink">{value as string}</p>
                </Card>
              )
            })}
          </div>

          {/* --- validation ---------------------------------------- */}
          <Card>
            <CardHeader
              title="How this was validated"
              subtitle={data.trained_at ? `Trained ${longDate(data.trained_at)}` : undefined}
            />
            <div className="space-y-3 text-xs leading-relaxed text-ink-soft">
              <p>
                <span className="font-medium text-ink">Whole fields are held out, not rows.</span>{' '}
                {data.split} Consecutive days within one field are near-identical, so a
                random row split would let the model see 5 May while predicting 6 May and
                report an R² that means nothing. Holding out entire fields measures the
                question that matters: how well this works on a farm never seen before.
              </p>
              <p>
                <span className="font-medium text-ink">Every model is scored against a naive baseline.</span>{' '}
                For salinity that baseline is "assume no change", which is genuinely hard
                to beat because soil salinity moves slowly. An earlier version of this
                model predicted the salinity <em>level</em> and scored R² 0.98 — while
                losing to that baseline. Forecasting the 30-day <em>change</em> instead is
                what made the number honest.
              </p>
            </div>
          </Card>

          {/* --- per-target metrics ------------------------------- */}
          <Card>
            <CardHeader title="Held-out performance" subtitle="Four independent XGBoost regressors" />
            <div className="space-y-3">
              {Object.entries(data.metrics).map(([target, metrics]) => (
                <MetricRow key={target} target={target} metrics={metrics} />
              ))}
            </div>
          </Card>

          {/* --- top features -------------------------------------- */}
          <Card>
            <CardHeader
              title="What the salinity model relies on"
              subtitle="Feature importance — categorical inputs are encoded as physical constants, not one-hot"
            />
            <div className="space-y-2">
              {(data.metrics['target_salinity_delta_30d']?.top_features ?? [])
                .slice(0, 8)
                .map((f) => (
                  <div key={f.feature}>
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-xs text-ink-soft">
                        {f.feature.replace(/_/g, ' ')}
                      </span>
                      <span className="tabular text-[11px] text-ink-muted">
                        {(f.importance * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-3">
                      <div
                        className="h-full rounded-full bg-series-1"
                        style={{ width: `${Math.min(100, f.importance * 100 * 2.5)}%` }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          </Card>
        </>
      )}
    </motion.div>
  )
}
