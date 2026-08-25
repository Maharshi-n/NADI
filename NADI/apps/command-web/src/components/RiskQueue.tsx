import type { RiskItem } from '../api/client';
import { SkeletonRiskItem } from './Skeleton';

interface RiskQueueProps {
  items: RiskItem[];
  loading: boolean;
  selectedFacilityId: number | null;
  onSelect: (item: RiskItem) => void;
}

/**
 * Risk queue — ranked list, clickable.
 * Sorted ascending by days remaining (server-side).
 * Clicking a row highlights its map pin.
 */
export function RiskQueue({ items, loading, selectedFacilityId, onSelect }: RiskQueueProps) {
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
          const isSelected = selectedFacilityId === item.facilityId;
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
              </div>

              <div className="risk-queue__days">
                <div className={statusClass}>
                  {item.daysToStockout != null ? Math.round(item.daysToStockout) : '—'}
                </div>
                <div className="risk-queue__days-label">days</div>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
