import { useEffect, useState, useCallback } from 'react';
import { fetchFacilities, fetchRisk, fetchKpis } from '../api/client';
import type { FacilityItem, RiskItem, KpiResponse } from '../api/client';
import { MapView } from '../components/Map';
import { KpiTiles } from '../components/KpiTiles';
import { RiskQueue } from '../components/RiskQueue';
import { FacilityDetail } from '../components/FacilityDetail';

/**
 * District Dashboard — the main page of Phase 1.
 * Composes map, KPI tiles, risk queue, and facility detail.
 */
export function Dashboard() {
  const [facilities, setFacilities] = useState<FacilityItem[]>([]);
  const [riskItems, setRiskItems] = useState<RiskItem[]>([]);
  const [kpis, setKpis] = useState<KpiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFacilityId, setSelectedFacilityId] = useState<number | null>(null);

  // Load all data on mount
  useEffect(() => {
    async function loadData() {
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
    }
    loadData();
  }, []);

  const handleRiskSelect = useCallback((item: RiskItem) => {
    setSelectedFacilityId((prev) =>
      prev === item.facilityId ? null : item.facilityId
    );
  }, []);

  const handleMapSelect = useCallback((id: number) => {
    setSelectedFacilityId((prev) => (prev === id ? null : id));
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedFacilityId(null);
  }, []);

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
        {selectedFacilityId != null && (
          <FacilityDetail
            facilityId={selectedFacilityId}
            onClose={handleCloseDetail}
          />
        )}
      </div>

      {/* Sidebar: KPIs + Risk Queue */}
      <div className="dashboard__sidebar" id="dashboard-sidebar">
        <KpiTiles kpis={kpis} loading={loading} />
        <RiskQueue
          items={riskItems}
          loading={loading}
          selectedFacilityId={selectedFacilityId}
          onSelect={handleRiskSelect}
        />
      </div>
    </div>
  );
}
