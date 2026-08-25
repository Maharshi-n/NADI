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
 * Composes map, KPI tiles, risk queue, forecast panel, scenario runner,
 * and facility detail.
 */
export function Dashboard() {
  const [facilities, setFacilities] = useState<FacilityItem[]>([]);
  const [riskItems, setRiskItems] = useState<RiskItem[]>([]);
  const [kpis, setKpis] = useState<KpiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFacilityId, setSelectedFacilityId] = useState<number | null>(null);
  const [selectedDrugId, setSelectedDrugId] = useState<number | null>(null);
  const [selectedDrugName, setSelectedDrugName] = useState<string>('');
  const [selectedFacilityName, setSelectedFacilityName] = useState<string>('');

  // Load all data
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

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRiskSelect = useCallback((item: RiskItem) => {
    setSelectedFacilityId((prev) => {
      const isSame = prev === item.facilityId && selectedDrugId === item.drugId;
      if (isSame) {
        setSelectedDrugId(null);
        setSelectedDrugName('');
        setSelectedFacilityName('');
        return null;
      }
      setSelectedDrugId(item.drugId);
      setSelectedDrugName(item.drugName);
      setSelectedFacilityName(item.facilityName);
      return item.facilityId;
    });
  }, [selectedDrugId]);

  const handleMapSelect = useCallback((id: number) => {
    setSelectedFacilityId((prev) => {
      if (prev === id) {
        setSelectedDrugId(null);
        setSelectedDrugName('');
        setSelectedFacilityName('');
        return null;
      }
      // When selecting from map, clear drug selection (show facility detail only)
      setSelectedDrugId(null);
      setSelectedDrugName('');
      setSelectedFacilityName('');
      return id;
    });
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedFacilityId(null);
    setSelectedDrugId(null);
    setSelectedDrugName('');
    setSelectedFacilityName('');
  }, []);

  const handleScenarioChange = useCallback(() => {
    // Reload all data after scenario fire/reset
    loadData();
    // Clear selection so user sees the updated risk queue
    setSelectedFacilityId(null);
    setSelectedDrugId(null);
    setSelectedDrugName('');
    setSelectedFacilityName('');
  }, [loadData]);

  return (
    <div className="dashboard" id="dashboard">
      {/* Map area */}
      <div className="dashboard__map">
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
      </div>

      {/* Sidebar: KPIs + Risk Queue + Forecast Panel + Scenario Runner */}
      <div className="dashboard__sidebar" id="dashboard-sidebar">
        <KpiTiles kpis={kpis} loading={loading} />
        <RiskQueue
          items={riskItems}
          loading={loading}
          selectedFacilityId={selectedFacilityId}
          selectedDrugId={selectedDrugId}
          onSelect={handleRiskSelect}
        />

        {/* Phase 2: Forecast panel shown when a risk item is selected */}
        {selectedFacilityId != null && selectedDrugId != null && (
          <ForecastPanel
            facilityId={selectedFacilityId}
            drugId={selectedDrugId}
            facilityName={selectedFacilityName}
            drugName={selectedDrugName}
          />
        )}

        {/* Phase 2: Scenario runner */}
        <ScenarioRunner onScenarioChange={handleScenarioChange} />
      </div>
    </div>
  );
}
