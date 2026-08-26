import { useState, useCallback, useEffect } from 'react';
import { generatePlan, approveTransfers, fetchFacilities } from '../api/client';
import type { PlanResponse, FacilityItem } from '../api/client';
import { TransferMap } from '../components/TransferMap';
import { ImpactPanel } from '../components/ImpactPanel';
import { TransferTable } from '../components/TransferTable';

export function TransferPlanner() {
  const [facilities, setFacilities] = useState<FacilityItem[]>([]);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // We need facilities to draw the map
  const loadFacilities = useCallback(async () => {
    try {
      const res = await fetchFacilities({ limit: 100 });
      setFacilities(res.items);
    } catch (err: any) {
      console.error('Failed to load facilities:', err);
    }
  }, []);

  useEffect(() => {
    loadFacilities();
  }, [loadFacilities]);

  const handleGeneratePlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await generatePlan({});
      setPlan(res);
    } catch (err: any) {
      setError(err.message || 'Failed to generate plan');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (selectedIds: number[]) => {
    if (!plan) return;
    setApproving(true);
    setError(null);
    try {
      // Create a list of the actual transfers to pass down
      const transfersToApprove = plan.transfers.filter((_, idx) => selectedIds.includes(idx));
      
      await approveTransfers({
        planId: plan.planId,
        transfers: transfersToApprove,
      });

      // After successful approval, remove them from the plan locally or regenerate
      const remainingTransfers = plan.transfers.filter((_, idx) => !selectedIds.includes(idx));
      setPlan({ ...plan, transfers: remainingTransfers });
    } catch (err: any) {
      setError(err.message || 'Failed to approve transfers');
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="dashboard" style={{ height: 'calc(100vh - var(--header-height))', display: 'flex' }}>
      {/* Map area (takes up available space) */}
      <div className="dashboard__map" style={{ flex: 1, position: 'relative' }}>
        <TransferMap 
          facilities={facilities} 
          transfers={plan?.transfers || []} 
        />
        
        {/* Overlay controls */}
        <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 10 }}>
          <div className="panel" style={{ padding: '20px', background: 'var(--bg-card)' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '12px' }}>AI Optimizer</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px', maxWidth: '250px' }}>
              Run the min-cost flow engine to find optimal stock redistributions.
            </p>
            <button 
              className="btn-primary" 
              onClick={handleGeneratePlan}
              disabled={loading || approving}
              style={{ width: '100%' }}
            >
              {loading ? 'Generating...' : 'Generate Plan'}
            </button>
            {error && (
              <div style={{ marginTop: '12px', color: 'var(--critical)', fontSize: '0.85rem' }}>
                {error}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Sidebar: Impact and Transfer Table */}
      <div className="dashboard__sidebar" style={{ width: '500px', display: 'flex', flexDirection: 'column', gap: '16px', padding: '16px', overflowY: 'auto', background: 'var(--bg-secondary)' }}>
        {plan ? (
          <>
            <ImpactPanel impact={plan.impact} />
            <TransferTable 
              transfers={plan.transfers} 
              onApprove={handleApprove} 
              isApproving={approving} 
            />
          </>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
            No plan generated yet.
          </div>
        )}
      </div>
    </div>
  );
}
