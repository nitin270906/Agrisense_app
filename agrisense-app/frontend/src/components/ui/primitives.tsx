/** Shared presentational primitives — warm Khet design system. */
import type { CSSProperties, ReactNode } from 'react'
import { AlertTriangle, Info, ShieldAlert, ShieldCheck } from 'lucide-react'
import { cx } from '../../lib/format'
import { riskMeta, severityMeta } from '../../lib/risk'
import type { RiskLevel, Severity } from '../../types/api'

/* ── Card ------------------------------------------------------------------ */

export function Card({
  children,
  className,
  padded = true,
  style,
  threeD = false,
  shimmer = false,
}: {
  children: ReactNode
  className?: string
  padded?: boolean
  style?: CSSProperties
  threeD?: boolean
  shimmer?: boolean
}) {
  return (
    <div
      className={cx(
        'rounded-2xl bg-surface-1',
        padded && 'p-4 sm:p-5',
        threeD && 'card-3d',
        shimmer && 'shimmer-effect',
        className
      )}
      style={{
        boxShadow: 'var(--shadow-card)',
        border: '1px solid var(--border)',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

/* ── CardHeader ------------------------------------------------------------ */

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

/* ── RiskBadge ------------------------------------------------------------- */

/** Risk pill: colour + icon + text — identity never rests on colour alone. */
export function RiskBadge({
  level,
  size = 'md',
  showRange = false,
}: {
  level: RiskLevel | string
  size?: 'sm' | 'md'
  showRange?: boolean
}) {
  const meta = riskMeta(level)
  const Icon =
    meta.level === 'low' ? ShieldCheck : meta.level === 'critical' ? ShieldAlert : AlertTriangle

  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full font-medium whitespace-nowrap',
        meta.chip,
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
      )}
    >
      <Icon size={size === 'sm' ? 11 : 13} aria-hidden />
      {meta.label}
      {showRange && <span className="opacity-70">· {meta.range}</span>}
    </span>
  )
}

/* ── SeverityBadge --------------------------------------------------------- */

export function SeverityBadge({ severity }: { severity: Severity | string }) {
  const meta = severityMeta(severity)
  const Icon = severity === 'info' ? Info : severity === 'critical' ? ShieldAlert : AlertTriangle
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
        meta.chip,
      )}
    >
      <Icon size={11} aria-hidden />
      {meta.label}
    </span>
  )
}

/* ── Skeleton -------------------------------------------------------------- */

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx('skeleton rounded-2xl', className)} />
}

/* ── ErrorState ------------------------------------------------------------ */

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-4 rounded-2xl p-10 text-center"
      style={{ boxShadow: 'var(--shadow-card)', border: '1px solid var(--border)', background: 'var(--surface-1)' }}
    >
      <div
        className="grid size-12 place-items-center rounded-full"
        style={{
          background: 'color-mix(in srgb, var(--status-serious) 12%, transparent)',
        }}
      >
        <AlertTriangle className="text-serious" size={22} aria-hidden />
      </div>
      <div>
        <p className="text-sm font-semibold text-ink">Something went wrong</p>
        <p className="mt-1.5 max-w-sm text-xs leading-relaxed text-ink-muted">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 rounded-xl px-5 py-2.5 text-xs font-semibold text-ink-soft transition hover:bg-surface-3 hover:text-ink active:scale-95"
          style={{ border: '1px solid var(--border-strong)' }}
        >
          Try again
        </button>
      )}
    </div>
  )
}

/* ── EmptyState ------------------------------------------------------------ */

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 p-10 text-center">
      <p className="text-sm font-medium text-ink-soft">{title}</p>
      {hint && <p className="text-xs text-ink-muted">{hint}</p>}
    </div>
  )
}

/* ── SimulatedBadge -------------------------------------------------------- */

/**
 * Persistent simulated-data disclosure.
 *
 * Judges must never need to ask whether this is real data. The badge is
 * unmissable and carries a tooltip with the scientific basis.
 */
export function SimulatedBadge({ compact = false }: { compact?: boolean }) {
  return (
    <span
      title="Models trained on physics-simulated data derived from FAO-56 and Maas-Hoffman relationships — not field measurements."
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium"
      style={{
        background: 'var(--accent-soft)',
        color: 'var(--accent)',
        border: '1px solid rgba(212,175,55,0.20)',
      }}
    >
      <Info size={11} aria-hidden />
      {compact ? 'Simulated' : 'Simulated data · physics-calibrated'}
    </span>
  )
}
