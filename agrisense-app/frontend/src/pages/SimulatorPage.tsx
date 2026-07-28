/**
 * What-if simulator.
 *
 * The dashboard answers "what is happening"; this answers "what if I did
 * something different", which is the question a farmer actually has. Both curves
 * are the same physics engine, so the comparison is like-for-like — only the
 * levers differ.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Play, TrendingDown, TrendingUp } from 'lucide-react'
import { useCrops, useFields, useSimulation } from '../api/hooks'
import { AXIS, ChartTooltip, GRID, LINE_WIDTH, LegendRow } from '../components/charts/chartBase'
import { Card, CardHeader, Skeleton } from '../components/ui/primitives'
import { cx, shortDate, titleCase } from '../lib/format'

function Slider({
  label,
  value,
  min,
  max,
  step,
  unit,
  hint,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  unit: string
  hint?: string
  onChange: (value: number) => void
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <label className="text-xs font-medium text-ink-soft">{label}</label>
        <span className="tabular text-xs font-semibold text-ink">
          {value}
          <span className="ml-0.5 font-normal text-ink-muted">{unit}</span>
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-surface-3 accent-[var(--accent)]"
      />
      {hint && <p className="mt-1 text-[10px] text-ink-muted">{hint}</p>}
    </div>
  )
}

export default function SimulatorPage() {
  const { fieldId } = useParams()
  const navigate = useNavigate()
  const { data: fields } = useFields()
  const { data: crops } = useCrops()

  const selectedId = Number(fieldId ?? 0) || fields?.[0]?.id || 0
  const field = fields?.find((f) => f.id === selectedId)
  const crop = crops?.find((c) => c.crop === field?.crop)

  const [irrigationMm, setIrrigationMm] = useState(60)
  const [waterEc, setWaterEc] = useState<number | null>(null)
  const [intervalDays, setIntervalDays] = useState(10)
  const [rainfall, setRainfall] = useState(1)
  const [drainageClass, setDrainageClass] = useState<'well' | 'moderate' | 'poor'>('moderate')
  const [fertilizerRate, setFertilizerRate] = useState(1.0)
  const [mulching, setMulching] = useState(false)

  const simulation = useSimulation(selectedId)
  const { mutate, data, isPending } = simulation

  // Seed the water-salinity slider from the field's actual supply once loaded.
  useEffect(() => {
    if (field && waterEc === null) setWaterEc(field.irrigation_water_ec)
  }, [field, waterEc])

  const run = () => {
    if (!selectedId) return
    mutate({
      irrigation_mm: irrigationMm,
      irrigation_water_ec: waterEc,
      irrigation_interval_days: intervalDays,
      rainfall_scenario: rainfall,
      horizon_days: 30,
      drainage_class: drainageClass,
      fertilizer_rate: fertilizerRate,
      mulching: mulching,
    })
  }

  // Auto-run simulation on initial mount or field select
  const hasRun = useRef(false)
  useEffect(() => {
    if (selectedId && !hasRun.current) {
      hasRun.current = true
      mutate({
        irrigation_mm: irrigationMm,
        irrigation_water_ec: waterEc ?? field?.irrigation_water_ec ?? 2.0,
        irrigation_interval_days: intervalDays,
        rainfall_scenario: rainfall,
        horizon_days: 30,
      })
    }
  }, [selectedId, field]) // eslint-disable-line react-hooks/exhaustive-deps

  const chartData = useMemo(() => {
    if (!data) return []
    return data.baseline.map((point, i) => ({
      date: point.date,
      baseline: point.salinity_ec,
      scenario: data.scenario[i]?.salinity_ec ?? null,
    }))
  }, [data])

  const improving = (data?.salinity_change ?? 0) < 0

  return (
    <motion.div
      className="space-y-5"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
          Irrigation simulator
        </h1>
        <p className="mt-1 text-xs text-ink-muted sm:text-sm">
          Test a watering plan against carrying on unchanged, over the next 30 days.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* --- controls --------------------------------------------- */}
        <Card className="space-y-5 lg:col-span-1">
          <CardHeader title="Scenario" subtitle="Adjust and run" />

          <div>
            <label className="text-xs font-medium text-ink-soft">Field</label>
            <select
              value={selectedId}
              onChange={(e) => navigate(`/fields/${e.target.value}/simulate`)}
              className="mt-1.5 w-full rounded-lg border border-edge bg-surface-2 px-3 py-2 text-xs text-ink outline-none focus:border-edge-strong"
            >
              {fields?.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} · {titleCase(f.crop)}
                </option>
              ))}
            </select>
          </div>

          <Slider
            label="Water per irrigation"
            value={irrigationMm}
            min={0}
            max={150}
            step={5}
            unit=" mm"
            onChange={setIrrigationMm}
          />

          <Slider
            label="Irrigation interval"
            value={intervalDays}
            min={3}
            max={30}
            step={1}
            unit=" days"
            hint={`Roughly ${Math.floor(30 / intervalDays)} events in 30 days`}
            onChange={setIntervalDays}
          />

          <Slider
            label="Irrigation water salinity"
            value={waterEc ?? 1}
            min={0}
            max={8}
            step={0.1}
            unit=" dS/m"
            hint={
              field
                ? `Your current supply is ${field.irrigation_water_ec.toFixed(1)} dS/m`
                : undefined
            }
            onChange={setWaterEc}
          />

          <Slider
            label="Rainfall scenario"
            value={rainfall}
            min={0}
            max={2}
            step={0.1}
            unit="×"
            hint="Multiplier on the forecast — test a dry or wet month"
            onChange={setRainfall}
          />

          <div>
            <label className="text-xs font-medium text-ink-soft">Drainage class</label>
            <select
              value={drainageClass}
              onChange={(e) => setDrainageClass(e.target.value as 'well' | 'moderate' | 'poor')}
              className="mt-1.5 w-full rounded-lg border border-edge bg-surface-2 px-3 py-2 text-xs text-ink outline-none focus:border-edge-strong"
            >
              <option value="well">Well drained</option>
              <option value="moderate">Moderately drained</option>
              <option value="poor">Poorly drained</option>
            </select>
          </div>

          <Slider
            label="Fertilizer rate"
            value={fertilizerRate}
            min={0}
            max={2}
            step={0.1}
            unit="×"
            hint="Multiplier on standard application rate"
            onChange={setFertilizerRate}
          />

          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-ink-soft">Mulching</label>
            <button
              onClick={() => setMulching(!mulching)}
              className={cx(
                'relative h-6 w-11 rounded-full transition-colors',
                mulching ? 'bg-accent' : 'bg-surface-3'
              )}
            >
              <span
                className={cx(
                  'absolute top-1 block h-4 w-4 rounded-full bg-white transition-transform',
                  mulching ? 'translate-x-6' : 'translate-x-1'
                )}
              />
            </button>
          </div>

          <button
            onClick={run}
            disabled={isPending || !selectedId}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-accent-ink transition hover:opacity-90 disabled:opacity-50"
          >
            <Play size={14} aria-hidden />
            {isPending ? 'Simulating…' : 'Run simulation'}
          </button>
        </Card>

        {/* --- results ---------------------------------------------- */}
        <div className="space-y-4 lg:col-span-2">
          {!data && !isPending && (
            <Card className="flex h-[300px] flex-col items-center justify-center text-center">
              <p className="text-sm font-medium text-ink-soft">No simulation yet</p>
              <p className="mt-1 max-w-sm text-xs text-ink-muted">
                Set a watering plan and run it. The chart will compare your scenario
                against what happens if nothing changes.
              </p>
            </Card>
          )}

          {isPending && <Skeleton className="h-[300px]" />}

          {data && (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <Card>
                  <p className="text-xs text-ink-muted">Salinity change</p>
                  <p
                    className="mt-1.5 flex items-center gap-1.5 text-xl font-semibold"
                    style={{
                      color: improving ? 'var(--status-good)' : 'var(--status-serious)',
                    }}
                  >
                    {improving ? <TrendingDown size={16} /> : <TrendingUp size={16} />}
                    {data.salinity_change > 0 ? '+' : ''}
                    {data.salinity_change.toFixed(2)}
                    <span className="text-xs font-normal text-ink-muted">dS/m</span>
                  </p>
                </Card>
                <Card>
                  <p className="text-xs text-ink-muted">Health change</p>
                  <p
                    className="mt-1.5 text-xl font-semibold"
                    style={{
                      color:
                        data.health_change >= 0
                          ? 'var(--status-good)'
                          : 'var(--status-serious)',
                    }}
                  >
                    {data.health_change > 0 ? '+' : ''}
                    {data.health_change.toFixed(0)}
                    <span className="ml-1 text-xs font-normal text-ink-muted">pts</span>
                  </p>
                </Card>
                <Card className="col-span-2 sm:col-span-1">
                  <p className="text-xs text-ink-muted">Water applied</p>
                  <p className="mt-1.5 text-xl font-semibold text-ink">
                    {Math.round(data.water_applied_mm)}
                    <span className="ml-1 text-xs font-normal text-ink-muted">mm</span>
                  </p>
                </Card>
              </div>

              <Card>
                <CardHeader title="Projected salinity" subtitle="Scenario against no change" />
                <div className="mb-3">
                  <LegendRow
                    items={[
                      { label: 'No change', color: 'var(--series-3)', dashed: true },
                      { label: 'Your scenario', color: 'var(--series-1)' },
                      ...(crop
                        ? [
                            {
                              label: `${crop.display_name} tolerance`,
                              color: 'var(--status-critical)',
                              dashed: true,
                            },
                          ]
                        : []),
                    ]}
                  />
                </div>

                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={chartData} margin={{ top: 6, right: 10, bottom: 0, left: -18 }}>
                    <CartesianGrid {...GRID} />
                    <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={40} {...AXIS} />
                    <YAxis width={46} {...AXIS} />

                    {crop && (
                      <ReferenceLine
                        y={crop.salt_threshold_a}
                        stroke="var(--status-critical)"
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                      />
                    )}

                    <Tooltip
                      cursor={{ stroke: 'var(--border-strong)', strokeWidth: 1 }}
                      content={({ active, payload, label }) => {
                        if (!active || !payload?.length) return null
                        const p = payload[0].payload as (typeof chartData)[number]
                        return (
                          <ChartTooltip
                            title={shortDate(String(label))}
                            rows={[
                              {
                                label: 'Your scenario',
                                value: `${p.scenario?.toFixed(2)} dS/m`,
                                color: 'var(--series-1)',
                              },
                              {
                                label: 'No change',
                                value: `${p.baseline?.toFixed(2)} dS/m`,
                                color: 'var(--series-3)',
                              },
                            ]}
                          />
                        )
                      }}
                    />

                    <Line
                      type="monotone"
                      dataKey="baseline"
                      stroke="var(--series-3)"
                      strokeWidth={LINE_WIDTH}
                      strokeDasharray="5 4"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="scenario"
                      stroke="var(--series-1)"
                      strokeWidth={LINE_WIDTH}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>

                <p
                  className={cx(
                    'mt-4 rounded-lg border-l-[3px] bg-surface-2 p-3 text-xs leading-relaxed text-ink-soft',
                  )}
                  style={{
                    borderLeftColor: improving
                      ? 'var(--status-good)'
                      : 'var(--status-warning)',
                  }}
                >
                  {data.summary}
                </p>
              </Card>
            </>
          )}
        </div>
      </div>
    </motion.div>
  )
}
