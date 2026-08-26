import { useEffect, useState } from 'react';
import { fetchFacilityDetail } from '../api/client';
import type { FacilityDetailResponse } from '../api/client';
import { Skeleton } from './Skeleton';

interface FacilityDetailProps {
  facilityId: number;
  onClose: () => void;
}

/**
 * Facility detail panel — shows on the map when a facility is selected.
 * Displays stock breakdown with burn rate and days of cover.
 */
export function FacilityDetail({ facilityId, onClose }: FacilityDetailProps) {
  const [facility, setFacility] = useState<FacilityDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchFacilityDetail(facilityId)
      .then(setFacility)
      .catch((err) => console.error('Failed to load facility:', err))
      .finally(() => setLoading(false));
  }, [facilityId]);

  if (loading) {
    return (
      <div className="facility-detail glass-card" id="facility-detail">
        <div className="facility-detail__header">
          <Skeleton width="200px" height="20px" />
          <button className="facility-detail__close" onClick={onClose}>✕</button>
        </div>
        <Skeleton width="150px" height="14px" />
        <div style={{ marginTop: 16 }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} height="36px" className="fade-in" />
          ))}
        </div>
      </div>
    );
  }

  if (!facility) return null;

  return (
    <div className="facility-detail glass-card" id="facility-detail">
      <div className="facility-detail__header">
        <div>
          <div className="facility-detail__name">{facility.name}</div>
          <span className={`status-pill status-pill--${facility.status}`}>
            {facility.status}
          </span>
        </div>
        <button className="facility-detail__close" onClick={onClose}>✕</button>
      </div>

      <div className="facility-detail__meta">
        <span>📍 {facility.block}, {facility.district}</span>
        <span>🛏️ {facility.bedsTotal} beds</span>
        <span>👥 {facility.populationServed.toLocaleString()} served</span>
        {facility.coldChainCapable && <span>❄️ Cold chain</span>}
      </div>

      {facility.stock.length > 0 ? (
        <div className="facility-detail__stock-grid">
          <div className="facility-detail__stock-row" style={{
            fontWeight: 600,
            fontSize: '0.7rem',
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            background: 'transparent',
          }}>
            <span>Drug</span>
            <span style={{ textAlign: 'right' }}>Stock</span>
            <span style={{ textAlign: 'right' }}>Burn/day</span>
            <span style={{ textAlign: 'right' }}>Cover</span>
          </div>
          {facility.stock.slice(0, 10).map((s) => (
            <div key={s.drugId} className="facility-detail__stock-row">
              <span className="facility-detail__stock-name">
                {s.isEssential && <span style={{ color: 'var(--accent)', marginRight: 4 }}>●</span>}
                {s.name}
              </span>
              <span className="facility-detail__stock-qty">
                {s.quantity.toLocaleString()} {s.unit}
              </span>
              <span className="facility-detail__stock-burn">
                {s.burnRate != null ? `${s.burnRate.toFixed(1)}/d` : '—'}
              </span>
              <span style={{
                textAlign: 'right',
                fontWeight: 600,
                color: s.status === 'critical' ? 'var(--critical)'
                     : s.status === 'warning' ? 'var(--warning)'
                     : 'var(--healthy)',
              }}>
                {s.daysOfCover != null ? `${Math.round(s.daysOfCover)}d` : '—'}
              </span>
            </div>
          ))}
          {facility.stock.length > 10 && (
            <div style={{
              padding: '8px 12px',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              textAlign: 'center',
            }}>
              +{facility.stock.length - 10} more items
            </div>
          )}
        </div>
      ) : (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '16px 0' }}>
          No stock data available
        </div>
      )}
    </div>
  );
}
