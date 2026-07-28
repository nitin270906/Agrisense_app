import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { Clock, RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import { keys, useDashboard, useFarms } from '../api/hooks'
import AlertsPanel from '../components/dashboard/AlertsPanel'
import FieldCard from '../components/dashboard/FieldCard'
import KpiRow from '../components/dashboard/KpiRow'
import RiskBreakdown from '../components/dashboard/RiskBreakdown'
import RiskMap from '../components/dashboard/RiskMap'
import { Card, CardHeader, ErrorState, Skeleton } from '../components/ui/primitives'
import { cx } from '../lib/format'

export default function DashboardPage() {
  const [farmId, setFarmId] = useState<number | undefined>(undefined)
  const { data: farms } = useFarms()
  const { data, isLoading, isError, error, refetch, isFetching } = useDashboard(farmId)
  const { data: alerts } = useQuery({
    queryKey: keys.alerts,
    queryFn: () => api.alerts(20),
    enabled: !!data,
  })

  return (
    <motion.div
      className="space-y-5"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* --- header ---------------------------------------------------- */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
            Salinity & crop stress
          </h1>
          <p className="mt-1 text-xs text-ink-muted sm:text-sm">
            30-day forecast across {data?.total_fields ?? '—'} fields ·{' '}
            {data?.total_area_ha?.toFixed(0) ?? '—'} ha monitored
          </p>
          {data && !isFetching && (
            <p className="mt-1.5 flex items-center gap-1.5 text-[11px] text-ink-muted">
              <Clock size={10} aria-hidden />
              Updated just now
              <span className="ml-1 inline-block size-1.5 rounded-full bg-good" aria-hidden />
              <span className="text-good">Live</span>
            </p>
          )}
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold text-ink-soft transition hover:bg-surface-2 hover:text-ink disabled:opacity-50"
          style={{ border: '1px solid var(--border-strong)' }}
        >
          <RefreshCw size={13} className={cx(isFetching && 'animate-spin')} aria-hidden />
          {isFetching ? 'Running models…' : 'Re-run forecast'}
        </button>
      </div>

      {/* --- farm filter ----------------------------------------------- */}
      {!!farms?.length && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFarmId(undefined)}
            className={cx(
              'rounded-full px-3 py-1.5 text-xs font-semibold transition',
              farmId === undefined
                ? ''
                : 'text-ink-soft hover:bg-surface-2',
            )}
            style={
              farmId === undefined
                ? { background: 'var(--accent-soft)', color: 'var(--accent)', border: '1px solid rgba(212,175,55,0.25)' }
                : { border: '1px solid var(--border)' }
            }
          >
            All farms
          </button>
          {farms.map((farm) => (
            <button
              key={farm.id}
              onClick={() => setFarmId(farm.id)}
              className={cx(
                'rounded-full px-3 py-1.5 text-xs font-semibold transition',
                farmId === farm.id ? '' : 'text-ink-soft hover:bg-surface-2',
              )}
              style={
                farmId === farm.id
                  ? { background: 'var(--accent-soft)', color: 'var(--accent)', border: '1px solid rgba(212,175,55,0.25)' }
                  : { border: '1px solid var(--border)' }
              }
            >
              {farm.name}
              <span className="ml-1.5 opacity-60">{farm.field_count}</span>
            </button>
          ))}
        </div>
      )}

      {isError ? (
        <ErrorState
          message={error instanceof Error ? error.message : 'Failed to load dashboard'}
          onRetry={() => refetch()}
        />
      ) : (
        <>
          <KpiRow data={data} loading={isLoading} />

          <div className="grid gap-4 lg:grid-cols-3">
            {/* --- field grid ------------------------------------------ */}
            <div className="lg:col-span-2">
              <Card padded={false} className="p-4 sm:p-5">
                <CardHeader
                  title="Fields"
                  subtitle="Ordered by salinity — the field needing attention is first"
                />
                {isLoading ? (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <Skeleton key={i} className="h-[220px]" />
                    ))}
                  </div>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {data?.fields.map((field, i) => (
                      <FieldCard key={field.field_id} field={field} index={i} />
                    ))}
                  </div>
                )}
              </Card>
            </div>

            {/* --- side rail ------------------------------------------- */}
            <div className="space-y-4">
              <Card>
                <CardHeader
                  title="Risk distribution"
                  subtitle="USDA soil salinity classes"
                />
                {isLoading || !data ? (
                  <Skeleton className="h-24" />
                ) : (
                  <RiskBreakdown
                    breakdown={data.risk_breakdown}
                    total={data.total_fields}
                  />
                )}
              </Card>

              <Card>
                <CardHeader
                  title="Field locations"
                  subtitle="Dot colour = salinity risk"
                />
                {isLoading || !data ? (
                  <Skeleton className="h-48" />
                ) : (
                  <RiskMap fields={data.fields} />
                )}
              </Card>

              <Card>
                <CardHeader
                  title="Priority actions"
                  subtitle="Across all fields, most urgent first"
                />
                {isLoading ? (
                  <Skeleton className="h-40" />
                ) : (
                  <AlertsPanel alerts={alerts ?? []} fields={data?.fields ?? []} />
                )}
              </Card>
            </div>
          </div>
        </>
      )}
    </motion.div>
  )
}
