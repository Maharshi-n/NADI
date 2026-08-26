import { useEffect, useState, useCallback } from 'react';
import { fetchFacilities, fetchRisk, fetchKpis, fetchCapacity } from '../api/client';
import type { FacilityItem, RiskItem, KpiResponse } from '../api/client';
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
      if (prev === id) {
        setSelectedDrugId(null);
        setShowCapacity(false);
        return null;
      }
      // When selecting from map, show capacity panel
      setSelectedDrugId(null);
      setShowCapacity(true);
      return id;
    });
  }, []);

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

  return (
    <div className="dashboard" id="dashboard">
      {/* Map area */}
      <div className="dashboard__map">
        {/* KPI Tiles overlay on the map */}
        <div className="dashboard__kpi-overlay">
          <KpiTiles kpis={kpis} loading={loading} />
        </div>

        <MapView
          facilities={facilities}
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
      <div className="dashboard__sidebar" id="dashboard-sidebar">
        <ScenarioRunner onScenarioFired={handleScenarioFired} />
        <RiskQueue
          items={riskItems}
          loading={loading}
          selectedFacilityId={selectedFacilityId}
          selectedDrugId={selectedDrugId}
          onSelect={handleRiskSelect}
        />
      </div>
    </div>
  );
}
