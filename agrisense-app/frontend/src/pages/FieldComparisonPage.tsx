import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'
import { Scale, Check, Plus, Trash2 } from 'lucide-react'
import { useDashboard } from '../api/hooks'
import { Card, CardHeader, RiskBadge, Skeleton, ErrorState } from '../components/ui/primitives'
import DataExport from '../components/DataExport'
import { AXIS, GRID, ChartTooltip } from '../components/charts/chartBase'
import { titleCase } from '../lib/format'
import { riskMeta, healthColor } from '../lib/risk'

export default function FieldComparisonPage() {
  const { data: dashboard, isLoading, isError, error, refetch } = useDashboard()
  const [selectedFieldIds, setSelectedFieldIds] = useState<number[]>([1, 2])

  const fields = dashboard?.fields ?? []

  const toggleField = (id: number) => {
    setSelectedFieldIds((prev) => {
      if (prev.includes(id)) {
        if (prev.length <= 1) return prev // keep at least 1
        return prev.filter((item) => item !== id)
      } else {
        if (prev.length >= 4) return prev // max 4 fields
        return [...prev, id]
      }
    })
  }

  const selectedFields = useMemo(() => {
    return fields.filter((f) => selectedFieldIds.includes(f.field_id))
  }, [fields, selectedFieldIds])

  const comparisonChartData = useMemo(() => {
    return selectedFields.map((f) => ({
      name: f.field_name,
      salinity: f.salinity_ec,
      health: f.health_score,
      irrigation: f.irrigation_need_mm,
      riskLevel: f.risk_level,
    }))
  }, [selectedFields])

  if (isError) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : 'Failed to load comparison data'}
        onRetry={() => refetch()}
      />
    )
  }

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* --- Header -------------------------------------------------------- */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Scale size={20} className="text-accent" />
            <h1 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
              Field Comparison Tool
            </h1>
          </div>
          <p className="mt-1 text-xs text-ink-muted sm:text-sm">
            Side-by-side metric comparison across up to 4 farm fields.
          </p>
        </div>

        {selectedFields.length > 0 && (
          <DataExport
            data={selectedFields.map((f) => ({
              field_id: f.field_id,
              name: f.field_name,
              crop: f.crop,
              area_ha: f.area_ha,
              salinity_ec: f.salinity_ec,
              salinity_delta_30d: f.salinity_delta,
              health_score: f.health_score,
              irrigation_need_mm: f.irrigation_need_mm,
              risk_level: f.risk_level,
            }))}
            filename="field-comparison"
            label="Export Comparison"
          />
        )}
      </div>

      {isLoading ? (
        <Skeleton className="h-64" />
      ) : (
        <>
          {/* --- Field Selector Pills --------------------------------------- */}
          <Card>
            <CardHeader
              title="Select fields to compare (Max 4)"
              subtitle={`Currently comparing ${selectedFields.length} field${selectedFields.length > 1 ? 's' : ''}`}
            />
            <div className="flex flex-wrap gap-2 pt-1">
              {fields.map((f) => {
                const isSelected = selectedFieldIds.includes(f.field_id)
                const meta = riskMeta(f.risk_level)
                return (
                  <button
                    key={f.field_id}
                    onClick={() => toggleField(f.field_id)}
                    className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold transition"
                    style={
                      isSelected
                        ? {
                            background: 'var(--accent-soft)',
                            color: 'var(--accent)',
                            border: '1.5px solid var(--accent)',
                          }
                        : {
                            background: 'var(--surface-2)',
                            color: 'var(--text-secondary)',
                            border: '1px solid var(--border)',
                          }
                    }
                  >
                    {isSelected ? <Check size={13} /> : <Plus size={13} />}
                    <span>{f.field_name}</span>
                    <span
                      className="size-2 rounded-full"
                      style={{ background: meta.colorVar }}
                    />
                  </button>
                )
              })}
            </div>
          </Card>

          {/* --- Comparison Visualizations ---------------------------------- */}
          <div className="grid gap-4 lg:grid-cols-3">
            {/* Salinity Bar Chart */}
            <Card>
              <CardHeader title="Soil Salinity (ECe)" subtitle="dS/m (Lower is better)" />
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={comparisonChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid {...GRID} />
                  <XAxis dataKey="name" {...AXIS} tick={{ fontSize: 10 }} />
                  <YAxis {...AXIS} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <ChartTooltip
                          title={d.name}
                          rows={[{ label: 'Salinity', value: `${d.salinity.toFixed(1)} dS/m`, color: riskMeta(d.riskLevel).colorVar }]}
                        />
                      )
                    }}
                  />
                  <Bar dataKey="salinity" radius={[6, 6, 0, 0]}>
                    {comparisonChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={riskMeta(entry.riskLevel).colorVar} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>

            {/* Health Score Bar Chart */}
            <Card>
              <CardHeader title="Crop Health Score" subtitle="/ 100 (Higher is better)" />
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={comparisonChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid {...GRID} />
                  <XAxis dataKey="name" {...AXIS} tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 100]} {...AXIS} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <ChartTooltip
                          title={d.name}
                          rows={[{ label: 'Health Score', value: `${d.health.toFixed(0)} / 100`, color: healthColor(d.health) }]}
                        />
                      )
                    }}
                  />
                  <Bar dataKey="health" radius={[6, 6, 0, 0]}>
                    {comparisonChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={healthColor(entry.health)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>

            {/* Irrigation Need Bar Chart */}
            <Card>
              <CardHeader title="Irrigation Requirement" subtitle="mm water needed" />
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={comparisonChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid {...GRID} />
                  <XAxis dataKey="name" {...AXIS} tick={{ fontSize: 10 }} />
                  <YAxis {...AXIS} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <ChartTooltip
                          title={d.name}
                          rows={[{ label: 'Irrigation', value: `${Math.round(d.irrigation)} mm`, color: 'var(--series-1)' }]}
                        />
                      )
                    }}
                  />
                  <Bar dataKey="irrigation" fill="var(--series-1)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* --- Detailed Side-by-Side Cards Table -------------------------- */}
          <Card padded={false} className="overflow-hidden p-4 sm:p-5">
            <CardHeader
              title="Side-by-Side Breakdown"
              subtitle="Comprehensive field metric summary"
            />
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-edge bg-surface-2">
                    <th className="p-3 font-semibold text-ink-muted">Metric</th>
                    {selectedFields.map((f) => (
                      <th key={f.field_id} className="p-3 font-semibold text-ink">
                        <div className="flex items-center justify-between">
                          <span>{f.field_name}</span>
                          {selectedFields.length > 1 && (
                            <button
                              onClick={() => toggleField(f.field_id)}
                              className="text-ink-muted hover:text-[#B81C1C]"
                              title="Remove from comparison"
                            >
                              <Trash2 size={12} />
                            </button>
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  <tr>
                    <td className="p-3 font-medium text-ink-muted">Crop</td>
                    {selectedFields.map((f) => (
                      <td key={f.field_id} className="p-3 text-ink font-semibold">
                        {titleCase(f.crop)}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-ink-muted">Risk Status</td>
                    {selectedFields.map((f) => (
                      <td key={f.field_id} className="p-3">
                        <RiskBadge level={f.risk_level} size="sm" />
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-ink-muted">Soil Salinity</td>
                    {selectedFields.map((f) => (
                      <td key={f.field_id} className="p-3 tabular font-bold text-ink">
                        {f.salinity_ec.toFixed(1)} <span className="font-normal text-ink-muted">dS/m</span>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-ink-muted">30-Day Trend</td>
                    {selectedFields.map((f) => (
                      <td
                        key={f.field_id}
                        className={`p-3 tabular font-semibold ${
                          f.salinity_delta > 0 ? 'text-serious' : 'text-good'
                        }`}
                      >
                        {f.salinity_delta > 0 ? '+' : ''}
                        {f.salinity_delta.toFixed(2)} dS/m
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-ink-muted">Health Score</td>
                    {selectedFields.map((f) => (
                      <td
                        key={f.field_id}
                        className="p-3 tabular font-bold"
                        style={{ color: healthColor(f.health_score) }}
                      >
                        {f.health_score.toFixed(0)} / 100
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-ink-muted">Irrigation Need</td>
                    {selectedFields.map((f) => (
                      <td key={f.field_id} className="p-3 tabular text-ink font-semibold">
                        {Math.round(f.irrigation_need_mm)} mm
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-ink-muted">Priority Action</td>
                    {selectedFields.map((f) => (
                      <td key={f.field_id} className="p-3 text-ink-soft text-[11px]">
                        {f.top_action ?? 'Optimal conditions'}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </motion.div>
  )
}
