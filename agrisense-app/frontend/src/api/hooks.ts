/** TanStack Query hooks. Server state lives here; there is no client store. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { SimulationRequest } from '../types/api'

/** Dashboard runs inference for every field, so it is the slow one. */
const SLOW = 120_000
const NORMAL = 60_000

export const keys = {
  health: ['health'] as const,
  modelInfo: ['model-info'] as const,
  crops: ['crops'] as const,
  farms: ['farms'] as const,
  fields: (farmId?: number) => ['fields', farmId ?? 'all'] as const,
  field: (id: number) => ['field', id] as const,
  readings: (id: number, days: number) => ['readings', id, days] as const,
  weather: (id: number) => ['weather', id] as const,
  prediction: (id: number) => ['prediction', id] as const,
  forecast: (id: number, days: number) => ['forecast', id, days] as const,
  recommendations: (id: number) => ['recommendations', id] as const,
  dashboard: (farmId?: number) => ['dashboard', farmId ?? 'all'] as const,
  alerts: ['alerts'] as const,
}

export const useHealth = () =>
  useQuery({ queryKey: keys.health, queryFn: api.health, staleTime: NORMAL })

export const useModelInfo = () =>
  useQuery({ queryKey: keys.modelInfo, queryFn: api.modelInfo, staleTime: Infinity })

export const useCrops = () =>
  useQuery({ queryKey: keys.crops, queryFn: api.crops, staleTime: Infinity })

export const useFarms = () =>
  useQuery({ queryKey: keys.farms, queryFn: api.farms, staleTime: SLOW })

export const useFields = (farmId?: number) =>
  useQuery({ queryKey: keys.fields(farmId), queryFn: () => api.fields(farmId), staleTime: SLOW })

export const useField = (id: number) =>
  useQuery({ queryKey: keys.field(id), queryFn: () => api.field(id), enabled: id > 0 })

export const useReadings = (id: number, days = 90) =>
  useQuery({
    queryKey: keys.readings(id, days),
    queryFn: () => api.readings(id, days),
    enabled: id > 0,
    staleTime: SLOW,
  })

export const useWeather = (id: number) =>
  useQuery({
    queryKey: keys.weather(id),
    queryFn: () => api.weather(id),
    enabled: id > 0,
    staleTime: SLOW,
  })

export const usePrediction = (id: number) =>
  useQuery({
    queryKey: keys.prediction(id),
    queryFn: () => api.latestPrediction(id),
    enabled: id > 0,
    staleTime: NORMAL,
  })

export const useForecast = (id: number, days = 30) =>
  useQuery({
    queryKey: keys.forecast(id, days),
    queryFn: () => api.forecast(id, days),
    enabled: id > 0,
    staleTime: SLOW,
  })

export const useRecommendations = (id: number) =>
  useQuery({
    queryKey: keys.recommendations(id),
    queryFn: () => api.recommendations(id),
    enabled: id > 0,
    staleTime: NORMAL,
  })

export const useDashboard = (farmId?: number) =>
  useQuery({
    queryKey: keys.dashboard(farmId),
    queryFn: () => api.dashboard(farmId),
    staleTime: SLOW,
  })

/** Re-run inference for a field and refresh everything derived from it. */
export const usePredictMutation = (fieldId: number) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.predict(fieldId),
    onSuccess: (prediction) => {
      qc.setQueryData(keys.prediction(fieldId), prediction)
      qc.invalidateQueries({ queryKey: keys.recommendations(fieldId) })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export const useSimulation = (fieldId: number) =>
  useMutation({
    mutationFn: (payload: SimulationRequest) => api.simulate(fieldId, payload),
  })
