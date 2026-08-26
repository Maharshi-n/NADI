import { useEffect, useState } from 'react';
import { fetchCapacity } from '../api/client';
import type { CapacityResponse } from '../api/client';

interface CapacityPanelProps {
  facilityId: number;
  onClose: () => void;
}

const BOTTLENECK_ICONS: Record<string, string> = {
  medicine: '💊',
  beds: '🛏️',
  staff: '👤',
};

const BOTTLENECK_LABELS: Record<string, string> = {
  medicine: 'Medicine Supply',
  beds: 'Bed Availability',
  staff: 'Staff Presence',
};

function ScoreBar({ label, score, icon, infoTooltip }: { label: string; score: number; icon: string; infoTooltip?: string }) {
  const pct = Math.round(score * 100);
  const color =
    pct < 30 ? 'var(--critical)' :
    pct < 60 ? 'var(--warning)' :
    'var(--healthy)';

  return (
    <div className="capacity-bar">
      <div className="capacity-bar__header">
        <span className="capacity-bar__icon">{icon}</span>
        <div className="capacity-bar__label">
          {label}
          {infoTooltip && (
            <div className="capacity-bar__info-wrapper">
              <span className="capacity-bar__info-icon">ⓘ</span>
              <div className="capacity-bar__tooltip">{infoTooltip}</div>
            </div>
          )}
        </div>
        <span className="capacity-bar__value" style={{ color }}>{pct}%</span>
      </div>
      <div className="capacity-bar__track">
        <div
          className="capacity-bar__fill"
          style={{
            width: `${pct}%`,
            background: color,
          }}
        />
      </div>
    </div>
  );
}

/**
 * Capacity Panel — Phase 5.
 * Shows CBI ring, three constraint bars (medicine/beds/staff),
 * days-to-saturation, spillover, and staff roster.
 */
export function CapacityPanel({ facilityId, onClose }: CapacityPanelProps) {
  const [data, setData] = useState<CapacityResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchCapacity({ facilityId })
      .then((res) => {
        // Single facility returns a single object
        setData(Array.isArray(res) ? res[0] : res);
      })
      .catch((err) => console.error('Failed to load capacity:', err))
      .finally(() => setLoading(false));
  }, [facilityId]);

  if (loading) {
    return (
      <div className="capacity-panel glass-panel">
        <div className="capacity-panel__header">
          <h3>Capacity</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="capacity-panel__loading">Loading capacity data...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="capacity-panel glass-panel">
        <div className="capacity-panel__header">
          <h3>Capacity</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="capacity-panel__loading">No capacity data available</div>
      </div>
    );
  }

  const cbiPct = Math.round(data.cbi * 100);
  const cbiColor =
    cbiPct < 30 ? 'var(--critical)' :
    cbiPct < 60 ? 'var(--warning)' :
    'var(--healthy)';

  return (
    <div className="capacity-panel glass-panel fade-in">
      <div className="capacity-panel__header">
        <h3>{data.facilityName}</h3>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>

      {/* CBI Ring */}
      <div className="capacity-panel__cbi">
        <div
          className="cbi-ring"
          style={{
            background: `conic-gradient(${cbiColor} ${cbiPct * 3.6}deg, rgba(255,255,255,0.08) 0deg)`,
          }}
        >
          <div className="cbi-ring__inner">
            <span className="cbi-ring__value" style={{ color: cbiColor }}>{cbiPct}</span>
            <span className="cbi-ring__label">CBI</span>
          </div>
        </div>
        <div className="capacity-panel__bottleneck">
          <span className="bottleneck-badge" style={{
            borderColor: cbiColor,
            color: cbiColor,
          }}>
            {BOTTLENECK_ICONS[data.bottleneck] || '⚠️'}{' '}
            {BOTTLENECK_LABELS[data.bottleneck] || data.bottleneck}
          </span>
        </div>
      </div>

      {/* Three constraint bars */}
      <div className="capacity-panel__bars">
        <ScoreBar 
          label="Medicine" 
          score={data.medicineScore} 
          icon="💊" 
          infoTooltip="% of essential drugs with > 15 days cover. Drops to 0% if Pharmacist is missing."
        />
        <ScoreBar label="Beds" score={data.bedScore} icon="🛏️" />
        <ScoreBar label="Staff" score={data.staffScore} icon="👤" />
      </div>

      {/* Bed details */}
      <div className="capacity-panel__details">
        <div className="capacity-detail-row">
          <span>Beds</span>
          <span>{data.bedsOccupied} / {data.bedsTotal} occupied</span>
        </div>
        {data.daysToSaturation != null && (
          <div className="capacity-detail-row capacity-detail-row--warning">
            <span>⏳ Days to saturation</span>
            <span style={{ color: 'var(--warning)', fontWeight: 600 }}>
              {data.daysToSaturation}
            </span>
          </div>
        )}
        {data.spilloverTo && (
          <div className="capacity-detail-row">
            <span>↗️ Spillover to</span>
            <span style={{ color: 'var(--accent-hover)', fontWeight: 600 }}>{data.spilloverTo.name}</span>
          </div>
        )}
      </div>

      {/* Staff roster */}
      <div className="capacity-panel__staff">
        <div className="capacity-panel__staff-title">Staff Roster</div>
        {Object.keys(data.staffRequired).length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>No staff data</div>
        ) : (
          Object.entries(data.staffRequired).map(([role, required]) => {
            const present = data.staffPresent[role] || 0;
            const isMissing = present < required;
            return (
              <div
                key={role}
                className={`staff-row ${isMissing ? 'staff-row--missing' : ''}`}
              >
                <span className="staff-row__role">{role}</span>
                <span className={`staff-row__status ${isMissing ? 'staff-row__status--absent' : 'staff-row__status--present'}`}>
                  {present}/{required} {isMissing ? '✗' : '✓'}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
