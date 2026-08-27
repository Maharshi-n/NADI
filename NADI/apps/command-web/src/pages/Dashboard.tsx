import { useEffect, useState, useCallback, useMemo } from 'react';
import { fetchFacilities, fetchRisk, fetchKpis, fetchCapacity } from '../api/client';
import type { FacilityItem, RiskItem, KpiResponse, TwinSimulateResponse } from '../api/client';
import { MapView } from '../components/Map';
import { KpiTiles } from '../components/KpiTiles';
import { RiskQueue } from '../components/RiskQueue';
import { FacilityDetail } from '../components/FacilityDetail';
import { ForecastPanel } from '../components/ForecastPanel';
import { ScenarioRunner } from '../components/ScenarioRunner';
import { CapacityPanel } from '../components/CapacityPanel';

/**
 * District Dashboard — Phase 5.
 * Composes map, KPI tiles, risk queue, forecast panel, scenario runner,
 * facility detail, and capacity panel.
 */
export function Dashboard() {
  const [facilities, setFacilities] = useState<FacilityItem[]>([]);
  const [riskItems, setRiskItems] = useState<RiskItem[]>([]);
  const [kpis, setKpis] = useState<KpiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFacilityId, setSelectedFacilityId] = useState<number | null>(null);
  const [selectedDrugId, setSelectedDrugId] = useState<number | null>(null);
  const [selectedFacilityName, setSelectedFacilityName] = useState('');
  const [selectedDrugName, setSelectedDrugName] = useState('');
  // Phase 5: track whether to show capacity panel
  const [showCapacity, setShowCapacity] = useState(false);
  // Phase 8: War Room simulation result
  const [twinResult, setTwinResult] = useState<TwinSimulateResponse | null>(null);

  const simulatedFacilities = useMemo(() => {
    if (!twinResult) return facilities;
    return facilities.map(fac => {
      const frag = twinResult.fragilityRanking.find(f => f.facilityId === fac.id);
      if (!frag || frag.daysToStockout === null) return { ...fac, status: 'healthy' as const };
      if (frag.daysToStockout < 15) return { ...fac, status: 'critical' as const };
      if (frag.daysToStockout < 30) return { ...fac, status: 'warning' as const };
      return { ...fac, status: 'healthy' as const };
    });
  }, [facilities, twinResult]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // Phase 5: trigger capacity computation first, then load everything
      try {
        await fetchCapacity({});
      } catch {
        // Capacity computation is best-effort
      }

      const [facRes, riskRes, kpiRes] = await Promise.all([
        fetchFacilities({ limit: 100 }),
        fetchRisk({ limit: 100 }),
        fetchKpis({}),
      ]);
      setFacilities(facRes.items);
      setRiskItems(riskRes.items);
      setKpis(kpiRes);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load all data on mount
  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRiskSelect = useCallback((item: RiskItem) => {
    // Phase 5: non-medicine bottleneck items open capacity panel
    if (item.bottleneck !== 'medicine') {
      setSelectedFacilityId(item.facilityId);
      setSelectedDrugId(null);
      setSelectedFacilityName(item.facilityName);
      setSelectedDrugName('');
      setShowCapacity(true);
      return;
    }

    setShowCapacity(false);
    setSelectedFacilityId((prev) => {
      const isSame = prev === item.facilityId && selectedDrugId === item.drugId;
      if (isSame) {
        setSelectedDrugId(null);
        setSelectedFacilityName('');
        setSelectedDrugName('');
        return null;
      }
      setSelectedDrugId(item.drugId);
      setSelectedFacilityName(item.facilityName);
      setSelectedDrugName(item.drugName || '');
      return item.facilityId;
    });
  }, [selectedDrugId]);

  const handleMapSelect = useCallback((id: number) => {
    setSelectedFacilityId((prev) => {
      if (prev === id && !showCapacity) {
        setSelectedDrugId(null);
        return null;
      }
      setSelectedDrugId(null);
      // Always show FacilityDetail on map click so user can drill down to drugs
      setShowCapacity(false);
      return id;
    });
  }, [showCapacity]);

  const handleFacilityDetailSelect = useCallback((id: number) => {
    setSelectedFacilityId((prev) => {
      if (prev === id && !showCapacity) {
        setSelectedDrugId(null);
        return null;
      }
      setSelectedDrugId(null);
      setShowCapacity(false);
      return id;
    });
  }, [showCapacity]);

  const handleCloseDetail = useCallback(() => {
    setSelectedFacilityId(null);
    setSelectedDrugId(null);
    setShowCapacity(false);
  }, []);

  const handleScenarioFired = useCallback(() => {
    // Refresh all data after scenario fire or reset
    loadData();
    setSelectedDrugId(null);
    setShowCapacity(false);
  }, [loadData]);

  const handleModeChange = useCallback(() => {
    setSelectedFacilityId(null);
    setSelectedDrugId(null);
    setShowCapacity(false);
  }, []);

  return (
    <div className="dashboard" id="dashboard">
      {/* Map area */}
      <div className="dashboard__map" style={{ position: 'relative', border: twinResult ? '2px solid var(--accent)' : 'none', transition: 'border 0.3s ease' }}>
        {twinResult && (
          <div style={{ position: 'absolute', top: 16, left: '50%', transform: 'translateX(-50%)', background: 'var(--accent)', color: '#fff', padding: '6px 16px', borderRadius: '20px', fontSize: '0.85rem', fontWeight: 600, zIndex: 100, boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}>
            MACRO PREDICTION ACTIVE
          </div>
        )}
        
        {/* KPI Tiles overlay on the map */}
        <div className="dashboard__kpi-overlay">
          <KpiTiles kpis={kpis} loading={loading} />
        </div>

        <MapView
          facilities={simulatedFacilities}
          selectedFacilityId={selectedFacilityId}
          onSelectFacility={handleMapSelect}
        />

        {/* Phase 5: Capacity panel overlay */}
        {selectedFacilityId != null && showCapacity && (
          <CapacityPanel
            facilityId={selectedFacilityId}
            onClose={handleCloseDetail}
          />
        )}

        {/* Facility detail overlay on the map */}
        {selectedFacilityId != null && !showCapacity && selectedDrugId == null && (
          <FacilityDetail
            facilityId={selectedFacilityId}
            onClose={handleCloseDetail}
            onSelectDrug={(drugId, drugName) => {
              setSelectedDrugId(drugId);
              setSelectedDrugName(drugName);
            }}
          />
        )}

        {/* Forecast panel overlay on the map */}
        {selectedFacilityId != null && selectedDrugId != null && (
          <ForecastPanel
            facilityId={selectedFacilityId}
            drugId={selectedDrugId}
            facilityName={selectedFacilityName}
            drugName={selectedDrugName}
            onClose={handleCloseDetail}
          />
        )}
      </div>

      {/* Sidebar: Scenario + Risk Queue */}
      <div className="dashboard__sidebar" id="dashboard-sidebar" style={{ overflowY: twinResult ? 'auto' : 'hidden' }}>
        <div style={{ flexShrink: 0 }}>
          <ScenarioRunner 
            onScenarioFired={handleScenarioFired} 
            onTwinResult={setTwinResult}
            onModeChange={handleModeChange}
          />
        </div>
        
        {twinResult ? (
          <div style={{ padding: '0 16px 16px 16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>Simulation Results</h2>
              <button 
                onClick={() => setTwinResult(null)}
                style={{ background: 'transparent', border: '1px solid var(--bg-glass-border)', color: 'var(--text-secondary)', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem' }}
              >
                ✕ Close
              </button>
            </div>

            <div className="panel" style={{ padding: '16px', background: 'var(--bg-card)' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Stockout Days Prevented</div>
              <div style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--healthy)' }}>
                {twinResult.counterfactualImpact.stockoutDaysPrevented}
              </div>
            </div>
            
            <div className="panel" style={{ padding: '16px', background: 'var(--bg-card)' }}>
              <h3 style={{ fontSize: '1rem', marginBottom: '12px', color: 'var(--text-primary)' }}>First to Break</h3>
              {twinResult.firstToBreak.length === 0 ? (
                <div style={{ color: 'var(--text-muted)' }}>No stockouts projected.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {twinResult.firstToBreak.map(f => (
                    <div 
                      key={f.facilityId} 
                      style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--bg-glass-border)', paddingBottom: '8px', cursor: 'pointer' }}
                      onClick={() => handleFacilityDetailSelect(f.facilityId)}
                    >
                      <span style={{ fontSize: '0.9rem' }}>{f.facilityName}</span>
                      <span style={{ fontSize: '0.9rem', color: 'var(--critical)' }}>In {f.daysToStockout} days</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <RiskQueue
            items={riskItems}
            loading={loading}
            selectedFacilityId={selectedFacilityId}
            selectedDrugId={selectedDrugId}
            onSelect={handleRiskSelect}
          />
        )}
      </div>
    </div>
  );
}
