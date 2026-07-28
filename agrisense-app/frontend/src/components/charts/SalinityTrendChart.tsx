/**
 * Measured soil salinity plus the forecast trajectory, against the crop's
 * tolerance threshold.
 *
 * The threshold line is the point of the chart. A salinity number in isolation
 * means nothing to a farmer; the same number against "wheat starts losing yield
 * here" is a decision. Historical and forecast segments share one axis and one
 * hue, distinguished by a dashed stroke, because they are the same quantity.
 */
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS, ChartTooltip, ChartWithTable, GRID, LINE_WIDTH, LegendRow } from './chartBase'
import { shortDate } from '../../lib/format'
import type { ForecastPoint, Reading } from '../../types/api'

interface Point {
  date: string
  measured?: number
  forecast?: number
}

export default function SalinityTrendChart({
  readings,
  forecast,
  threshold,
  cropName,
  height = 260,
}: {
  readings: Reading[]
  forecast: ForecastPoint[]
  threshold: number
  cropName: string
  height?: number
}) {
  // Down-sample history so the line stays legible; a reading per day over 90
  // days renders as noise at this width.
  const step = Math.max(1, Math.floor(readings.length / 60))
  const history: Point[] = readings
    .filter((_, i) => i % step === 0 || i === readings.length - 1)
    .map((r) => ({ date: r.ts, measured: Number(r.soil_ec.toFixed(2)) }))

  const bridge = history.length ? history[history.length - 1].measured : undefined
  const projected: Point[] = forecast.map((f, i) => ({
    date: f.date,
    forecast: f.salinity_ec,
    // Seed the first forecast point with the last measured value so the two
    // segments join instead of showing a visual gap.
    ...(i === 0 && bridge !== undefined ? { measured: bridge } : {}),
  }))

  const data = [...history, ...projected]
  if (!data.length) return null

  const values = data.flatMap((d) => [d.measured, d.forecast].filter((v): v is number => v != null))
  const maxValue = Math.max(...values, threshold)

  const tableData = data.map((d) => ({
    date: d.date,
    measured: d.measured?.toFixed(2) ?? '—',
    forecast: d.forecast?.toFixed(2) ?? '—',
    tolerance: threshold.toFixed(1),
  }))
  const tableColumns = [
    { key: 'date' as const, label: 'Date' },
    { key: 'measured' as const, label: 'Measured (dS/m)' },
    { key: 'forecast' as const, label: 'Forecast (dS/m)' },
    { key: 'tolerance' as const, label: `${cropName} tolerance (dS/m)` },
  ]

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <LegendRow
          items={[
            { label: 'Measured', color: 'var(--series-1)' },
            { label: 'Forecast', color: 'var(--series-1)', dashed: true },
            { label: `${cropName} tolerance`, color: 'var(--status-critical)', dashed: true },
          ]}
        />
      </div>

      <ChartWithTable data={tableData} columns={tableColumns}>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={{ top: 6, right: 10, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id="salinityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--series-1)" stopOpacity={0.28} />
              <stop offset="100%" stopColor="var(--series-1)" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid {...GRID} />
          <XAxis
            dataKey="date"
            tickFormatter={shortDate}
            minTickGap={44}
            {...AXIS}
          />
          <YAxis
            domain={[0, Math.ceil(maxValue * 1.15)]}
            width={46}
            {...AXIS}
            label={{
              value: 'dS/m',
              position: 'insideTopLeft',
              offset: 6,
              fill: 'var(--text-muted)',
              fontSize: 10,
            }}
          />

          <ReferenceLine
            y={threshold}
            stroke="var(--status-critical)"
            strokeDasharray="4 4"
            strokeWidth={1.5}
          />

          <Tooltip
            cursor={{ stroke: 'var(--border-strong)', strokeWidth: 1 }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              const point = payload[0].payload as Point
              const value = point.forecast ?? point.measured
              if (value == null) return null
              const over = value - threshold
              return (
                <ChartTooltip
                  title={shortDate(String(label))}
                  rows={[
                    {
                      label: point.forecast != null ? 'Forecast' : 'Measured',
                      value: `${value.toFixed(2)} dS/m`,
                      color: 'var(--series-1)',
                    },
                  ]}
                  footer={
                    over > 0
                      ? `${over.toFixed(1)} dS/m above ${cropName} tolerance`
                      : `${Math.abs(over).toFixed(1)} dS/m of headroom`
                  }
                />
              )
            }}
          />

          <Area
            type="monotone"
            dataKey="measured"
            stroke="none"
            fill="url(#salinityFill)"
            connectNulls
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="measured"
            stroke="var(--series-1)"
            strokeWidth={LINE_WIDTH}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="var(--series-1)"
            strokeWidth={LINE_WIDTH}
            strokeDasharray="5 4"
            dot={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
      </ChartWithTable>
    </div>
  )
}
