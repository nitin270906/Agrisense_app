/** Types mirroring the FastAPI response schemas. */

export type RiskLevel = 'low' | 'moderate' | 'high' | 'critical'
export type Severity = 'info' | 'warning' | 'urgent' | 'critical'
export type RecommendationCategory =
  | 'irrigation'
  | 'leaching'
  | 'amendment'
  | 'crop_choice'
  | 'drainage'
  | 'monitoring'

export interface Farm {
  id: number
  name: string
  owner: string
  region: string
  state: string
  lat: number
  lon: number
  field_count: number
}

export interface Field {
  id: number
  farm_id: number
  name: string
  crop: string
  area_ha: number
  soil_texture: string
  drainage_class: string
  planting_date: string
  irrigation_water_ec: number
  water_table_depth_m: number
  lat: number
  lon: number
}

export interface CropProfile {
  crop: string
  display_name: string
  salt_threshold_a: number
  salt_slope_b: number
  root_depth_m: number
  season_days: number
  tolerance_label: string
}

export interface Reading {
  id: number
  field_id: number
  ts: string
  soil_ec: number
  soil_moisture_pct: number
  soil_temp_c: number
  ph: number
  irrigation_mm: number
  source: string
}

export interface WeatherDay {
  date: string
  t_mean_c: number
  t_max_c: number
  t_min_c: number
  precip_mm: number
  et0_mm: number
  humidity_pct: number
  wind_ms: number
  is_forecast: boolean
}

export interface Weather {
  lat: number
  lon: number
  provider: string
  from_cache: boolean
  stale: boolean
  days: WeatherDay[]
}

export interface Driver {
  feature: string
  label: string
  value: number
  importance: number
}

export interface Prediction {
  id: number | null
  field_id: number
  ts: string
  horizon_days: number
  salinity_ec: number
  salinity_delta: number
  water_stress_index: number
  irrigation_need_mm: number
  health_score: number
  risk_level: RiskLevel
  confidence: number
  model_version: string
  drivers: Driver[]
  salinity_ec_p10?: number | null
  salinity_ec_p90?: number | null
}

export interface ForecastPoint {
  date: string
  salinity_ec: number
  water_stress_index: number
  health_score: number
  is_forecast: boolean
}

export interface Recommendation {
  id: number | null
  field_id: number
  category: RecommendationCategory
  severity: Severity
  title: string
  message: string
  action_mm: number | null
  priority: number
}

export interface FieldSummary {
  field_id: number
  field_name: string
  farm_id: number
  farm_name: string
  crop: string
  area_ha: number
  lat: number
  lon: number
  salinity_ec: number
  salinity_delta: number
  water_stress_index: number
  irrigation_need_mm: number
  health_score: number
  risk_level: RiskLevel
  top_action: string | null
  sparkline: number[]
}

export interface DashboardSummary {
  total_fields: number
  total_area_ha: number
  fields_at_risk: number
  critical_alerts: number
  avg_salinity_ec: number
  avg_health_score: number
  total_irrigation_need_mm: number
  risk_breakdown: Record<string, number>
  fields: FieldSummary[]
}

export interface SimulationPoint {
  day: number
  date: string
  salinity_ec: number
  water_stress_index: number
  health_score: number
  soil_moisture_pct: number
}

export interface SimulationRequest {
  irrigation_mm: number
  irrigation_water_ec?: number | null
  irrigation_interval_days: number
  rainfall_scenario: number
  horizon_days: number
  drainage_class?: string | null
  fertilizer_rate?: number
  mulching?: boolean
}

export interface SimulationResult {
  baseline: SimulationPoint[]
  scenario: SimulationPoint[]
  salinity_change: number
  health_change: number
  water_applied_mm: number
  summary: string
}

export interface TargetMetrics {
  overall: { r2: number; mae: number; rmse: number }
  baseline: { r2: number; mae: number; rmse: number }
  nonzero_tail?: { r2: number; mae: number; rmse: number }
  zero_share?: number
  best_iteration: number
  n_train: number
  n_test: number
  top_features: { feature: string; importance: number }[]
}

export interface ModelInfo {
  model_version: string
  trained_at: string | null
  loaded: boolean
  n_rows: number | null
  n_fields: number | null
  split: string | null
  data_provenance: string | null
  feature_count: number
  metrics: Record<string, TargetMetrics>
}

export interface Health {
  status: string
  model_loaded: boolean
  model_version: string
  weather_provider: string
  database: string
}
