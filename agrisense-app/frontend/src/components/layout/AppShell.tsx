/**
 * Application chrome: sidebar on desktop, bottom navigation on mobile.
 *
 * Warm light default. Sidebar: clean white, gold active state, premium brand.
 * Mobile: bottom nav for one-handed reach on phones in the field.
 */
import { type ReactNode, useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Activity, BarChart2, Cpu, LayoutDashboard, Moon, RotateCw, Sprout, Sun } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { cx } from '../../lib/format'
import { SimulatedBadge } from '../ui/primitives'
import { useHealth } from '../../api/hooks'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/compare', label: 'Compare', icon: BarChart2, end: false },
  { to: '/simulator', label: 'Simulator', icon: Activity, end: false },
  { to: '/model', label: 'Model', icon: Cpu, end: false },
]

function useTheme() {
  const [theme, setTheme] = useState<'dark' | 'light'>(
    () => (localStorage.getItem('theme') as 'dark' | 'light') ?? 'light',
  )

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  return { theme, toggle: () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')) }
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div
        className="grid size-9 shrink-0 place-items-center rounded-xl"
        style={{
          background: 'var(--accent-soft)',
          border: '1.5px solid rgba(212,175,55,0.25)',
        }}
      >
        <Sprout size={17} style={{ color: 'var(--accent)' }} aria-hidden />
      </div>
      <div className="min-w-0">
        <p className="truncate text-[13px] font-semibold tracking-tight text-ink">AGRISENSE</p>
        <p className="truncate text-[11px] font-medium" style={{ color: 'var(--accent)' }}>
          AI Salinity Intelligence
        </p>
      </div>
    </div>
  )
}

export default function AppShell({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme()
  const { data: health } = useHealth()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await queryClient.invalidateQueries()
    } catch (error) {
      console.error('Failed to refresh data:', error)
    } finally {
      setTimeout(() => setIsRefreshing(false), 500)
    }
  }

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [location.pathname])

  return (
    <div className="min-h-full bg-surface-0">

      {/* ── Desktop sidebar ──────────────────────────────────────────────── */}
      <aside
        className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col p-5 lg:flex"
        style={{
          background: 'var(--surface-1)',
          borderRight: '1px solid var(--border)',
        }}
      >
        <Brand />

        <nav className="mt-8 flex flex-col gap-0.5">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cx(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-all duration-150 hover:scale-105 active:scale-95',
                  isActive
                    ? 'font-semibold'
                    : 'font-medium text-ink-soft hover:bg-surface-2 hover:text-ink',
                )
              }
              style={({ isActive }) =>
                isActive
                  ? {
                      background: 'var(--accent-soft)',
                      color: 'var(--accent)',
                    }
                  : {}
              }
            >
              <Icon size={16} aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto space-y-2.5">
          <SimulatedBadge />

          {/* Model status pill */}
          <div
            className="flex items-center justify-between rounded-lg px-3 py-2.5"
            style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
          >
            <span className="text-[11px] font-medium text-ink-muted">
              {health?.model_loaded ? `Model v${health.model_version}` : 'Physics mode'}
            </span>
            <span
              className="size-1.5 rounded-full"
              style={{
                background: health?.model_loaded
                  ? 'var(--status-good)'
                  : 'var(--status-warning)',
              }}
              aria-hidden
            />
          </div>

          {/* Refresh data button */}
          <button
            onClick={handleRefresh}
            title="Reload application data"
            className="btn-3d flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium text-ink-soft transition hover:bg-surface-2 hover:text-ink"
          >
            <RotateCw size={15} className={cx(isRefreshing && 'animate-spin')} aria-hidden />
            {isRefreshing ? 'Refreshing...' : 'Reload data'}
          </button>

          {/* Theme toggle */}
          <button
            onClick={toggle}
            className="btn-3d flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium text-ink-soft transition hover:bg-surface-2 hover:text-ink"
          >
            {theme === 'dark' ? <Sun size={15} aria-hidden /> : <Moon size={15} aria-hidden />}
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </button>

          {/* Hackathon branding */}
          <p className="pt-2 text-center text-[10px] leading-relaxed text-ink-muted">
            Built for the UNDP Climate Hackathon
          </p>
        </div>
      </aside>

      {/* ── Mobile top bar ───────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-30 flex items-center justify-between px-4 py-3 backdrop-blur lg:hidden"
        style={{
          background: 'var(--surface-glass)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <Brand />
        <div className="flex items-center gap-2">
          <SimulatedBadge compact />
          <button
            onClick={handleRefresh}
            aria-label="Reload application data"
            title="Reload application data"
            className="grid size-8 place-items-center rounded-lg text-ink-soft transition hover:bg-surface-3"
          >
            <RotateCw size={15} className={cx(isRefreshing && 'animate-spin')} aria-hidden />
          </button>
          <button
            onClick={toggle}
            aria-label="Toggle colour theme"
            className="grid size-8 place-items-center rounded-lg text-ink-soft transition hover:bg-surface-3"
          >
            {theme === 'dark' ? <Sun size={15} aria-hidden /> : <Moon size={15} aria-hidden />}
          </button>
        </div>
      </header>

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <main className="pb-24 lg:ml-64 lg:pb-10">
        <div className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 sm:py-8">
          {children}
        </div>
      </main>

      {/* ── Mobile bottom navigation ─────────────────────────────────────── */}
      <nav
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 backdrop-blur lg:hidden"
        style={{
          background: 'var(--surface-glass)',
          borderTop: '1px solid var(--border)',
        }}
      >
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cx(
                'flex flex-col items-center gap-1 py-3 text-[11px] font-medium transition',
                isActive ? 'text-ink' : 'text-ink-muted',
              )
            }
            style={({ isActive }) =>
              isActive ? { color: 'var(--accent)' } : {}
            }
          >
            <Icon size={18} aria-hidden />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
