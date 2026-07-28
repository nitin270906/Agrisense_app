/**
 * Radial gauge for a single bounded score.
 *
 * A hero figure, not a chart: one number is the whole payload, so the arc exists
 * to give it position on a scale rather than to be read precisely. The numeral
 * carries the value; the arc carries the context.
 */
export default function Gauge({
  value,
  max = 100,
  label,
  suffix = '',
  color,
  size = 132,
}: {
  value: number
  max?: number
  label: string
  suffix?: string
  color: string
  size?: number
}) {
  const stroke = 10
  const radius = (size - stroke) / 2
  const circumference = Math.PI * radius // semicircle
  const fraction = Math.max(0, Math.min(1, value / max))
  const height = size / 2 + stroke

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={height} viewBox={`0 0 ${size} ${height}`} role="img"
           aria-label={`${label}: ${value}${suffix}`}>
        {/* track */}
        <path
          d={`M ${stroke / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - stroke / 2} ${size / 2}`}
          fill="none"
          stroke="var(--surface-3)"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        {/* value */}
        <path
          d={`M ${stroke / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - stroke / 2} ${size / 2}`}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference * fraction} ${circumference}`}
          style={{ transition: 'stroke-dasharray 700ms cubic-bezier(0.22, 1, 0.36, 1)' }}
        />
        <text
          x={size / 2}
          y={size / 2 - 6}
          textAnchor="middle"
          fill="var(--text-primary)"
          fontSize={size * 0.21}
          fontWeight={600}
        >
          {Math.round(value)}
          <tspan fontSize={size * 0.11} fill="var(--text-muted)">
            {suffix}
          </tspan>
        </text>
      </svg>
      <p className="-mt-1 text-xs text-ink-muted">{label}</p>
    </div>
  )
}
