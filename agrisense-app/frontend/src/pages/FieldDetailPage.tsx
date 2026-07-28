import { Link, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Activity,
  ArrowLeft,
  CloudOff,
  Info,
  RefreshCw,
} from 'lucide-react'
import {
  useCrops,
  useField,
  useForecast,
  usePredictMutation,
  usePrediction,
  useReadings,
  useRecommendations,
  useWeather,
} from '../api/hooks'
import Gauge from '../components/charts/Gauge'
import SalinityTrendChart from '../components/charts/SalinityTrendChart'
import StressChart from '../components/charts/StressChart'
import WeatherChart from '../components/charts/WeatherChart'
import PredictionCards from '../components/field/PredictionCards'
import RecommendationList from '../components/field/RecommendationList'
import { Card, CardHeader, ErrorState, RiskBadge, Skeleton } from '../components/ui/primitives'
import { cx, longDate, titleCase } from '../lib/format'
import { healthColor } from '../lib/risk'

export default function FieldDetailPage() {
  const { fieldId } = useParams()
  const id = Number(fieldId ?? 0)

  const field = useField(id)
  const prediction = usePrediction(id)
  const readings = useReadings(id, 90)
  const forecast = useForecast(id, 30)
  const weather = useWeather(id)
  const recommendations = useRecommendations(id)
  const { data: crops } = useCrops()
  const rerun = usePredictMutation(id)

  const crop = crops?.find((c) => c.crop === field.data?.crop)
  const threshold = crop?.salt_threshold_a ?? 4
  const cropName = crop?.display_name ?? titleCase(field.data?.crop ?? 'crop')

  if (field.isError) {
    return (
      <ErrorState
        message={field.error instanceof Error ? field.error.message : 'Field not found'}
      />
    )
  }

  return (
    <motion.div
      className="space-y-5"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* --- header ---------------------------------------------------- */}
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-ink-muted transition hover:text-ink"
        >
          <ArrowLeft size={13} aria-hidden />
          All fields
        </Link>

        <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {field.isLoading ? (
              <Skeleton className="h-8 w-52" />
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2.5">
                  <h1 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
                    {field.data?.name}
                  </h1>
                  {prediction.data && <RiskBadge level={prediction.data.risk_level} showRange />}
                </div>
                <p className="mt-1 text-xs text-ink-muted sm:text-sm">
                  {cropName} · {field.data?.area_ha.toFixed(1)} ha ·{' '}
                  {titleCase(field.data?.soil_texture ?? '')} soil ·{' '}
                  {titleCase(field.data?.drainage_class ?? '')} drainage · water table{' '}
                  {field.data?.water_table_depth_m.toFixed(1)} m
                </p>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Link
              to={`/fields/${id}/simulate`}
              className="flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold text-accent-ink transition hover:opacity-90"
              style={{ background: 'var(--accent-fill)' }}
            >
              <Activity size={13} aria-hidden />
              Simulate
            </Link>
            <button
              onClick={() => rerun.mutate()}
              disabled={rerun.isPending}
              className="flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold text-ink-soft transition hover:bg-surface-2 hover:text-ink disabled:opacity-50"
              style={{ border: '1px solid var(--border-strong)' }}
            >
              <RefreshCw size={13} className={cx(rerun.isPending && 'animate-spin')} aria-hidden />
              Re-run
            </button>
          </div>
        </div>
      </div>

      {/* --- stale weather notice -------------------------------------- */}
      {weather.data?.stale && (
        <div className="flex items-center gap-2.5 rounded-lg border border-edge bg-surface-2 px-3.5 py-2.5">
          <CloudOff size={14} className="text-warning" aria-hidden />
          <p className="text-[11px] text-ink-soft">
            Live weather is unreachable — showing the last cached forecast. Predictions
            remain available.
          </p>
        </div>
      )}

      {/* --- prediction cards ------------------------------------------ */}
      {prediction.isLoading || !prediction.data ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[160px]" />
          ))}
        </div>
      ) : (
        <PredictionCards
          prediction={prediction.data}
          threshold={threshold}
          cropName={cropName}
        />
      )}

      {/* --- main grid -------------------------------------------------- */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader
              title="Soil salinity — 90 days measured, 30 days forecast"
              subtitle={`Dashed red line marks the ${threshold.toFixed(1)} dS/m tolerance for ${cropName.toLowerCase()}`}
            />
            {readings.isLoading || forecast.isLoading ? (
              <Skeleton className="h-[260px]" />
            ) : (
              <SalinityTrendChart
                readings={readings.data ?? []}
                forecast={forecast.data ?? []}
                threshold={threshold}
                cropName={cropName.toLowerCase()}
              />
            )}
          </Card>

          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader title="Projected water stress" subtitle="Next 30 days" />
              {forecast.isLoading ? (
                <Skeleton className="h-[200px]" />
              ) : (
                <StressChart forecast={forecast.data ?? []} />
              )}
            </Card>

            <Card>
              <CardHeader
                title="Crop health"
                subtitle="Salt, water and heat stress combined"
              />
              <div className="flex h-[200px] flex-col items-center justify-center">
                {prediction.data ? (
                  <>
                    <Gauge
                      value={prediction.data.health_score}
                      label="Modelled relative yield"
                      color={healthColor(prediction.data.health_score)}
                    />
                    <p className="mt-3 max-w-[240px] text-center text-[11px] leading-relaxed text-ink-muted">
                      {prediction.data.health_score >= 85
                        ? 'Yield potential largely intact.'
                        : prediction.data.health_score >= 60
                          ? 'Measurable yield loss expected without intervention.'
                          : 'Severe loss projected — act now.'}
                    </p>
                  </>
                ) : (
                  <Skeleton className="h-[132px] w-[132px]" />
                )}
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader
              title="Rainfall vs evaporative demand"
              subtitle={
                weather.data
                  ? `${weather.data.provider === 'open_meteo' ? 'Open-Meteo' : weather.data.provider} · past 92 days and 16-day forecast`
                  : 'Loading weather…'
              }
            />
            {weather.isLoading ? (
              <Skeleton className="h-[220px]" />
            ) : (
              <WeatherChart days={(weather.data?.days ?? []).slice(-45)} />
            )}
          </Card>
        </div>

        {/* --- side rail --------------------------------------------- */}
        <div className="space-y-4">
          <Card>
            <CardHeader
              title="What to do"
              subtitle="Ranked by urgency"
            />
            {recommendations.isLoading ? (
              <Skeleton className="h-64" />
            ) : (
              <RecommendationList items={recommendations.data ?? []} />
            )}
          </Card>

          {/* --- model drivers ------------------------------------- */}
          {!!prediction.data?.drivers?.length && (
            <Card>
              <CardHeader
                title="What drives this forecast"
                subtitle="Top model features by importance"
              />
              <ul className="space-y-2.5">
                {prediction.data.drivers.map((driver) => (
                  <li key={driver.feature}>
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-xs text-ink-soft">{driver.label}</span>
                      <span className="tabular text-xs font-medium text-ink">
                        {driver.value}
                      </span>
                    </div>
                    <div className="mt-1 h-1 overflow-hidden rounded-full bg-surface-3">
                      <div
                        className="h-full rounded-full bg-series-1"
                        style={{ width: `${Math.min(100, driver.importance * 100 * 3)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
              <p className="mt-3 flex items-start gap-1.5 text-[11px] leading-relaxed text-ink-muted">
                <Info size={11} className="mt-0.5 shrink-0" aria-hidden />
                Model v{prediction.data.model_version} ·{' '}
                {Math.round(prediction.data.confidence * 100)}% confidence, reduced when a
                field has little history.
              </p>
            </Card>
          )}

          {/* --- field facts ---------------------------------------- */}
          <Card>
            <CardHeader title="Field record" />
            <dl className="space-y-2 text-xs">
              {[
                ['Crop', cropName],
                ['Salt tolerance', `${threshold.toFixed(1)} dS/m (${crop?.tolerance_label ?? '—'})`],
                ['Irrigation water', `${field.data?.irrigation_water_ec.toFixed(1)} dS/m`],
                ['Water table', `${field.data?.water_table_depth_m.toFixed(1)} m`],
                ['Soil', titleCase(field.data?.soil_texture ?? '')],
                ['Drainage', titleCase(field.data?.drainage_class ?? '')],
                ['Planted', field.data ? longDate(field.data.planting_date) : '—'],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between gap-3">
                  <dt className="text-ink-muted">{label}</dt>
                  <dd className="text-right font-medium text-ink">{value}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>
      </div>
    </motion.div>
  )
}
