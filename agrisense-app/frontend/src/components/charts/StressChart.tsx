/**
 * Projected crop water stress over the forecast horizon.
 *
 * Kept as its own chart rather than overlaid on rainfall: stress is a unitless
 * 0–1 index and millimetres are millimetres, and forcing them onto one frame
 * would mean a second y-axis. Two honest charts beat one misleading one.
 */
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS, ChartTooltip, GRID, LINE_WIDTH } from './chartBase'
import { shortDate } from '../../lib/format'
import type { ForecastPoint } from '../../types/api'

const STRESS_ONSET = 0.3

export default function StressChart({
  forecast,
  height = 200,
}: {
  forecast: ForecastPoint[]
  height?: number
}) {
  if (!forecast.length) return null

  const data = forecast.map((f) => ({
    date: f.date,
    stress: Number(f.water_stress_index.toFixed(3)),
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 6, right: 10, bottom: 0, left: -22 }}>
        <defs>
          <linearGradient id="stressFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--series-4)" stopOpacity={0.32} />
            <stop offset="100%" stopColor="var(--series-4)" stopOpacity={0.02} />
          </linearGradient>
        </defs>

        <CartesianGrid {...GRID} />
        <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={40} {...AXIS} />
        <YAxis
          domain={[0, 1]}
          ticks={[0, 0.25, 0.5, 0.75, 1]}
          tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
          width={46}
          {...AXIS}
        />

        <ReferenceLine
          y={STRESS_ONSET}
          stroke="var(--status-warning)"
          strokeDasharray="4 4"
          strokeWidth={1.5}
          label={{
            value: 'stress onset',
            position: 'insideTopRight',
            fill: 'var(--text-muted)',
            fontSize: 10,
          }}
        />

        <Tooltip
          cursor={{ stroke: 'var(--border-strong)', strokeWidth: 1 }}
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null
            const value = Number(payload[0].value)
            return (
              <ChartTooltip
                title={shortDate(String(label))}
                rows={[
                  {
                    label: 'Water stress',
                    value: `${Math.round(value * 100)}%`,
                    color: 'var(--series-4)',
                  },
                ]}
                footer={
                  value < 0.05
                    ? 'Crop fully supplied'
                    : value < STRESS_ONSET
                      ? 'Mild — within tolerance'
                      : 'Transpiration restricted — yield at risk'
                }
              />
            )
          }}
        />

        <Area
          type="monotone"
          dataKey="stress"
          stroke="var(--series-4)"
          strokeWidth={LINE_WIDTH}
          fill="url(#stressFill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
