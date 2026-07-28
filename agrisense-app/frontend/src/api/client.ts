/**
 * Thin typed fetch wrapper.
 *
 * Same-origin `/api` in both dev (Vite proxy) and production (FastAPI serves the
 * built bundle), so there is no base-URL configuration to get wrong between
 * environments.
 */
import type {
  CropProfile,
  DashboardSummary,
  Farm,
  Field,
  ForecastPoint,
  Health,
  ModelInfo,
  Prediction,
  Reading,
  Recommendation,
  SimulationRequest,
  SimulationResult,
  Weather,
} from '../types/api'

const BASE = '/api'

export class ApiError extends Error {
  // Declared explicitly rather than as constructor parameter properties, which
  // this project's `erasableSyntaxOnly` setting disallows.
  readonly status: number
  readonly path: string

  constructor(message: string, status: number, path: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.path = path
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })

  if (!response.ok) {
    // Surface the server's `detail` when present — it is far more actionable
    // than a bare status code.
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = body?.detail ?? detail
    } catch {
      /* non-JSON error body; keep the status text */
    }
    throw new ApiError(detail, response.status, path)
  }

  return response.json() as Promise<T>
}

const qs = (params: Record<string, string | number | boolean | undefined>) => {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) search.set(key, String(value))
  }
  const out = search.toString()
  return out ? `?${out}` : ''
}

export const api = {
  health: () => request<Health>('/health'),
  modelInfo: () => request<ModelInfo>('/model/info'),
  crops: () => request<CropProfile[]>('/meta/crops'),

  farms: () => request<Farm[]>('/farms'),
  fields: (farmId?: number) => request<Field[]>(`/fields${qs({ farm_id: farmId })}`),
  field: (id: number) => request<Field>(`/fields/${id}`),

  readings: (id: number, days = 90) =>
    request<Reading[]>(`/fields/${id}/readings${qs({ days })}`),

  weather: (id: number, refresh = false) =>
    request<Weather>(`/fields/${id}/weather${qs({ refresh })}`),

  latestPrediction: (id: number) =>
    request<Prediction>(`/fields/${id}/predictions/latest`),

  predict: (id: number) =>
    request<Prediction>(`/fields/${id}/predict`, { method: 'POST' }),

  forecast: (id: number, days = 30) =>
    request<ForecastPoint[]>(`/fields/${id}/forecast${qs({ days })}`),

  recommendations: (id: number) =>
    request<Recommendation[]>(`/fields/${id}/recommendations`),

  simulate: (id: number, payload: SimulationRequest) =>
    request<SimulationResult>(`/fields/${id}/simulate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  dashboard: (farmId?: number) =>
    request<DashboardSummary>(`/dashboard/summary${qs({ farm_id: farmId })}`),

  alerts: (limit = 20) => request<Recommendation[]>(`/dashboard/alerts${qs({ limit })}`),
}
