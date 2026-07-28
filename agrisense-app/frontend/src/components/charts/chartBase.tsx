/**
 * Shared chart chrome: recessive axes, hairline grid, and a single tooltip.
 *
 * Grid and axes are deliberately quiet — they orient the eye without competing
 * with the data. Every chart in the app pulls its axis styling from here so the
 * set reads as one system rather than four separately-tuned charts.
 */
import { useState } from 'react'
import type { ReactNode } from 'react'

export const AXIS = {
  stroke: 'var(--grid)',
  tick: { fill: 'var(--text-muted)', fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: 'var(--grid)' },
} as const

export const GRID = {
  stroke: 'var(--grid)',
  strokeDasharray: '2 4',
  vertical: false,
} as const

/** Line weight per the mark spec: thin, so data reads before decoration. */
export const LINE_WIDTH = 2
export const DOT_RADIUS = 4

export interface TooltipRow {
  label: string
  value: string
  color?: string
}

export function ChartTooltip({
  title,
  rows,
  footer,
}: {
  title: string
  rows: TooltipRow[]
  footer?: ReactNode
}) {
  return (
    <div className="rounded-lg border border-edge-strong bg-surface-2 px-3 py-2 shadow-lg">
      <p className="mb-1.5 text-[11px] font-medium text-ink-muted">{title}</p>
      <div className="space-y-1">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center gap-2.5 text-xs">
            {row.color && (
              <span
                className="size-2 shrink-0 rounded-full"
                style={{ background: row.color }}
                aria-hidden
              />
            )}
            <span className="text-ink-soft">{row.label}</span>
            <span className="tabular ml-auto font-medium text-ink">{row.value}</span>
          </div>
        ))}
      </div>
      {footer && <div className="mt-1.5 border-t border-edge pt-1.5 text-[11px] text-ink-muted">{footer}</div>}
    </div>
  )
}

/** Toggle between a chart and a plain data table (CVD + screen-reader safe). */
export function ChartWithTable<R extends Record<string, unknown>>({
  data,
  columns,
  children,
}: {
  data: R[]
  columns: { key: keyof R; label: string }[]
  children: ReactNode
}) {
  const [showTable, setShowTable] = useState(false)

  const downloadCsv = () => {
    const header = columns.map((c) => c.label).join(',')
    const rows = data.map((row) =>
      columns.map((c) => String(row[c.key] ?? '')).join(',')
    )
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'chart-data.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="mb-2 flex justify-end gap-2">
        <button
          onClick={() => setShowTable((v) => !v)}
          className="rounded px-2 py-0.5 text-[11px] font-medium text-ink-muted transition hover:bg-surface-2 hover:text-ink"
          aria-label={showTable ? 'Show chart' : 'Show data table'}
        >
          {showTable ? 'Chart' : 'Table'}
        </button>
        {showTable && (
          <button
            onClick={downloadCsv}
            className="rounded px-2 py-0.5 text-[11px] font-medium text-ink-muted transition hover:bg-surface-2 hover:text-ink"
          >
            CSV
          </button>
        )}
      </div>

      {showTable ? (
        <div className="overflow-x-auto rounded-lg border border-edge">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-edge bg-surface-2">
                {columns.map((c) => (
                  <th
                    key={String(c.key)}
                    className="px-3 py-2 text-left font-medium text-ink-muted"
                  >
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={i} className="border-b border-edge last:border-0 hover:bg-surface-2">
                  {columns.map((c) => (
                    <td key={String(c.key)} className="px-3 py-1.5 tabular text-ink">
                      {String(row[c.key] ?? '—')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        children
      )}
    </div>
  )
}

/** Legend chip: a coloured mark beside text ink, never coloured text. */
export function LegendRow({
  items,
}: {
  items: { label: string; color: string; dashed?: boolean }[]
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {items.map((item) => (
        <span key={item.label} className="flex items-center gap-1.5 text-[11px] text-ink-soft">
          <span
            className="inline-block h-0.5 w-4 rounded-full"
            style={
              item.dashed
                ? {
                    backgroundImage: `repeating-linear-gradient(90deg, ${item.color} 0 4px, transparent 4px 7px)`,
                  }
                : { background: item.color }
            }
            aria-hidden
          />
          {item.label}
        </span>
      ))}
    </div>
  )
}
