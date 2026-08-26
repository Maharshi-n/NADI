import { useEffect, useState, useCallback } from 'react';
import { fetchFacilities, fetchRisk, fetchKpis } from '../api/client';
import type { FacilityItem, RiskItem, KpiResponse } from '../api/client';
import { MapView } from '../components/Map';
import { KpiTiles } from '../components/KpiTiles';
import { RiskQueue } from '../components/RiskQueue';
import { FacilityDetail } from '../components/FacilityDetail';
import { ForecastPanel } from '../components/ForecastPanel';
import { ScenarioRunner } from '../components/ScenarioRunner';

/**
 * District Dashboard — Phase 2.
 * Composes map, KPI tiles, risk queue, forecast panel, scenario runner, and facility detail.
 */
export function Dashboard() {
  const [facilities, setFacilities] = useState<FacilityItem[]>([]);
  const [riskItems, setRiskItems] = useState<RiskItem[]>([]);
  const [kpis, setKpis] = useState<KpiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFacilityId, setSelectedFacilityId] = useState<number | null>(null);
  // Phase 2: track selected drug for forecast panel
  const [selectedDrugId, setSelectedDrugId] = useState<number | null>(null);
  const [selectedFacilityName, setSelectedFacilityName] = useState('');
  const [selectedDrugName, setSelectedDrugName] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
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
      setSelectedDrugName(item.drugName);
      return item.facilityId;
    });
  }, [selectedDrugId]);

  const handleMapSelect = useCallback((id: number) => {
    setSelectedFacilityId((prev) => {
      if (prev === id) {
        setSelectedDrugId(null);
        return null;
      }
      // When selecting from map, clear drug selection (show facility detail only)
      setSelectedDrugId(null);
      return id;
    });
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedFacilityId(null);
    setSelectedDrugId(null);
  }, []);

  const handleScenarioFired = useCallback(() => {
    // Refresh all data after scenario fire or reset
    loadData();
    // Clear forecast selection to force re-fetch
    setSelectedDrugId(null);
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

        {/* Facility detail overlay on the map */}
        {selectedFacilityId != null && selectedDrugId == null && (
          <FacilityDetail
            facilityId={selectedFacilityId}
            onClose={handleCloseDetail}
          />
        )}

        {/* Phase 2: Forecast panel overlay on the map */}
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
