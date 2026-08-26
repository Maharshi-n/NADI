import { useState, useMemo } from 'react';
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
 * Phase 5: shows bottleneck icons (medicine/beds/staff).
 */

const BOTTLENECK_ICONS: Record<string, string> = {
  medicine: '💊',
  beds: '🛏️',
  staff: '👤',
};

export function RiskQueue({ items, loading, selectedFacilityId, selectedDrugId, onSelect }: RiskQueueProps) {
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  const groupedItems = useMemo(() => {
    const groups: {
      facilityId: number;
      facilityName: string;
      worstStatus: string;
      worstDays: number | null;
      items: RiskItem[];
    }[] = [];
    const map = new Map<number, typeof groups[0]>();

    items.forEach(item => {
      if (!map.has(item.facilityId)) {
        const newGroup = {
          facilityId: item.facilityId,
          facilityName: item.facilityName,
          worstStatus: item.status,
          worstDays: item.daysToStockout,
          items: [],
        };
        map.set(item.facilityId, newGroup);
        groups.push(newGroup);
      }
      map.get(item.facilityId)!.items.push(item);
    });
    return groups;
  }, [items]);

  const toggleExpand = (facilityId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(facilityId)) next.delete(facilityId);
      else next.add(facilityId);
      return next;
    });
  };

  return (
    <div className="risk-queue" id="risk-queue">
      <div className="risk-queue__header">
        Risk Queue — {loading ? '...' : `${groupedItems.length} items`}
      </div>

      {loading ? (
        <>
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonRiskItem key={i} />
          ))}
        </>
      ) : groupedItems.length === 0 ? (
        <div style={{
          padding: '40px 20px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: '0.85rem',
        }}>
          All facilities are healthy ✓
        </div>
      ) : (
        groupedItems.map((group, i) => {
          const isExpanded = expandedIds.has(group.facilityId);
          const statusClass = `risk-queue__days--${group.worstStatus}`;

          return (
            <div key={`${group.facilityId}-${i}`} className="risk-queue__group">
              {/* Facility Header */}
              <div 
                className="risk-queue__facility-header" 
                onClick={(e) => toggleExpand(group.facilityId, e)}
              >
                <span className={`status-dot status-dot--${group.worstStatus}`} />
                <div className="risk-queue__item-info">
                  <div className="risk-queue__facility">
                    {BOTTLENECK_ICONS[group.items[0]?.bottleneck || 'medicine'] || '💊'}{' '}
                    {group.facilityName}
                  </div>
                  <div className="risk-queue__drug">
                    {(() => {
                      const capacityCount = group.items.filter(i => i.bottleneck !== 'medicine').length;
                      const medicineCount = group.items.filter(i => i.bottleneck === 'medicine').length;
                      
                      if (capacityCount > 0 && medicineCount > 0) {
                        return `${capacityCount} capacity issue(s), ${medicineCount} medicine(s)`;
                      } else if (capacityCount > 0) {
                        return `${capacityCount} capacity issue(s)`;
                      } else {
                        return `${medicineCount} medicine(s) in shortage`;
                      }
                    })()}
                  </div>
                </div>
                <div className="risk-queue__right">
                  <div className="risk-queue__days">
                    <div className={statusClass}>
                      {group.worstDays != null ? Math.round(group.worstDays) : '—'}
                    </div>
                    <div className="risk-queue__days-label">days</div>
                  </div>
                  <div className={`risk-queue__chevron ${isExpanded ? 'risk-queue__chevron--expanded' : ''}`}>
                    ▼
                  </div>
                </div>
              </div>

              {/* Expanded Drugs List */}
              {isExpanded && (
                <div className="risk-queue__expanded-list">
                  {group.items.map((item, j) => {
                    const isSelected = selectedFacilityId === item.facilityId && selectedDrugId === item.drugId;
                    const itemStatusClass = `risk-queue__days--${item.status}`;
                    
                    return (
                      <div
                        key={`${item.facilityId}-${item.drugId}-${j}`}
                        className={`risk-queue__item ${isSelected ? 'risk-queue__item--selected' : ''}`}
                        id={`risk-item-${item.facilityId}-${item.drugId}`}
                        onClick={() => onSelect(item)}
                      >
                        <div className="risk-queue__item-info">
                          <div className="risk-queue__drug" style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                            {item.bottleneck !== 'medicine'
                              ? <><span className="risk-queue__bottleneck-icon">{BOTTLENECK_ICONS[item.bottleneck]}</span>{item.driver}</>
                              : item.drugName
                            }
                          </div>
                          {item.bottleneck === 'medicine' && item.driver && (
                            <div className="risk-queue__driver">{item.driver}</div>
                          )}
                        </div>

                        <div className="risk-queue__right">
                          <div className="risk-queue__days" style={{ fontSize: '0.9rem' }}>
                            <div className={itemStatusClass}>
                              {item.daysToStockout != null ? Math.round(item.daysToStockout) : '—'}
                            </div>
                          </div>
                          {item.confidence != null && (
                            <div className="risk-queue__confidence">
                              {Math.round(item.confidence * 100)}%
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
