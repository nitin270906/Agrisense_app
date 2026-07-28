/** Display formatting helpers. */

export const cx = (...parts: (string | false | null | undefined)[]) =>
  parts.filter(Boolean).join(' ')

export const ec = (value: number) => `${value.toFixed(1)} dS/m`
export const mm = (value: number) => `${Math.round(value)} mm`
export const pct = (value: number, digits = 0) => `${(value * 100).toFixed(digits)}%`
export const ha = (value: number) => `${value.toFixed(1)} ha`

export const signed = (value: number, digits = 2) =>
  `${value > 0 ? '+' : ''}${value.toFixed(digits)}`

export const shortDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

export const longDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })

export const titleCase = (value: string) =>
  value
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')

export const relativeTime = (iso: string) => {
  const diffMs = Date.now() - new Date(iso).getTime()
  const minutes = Math.round(diffMs / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}
