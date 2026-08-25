import type { KpiResponse } from '../api/client';
import { SkeletonKpiTile } from './Skeleton';

interface KpiTilesProps {
  kpis: KpiResponse | null;
  loading: boolean;
}

/**
 * Four KPI tiles — per Phase 1 spec.
 * Computed server-side in one endpoint, displayed here.
 */
export function KpiTiles({ kpis, loading }: KpiTilesProps) {
  if (loading || !kpis) {
    return (
      <div className="kpi-grid" id="kpi-grid">
        <SkeletonKpiTile />
        <SkeletonKpiTile />
        <SkeletonKpiTile />
        <SkeletonKpiTile />
      </div>
    );
  }

  return (
    <div className="kpi-grid fade-in" id="kpi-grid">
      <div className="kpi-tile" id="kpi-facilities-at-risk">
        <span className="kpi-tile__label">Facilities at Risk</span>
        <span className="kpi-tile__value" style={{ color: kpis.facilitiesAtRisk > 0 ? 'var(--critical)' : undefined }}>
          {kpis.facilitiesAtRisk}
        </span>
        <span className="kpi-tile__sub">below 15 days cover</span>
      </div>

      <div className="kpi-tile" id="kpi-stockout-days">
        <span className="kpi-tile__label">Stockout-Days</span>
        <span className="kpi-tile__value">
          {kpis.projectedStockoutDays.toLocaleString()}
        </span>
        <span className="kpi-tile__sub">projected deficit</span>
      </div>

      <div className="kpi-tile" id="kpi-expiry-risk">
        <span className="kpi-tile__label">Expiry at Risk</span>
        <span className="kpi-tile__value">
          {kpis.expiryAtRiskPaise > 0
            ? `₹${(kpis.expiryAtRiskPaise / 100).toLocaleString()}`
            : '—'}
        </span>
        <span className="kpi-tile__sub">value of near-expiry stock</span>
      </div>

      <div className="kpi-tile" id="kpi-fill-rate">
        <span className="kpi-tile__label">Fill Rate</span>
        <span className="kpi-tile__value" style={{
          color: kpis.fillRate < 0.8 ? 'var(--warning)' : kpis.fillRate >= 0.95 ? 'var(--healthy)' : undefined,
        }}>
          {(kpis.fillRate * 100).toFixed(1)}%
        </span>
        <span className="kpi-tile__sub">essential drugs in stock</span>
      </div>
    </div>
  );
}
