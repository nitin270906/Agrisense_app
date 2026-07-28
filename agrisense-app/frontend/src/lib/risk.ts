/**
 * Risk semantics, shared by every component that renders a risk state.
 *
 * Bands follow the USDA soil salinity classes. Each carries a colour token, an
 * icon name and a text label, because colour alone is never sufficient: the
 * palette's status scale puts warning and serious below 3:1 contrast on a light
 * surface by design, and the icon + label pairing is the mitigation.
 */
import type { RiskLevel, Severity } from '../types/api'

export interface RiskMeta {
  level: RiskLevel
  label: string
  /** USDA class description, shown as supporting text. */
  description: string
  /** CSS custom property holding the status colour. */
  colorVar: string
  /** Tailwind text colour utility. */
  text: string
  /** Tint + ring for chips and cards. */
  chip: string
  range: string
}

export const RISK_META: Record<RiskLevel, RiskMeta> = {
  low: {
    level: 'low',
    label: 'Low',
    description: 'Non-saline — no yield impact expected',
    colorVar: 'var(--status-good)',
    text: 'text-good',
    chip: 'bg-[color-mix(in_srgb,var(--status-good)_16%,transparent)] text-good ring-1 ring-[color-mix(in_srgb,var(--status-good)_38%,transparent)]',
    range: '< 2 dS/m',
  },
  moderate: {
    level: 'moderate',
    label: 'Moderate',
    description: 'Slightly saline — sensitive crops affected',
    colorVar: 'var(--status-warning)',
    text: 'text-warning',
    chip: 'bg-[color-mix(in_srgb,var(--status-warning)_16%,transparent)] text-warning ring-1 ring-[color-mix(in_srgb,var(--status-warning)_38%,transparent)]',
    range: '2 – 4 dS/m',
  },
  high: {
    level: 'high',
    label: 'High',
    description: 'Moderately saline — most crops lose yield',
    colorVar: 'var(--status-serious)',
    text: 'text-serious',
    chip: 'bg-[color-mix(in_srgb,var(--status-serious)_16%,transparent)] text-serious ring-1 ring-[color-mix(in_srgb,var(--status-serious)_38%,transparent)]',
    range: '4 – 8 dS/m',
  },
  critical: {
    level: 'critical',
    label: 'Critical',
    description: 'Strongly saline — only tolerant crops survive',
    colorVar: 'var(--status-critical)',
    text: 'text-critical',
    chip: 'bg-[color-mix(in_srgb,var(--status-critical)_18%,transparent)] text-critical ring-1 ring-[color-mix(in_srgb,var(--status-critical)_42%,transparent)]',
    range: '> 8 dS/m',
  },
}

export const riskFromEc = (ec: number): RiskLevel =>
  ec < 2 ? 'low' : ec < 4 ? 'moderate' : ec < 8 ? 'high' : 'critical'

export const riskMeta = (level: RiskLevel | string): RiskMeta =>
  RISK_META[(level as RiskLevel) in RISK_META ? (level as RiskLevel) : 'low']

/** Recommendation severity shares the status scale so urgency reads consistently. */
export const SEVERITY_META: Record<Severity, { label: string; colorVar: string; chip: string }> = {
  info: {
    label: 'Info',
    colorVar: 'var(--status-good)',
    chip: 'bg-[color-mix(in_srgb,var(--status-good)_14%,transparent)] text-good ring-1 ring-[color-mix(in_srgb,var(--status-good)_34%,transparent)]',
  },
  warning: {
    label: 'Watch',
    colorVar: 'var(--status-warning)',
    chip: 'bg-[color-mix(in_srgb,var(--status-warning)_14%,transparent)] text-warning ring-1 ring-[color-mix(in_srgb,var(--status-warning)_34%,transparent)]',
  },
  urgent: {
    label: 'Urgent',
    colorVar: 'var(--status-serious)',
    chip: 'bg-[color-mix(in_srgb,var(--status-serious)_14%,transparent)] text-serious ring-1 ring-[color-mix(in_srgb,var(--status-serious)_34%,transparent)]',
  },
  critical: {
    label: 'Critical',
    colorVar: 'var(--status-critical)',
    chip: 'bg-[color-mix(in_srgb,var(--status-critical)_16%,transparent)] text-critical ring-1 ring-[color-mix(in_srgb,var(--status-critical)_38%,transparent)]',
  },
}

export const severityMeta = (severity: Severity | string) =>
  SEVERITY_META[(severity as Severity) in SEVERITY_META ? (severity as Severity) : 'info']

/** Health score bands mirror the risk scale so the two read together. */
export const healthColor = (score: number): string =>
  score >= 85
    ? 'var(--status-good)'
    : score >= 65
      ? 'var(--status-warning)'
      : score >= 40
        ? 'var(--status-serious)'
        : 'var(--status-critical)'

export const stressColor = (index: number): string =>
  index < 0.15
    ? 'var(--status-good)'
    : index < 0.35
      ? 'var(--status-warning)'
      : index < 0.6
        ? 'var(--status-serious)'
        : 'var(--status-critical)'
