/**
 * Scatter-plot of all fields by geographic position, coloured by salinity risk.
 *
 * Zero external dependencies — pure SVG. Position is lat/lon projected linearly
 * onto the bounding box of the visible fields. This is adequate for a portfolio
 * spanning one or two districts; for multi-state coverage a proper projection
 * would be needed, but that's a future upgrade.
 *
 * Colour semantics follow the same four-level USDA scheme used everywhere else
 * in the app, so a field that looks red here is the same red as in the risk badge
 * and the gauge. Colour is never the sole channel: each dot also carries the
 * field name on hover.
 */
import type { FieldSummary } from '../../types/api'
import { riskMeta } from '../../lib/risk'

const W = 320
const H = 200
const PAD = 28   // space for labels at the edges

function project(
  lat: number, lon: number,
  minLat: number, maxLat: number, minLon: number, maxLon: number,
): [number, number] {
  const latRange = maxLat - minLat || 1
  const lonRange = maxLon - minLon || 1
  const x = PAD + ((lon - minLon) / lonRange) * (W - 2 * PAD)
  // SVG y-axis is inverted: higher latitude is higher on screen
  const y = H - PAD - ((lat - minLat) / latRange) * (H - 2 * PAD)
  return [x, y]
}

export default function RiskMap({ fields }: { fields: FieldSummary[] }) {
  if (!fields.length) return null

  const lats = fields.map((f) => f.lat)
  const lons = fields.map((f) => f.lon)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const minLon = Math.min(...lons)
  const maxLon = Math.max(...lons)

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        aria-label="Field risk map — dots show field positions coloured by salinity risk level"
        role="img"
        className="overflow-visible"
      >
        {/* faint grid lines to orient the eye */}
        {[0.25, 0.5, 0.75].map((t) => (
          <g key={t}>
            <line
              x1={PAD + t * (W - 2 * PAD)} y1={PAD}
              x2={PAD + t * (W - 2 * PAD)} y2={H - PAD}
              stroke="var(--border)" strokeWidth={0.5} strokeDasharray="2 4"
            />
            <line
              x1={PAD} y1={PAD + t * (H - 2 * PAD)}
              x2={W - PAD} y2={PAD + t * (H - 2 * PAD)}
              stroke="var(--border)" strokeWidth={0.5} strokeDasharray="2 4"
            />
          </g>
        ))}

        {/* axis labels */}
        <text x={PAD} y={H - 6} fontSize={9} fill="var(--text-muted)" textAnchor="middle">
          {minLon.toFixed(1)}°E
        </text>
        <text x={W - PAD} y={H - 6} fontSize={9} fill="var(--text-muted)" textAnchor="middle">
          {maxLon.toFixed(1)}°E
        </text>
        <text x={8} y={H - PAD} fontSize={9} fill="var(--text-muted)" textAnchor="middle" transform={`rotate(-90,8,${H - PAD})`}>
          {minLat.toFixed(1)}°N
        </text>
        <text x={8} y={PAD} fontSize={9} fill="var(--text-muted)" textAnchor="middle" transform={`rotate(-90,8,${PAD})`}>
          {maxLat.toFixed(1)}°N
        </text>

        {/* field dots */}
        {fields.map((field) => {
          const [x, y] = project(field.lat, field.lon, minLat, maxLat, minLon, maxLon)
          const meta = riskMeta(field.risk_level)
          return (
            <g key={field.field_id}>
              {/* outer ring for visibility on either theme */}
              <circle cx={x} cy={y} r={9} fill="var(--surface-1)" stroke={meta.colorVar} strokeWidth={1.5} />
              <circle cx={x} cy={y} r={6} fill={meta.colorVar} fillOpacity={0.9} />
              <title>{`${field.field_name} — ${field.salinity_ec.toFixed(1)} dS/m · ${meta.label}`}</title>
            </g>
          )
        })}

        {/* field labels — only shown if dots don't crowd each other */}
        {fields.map((field) => {
          const [x, y] = project(field.lat, field.lon, minLat, maxLat, minLon, maxLon)
          return (
            <text
              key={`lbl-${field.field_id}`}
              x={x}
              y={y - 12}
              fontSize={8}
              fill="var(--text-soft)"
              textAnchor="middle"
              className="pointer-events-none select-none"
            >
              {field.field_name.length > 10
                ? field.field_name.slice(0, 9) + '…'
                : field.field_name}
            </text>
          )
        })}
      </svg>

      {/* compact legend */}
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
        {(['low', 'moderate', 'high', 'critical'] as const).map((level) => {
          const m = riskMeta(level)
          return (
            <span key={level} className="flex items-center gap-1.5 text-[10px] text-ink-soft">
              <span className="size-2 rounded-full" style={{ background: m.colorVar }} aria-hidden />
              {m.label}
            </span>
          )
        })}
      </div>
    </div>
  )
}
