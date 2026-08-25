/**
 * API client — typed fetch wrapper for /api/* endpoints.
 * Base URL configurable via env var for dev/prod.
 *
 * Phase 2: adds forecast, scenario, and reset endpoints.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function fetchJSON<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value));
      }
    });
  }

  const queryString = searchParams.toString();
  const url = `${API_BASE}${path}${queryString ? '?' + queryString : ''}`;

  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message || `API error: ${res.status}`);
  }
  return res.json();
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.error?.message || `API error: ${res.status}`);
  }
  return res.json();
}

// ---------- Types matching API.md contracts (camelCase) ----------

export interface FacilityItem {
  id: number;
  name: string;
  type: string;
  district: string;
  block: string;
  state: string;
  lat: number;
  lng: number;
  status: 'critical' | 'warning' | 'healthy';
  worstDaysOfCover: number | null;
  bedsTotal: number;
  coldChainCapable: boolean;
  populationServed: number;
}

export interface FacilityListResponse {
  items: FacilityItem[];
  total: number;
}

export interface StockSummaryItem {
  drugId: number;
  name: string;
  salt: string;
  unit: string;
  category: string;
  isEssential: boolean;
  quantity: number;
  burnRate: number | null;
  daysOfCover: number | null;
  expiryDate: string | null;
  status: 'critical' | 'warning' | 'healthy';
}

export interface FacilityDetailResponse {
  id: number;
  name: string;
  type: string;
  district: string;
  block: string;
  state: string;
  lat: number;
  lng: number;
  hfrCode: string | null;
  bedsTotal: number;
  coldChainCapable: boolean;
  populationServed: number;
  status: string;
  worstDaysOfCover: number | null;
  stock: StockSummaryItem[];
}

export interface RiskItem {
  facilityId: number;
  facilityName: string;
  drugId: number;
  drugName: string;
  daysToStockout: number | null;
  confidence: number | null;
  driver: string | null;
  bottleneck: string;
  status: 'critical' | 'warning' | 'healthy';
}

export interface RiskListResponse {
  items: RiskItem[];
  total: number;
}

export interface KpiResponse {
  facilitiesAtRisk: number;
  projectedStockoutDays: number;
  expiryAtRiskPaise: number;
  fillRate: number;
}

// ---------- Phase 2 types ----------

export interface ForecastHistoryItem {
  date: string;
  quantity: number;
}

export interface ForecastBandItem {
  date: string;
  predicted: number;
  lower: number;
  upper: number;
}

export interface ForecastResponse {
  history: ForecastHistoryItem[];
  forecast: ForecastBandItem[];
  reorderPoint: number;
  stockoutDate: string | null;
  daysToStockout: number | null;
  confidence: number;
  driver: string;
  methodUsed: string;
}

export interface ScenarioRequest {
  condition: string;
  multiplier: number;
  district?: string;
  startWeek?: number;
}

export interface ScenarioResponse {
  affectedFacilities: number;
  message: string;
}

// ---------- API calls ----------

export function fetchFacilities(params?: {
  district?: string;
  type?: string;
  limit?: number;
  offset?: number;
}): Promise<FacilityListResponse> {
  return fetchJSON('/facilities', params);
}

export function fetchFacilityDetail(id: number): Promise<FacilityDetailResponse> {
  return fetchJSON(`/facilities/${id}`);
}

export function fetchRisk(params?: {
  district?: string;
  limit?: number;
  offset?: number;
}): Promise<RiskListResponse> {
  return fetchJSON('/risk', params);
}

export function fetchKpis(params?: {
  district?: string;
}): Promise<KpiResponse> {
  return fetchJSON('/kpis', params);
}

// Phase 2

export function fetchForecast(facilityId: number, drugId: number): Promise<ForecastResponse> {
  return fetchJSON('/forecast', { facilityId, drugId });
}

export function fireScenario(body: ScenarioRequest): Promise<ScenarioResponse> {
  return postJSON('/demo/scenario', body);
}

export function resetDemo(): Promise<ScenarioResponse> {
  return postJSON('/demo/reset', {});
}
