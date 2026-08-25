import type { RiskItem } from '../api/client';
import { SkeletonRiskItem } from './Skeleton';

interface RiskQueueProps {
  items: RiskItem[];
  loading: boolean;
  selectedFacilityId: number | null;
  selectedDrugId: number | null;
  onSelect: (item: RiskItem) => void;
}

/**
 * Risk queue — ranked list, clickable.
 * Sorted ascending by days remaining (server-side).
 * Clicking a row highlights its map pin.
 * Phase 2: shows confidence badge and driver string per row.
 */
export function RiskQueue({ items, loading, selectedFacilityId, selectedDrugId, onSelect }: RiskQueueProps) {
  return (
    <div className="risk-queue" id="risk-queue">
      <div className="risk-queue__header">
        Risk Queue — {loading ? '...' : `${items.length} items`}
      </div>

      {loading ? (
        <>
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonRiskItem key={i} />
          ))}
        </>
      ) : items.length === 0 ? (
        <div style={{
          padding: '40px 20px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: '0.85rem',
        }}>
          All facilities are healthy ✓
        </div>
      ) : (
        items.map((item, i) => {
          const isSelected = selectedFacilityId === item.facilityId && selectedDrugId === item.drugId;
          const statusClass = `risk-queue__days--${item.status}`;

          return (
            <div
              key={`${item.facilityId}-${item.drugId}-${i}`}
              className={`risk-queue__item ${isSelected ? 'risk-queue__item--selected' : ''}`}
              id={`risk-item-${item.facilityId}-${item.drugId}`}
              onClick={() => onSelect(item)}
            >
              <span className={`status-dot status-dot--${item.status}`} />

              <div className="risk-queue__item-info">
                <div className="risk-queue__facility">{item.facilityName}</div>
                <div className="risk-queue__drug">{item.drugName}</div>
                {/* Phase 2: Driver string */}
                {item.driver && (
                  <div className="risk-queue__driver">{item.driver}</div>
                )}
              </div>

              <div className="risk-queue__right">
                <div className="risk-queue__days">
                  <div className={statusClass}>
                    {item.daysToStockout != null ? Math.round(item.daysToStockout) : '—'}
                  </div>
                  <div className="risk-queue__days-label">days</div>
                </div>
                {/* Phase 2: Confidence badge */}
                {item.confidence != null && (
                  <div className={`risk-queue__confidence ${
                    item.confidence >= 0.7 ? 'risk-queue__confidence--high' :
                    item.confidence >= 0.4 ? 'risk-queue__confidence--mid' :
                    'risk-queue__confidence--low'
                  }`}>
                    {Math.round(item.confidence * 100)}%
                  </div>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
