/**
 * Rainfall against reference evapotranspiration.
 *
 * Both series are in millimetres, so they legitimately share one axis — this is
 * a genuine comparison of water in versus water out, not a dual-axis chart
 * forcing unrelated scales together. When the ET0 line sits above the rain bars
 * the field is drying and salt is concentrating; that crossover is the story.
 */
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS, ChartTooltip, GRID, LINE_WIDTH, LegendRow } from './chartBase'
import { shortDate } from '../../lib/format'
import type { WeatherDay } from '../../types/api'

export default function WeatherChart({
  days,
  height = 220,
}: {
  days: WeatherDay[]
  height?: number
}) {
  if (!days.length) return null

  const data = days.map((d) => ({
    date: d.date,
    precip: Number(d.precip_mm.toFixed(1)),
    et0: Number(d.et0_mm.toFixed(2)),
    isForecast: d.is_forecast,
    temp: d.t_max_c,
  }))

  const firstForecast = data.find((d) => d.isForecast)?.date

  return (
    <div>
      <div className="mb-3">
        <LegendRow
          items={[
            { label: 'Rainfall', color: 'var(--series-2)' },
            { label: 'Evapotranspiration (ET₀)', color: 'var(--series-3)' },
          ]}
        />
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={{ top: 6, right: 10, bottom: 0, left: -18 }}>
          <CartesianGrid {...GRID} />
          <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={40} {...AXIS} />
          <YAxis
            width={40}
            {...AXIS}
            label={{
              value: 'mm',
              position: 'insideTopLeft',
              offset: 6,
              fill: 'var(--text-muted)',
              fontSize: 10,
            }}
          />

          {firstForecast && (
            <ReferenceLine
              x={firstForecast}
              stroke="var(--border-strong)"
              strokeDasharray="3 3"
              label={{
                value: 'forecast',
                position: 'insideTopRight',
                fill: 'var(--text-muted)',
                fontSize: 10,
              }}
            />
          )}

          <Tooltip
            cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              const p = payload[0].payload as (typeof data)[number]
              return (
                <ChartTooltip
                  title={shortDate(String(label))}
                  rows={[
                    { label: 'Rainfall', value: `${p.precip} mm`, color: 'var(--series-2)' },
                    { label: 'ET₀', value: `${p.et0} mm`, color: 'var(--series-3)' },
                    { label: 'Max temp', value: `${p.temp.toFixed(0)}°C` },
                  ]}
                  footer={
                    p.precip >= p.et0
                      ? 'Net water gain — salts moving down'
                      : 'Net water loss — salts concentrating'
                  }
                />
              )
            }}
          />

          {/* 4px rounded data-ends anchored to the baseline, per the mark spec. */}
          <Bar dataKey="precip" fill="var(--series-2)" radius={[4, 4, 0, 0]} maxBarSize={14} />
          <Line
            type="monotone"
            dataKey="et0"
            stroke="var(--series-3)"
            strokeWidth={LINE_WIDTH}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
