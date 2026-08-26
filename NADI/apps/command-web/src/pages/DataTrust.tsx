import React, { useEffect, useState } from 'react';
import { getAnomalies, runTrustSimulation } from '../api/client';

export function DataTrust() {
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);

  const fetchAnomalies = async () => {
    setLoading(true);
    try {
      const data = await getAnomalies();
      setAnomalies(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnomalies();
  }, []);

  const handleRunSimulation = async () => {
    setSimulating(true);
    try {
      const res = await runTrustSimulation();
      setSimResult(res);
      await fetchAnomalies();
    } catch (e) {
      console.error(e);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="page-container" style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
            Data Trust & Provenance
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Cryptographic ledger integrity and statistical anomaly detection on incoming data.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {simResult && (
            <span style={{ fontSize: '0.8rem', color: 'var(--status-green)' }}>
              ✓ Hashes computed ({simResult.ledgerHashesComputed} rows)
            </span>
          )}
          <button 
            className="btn-primary" 
            onClick={handleRunSimulation} 
            disabled={simulating}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            {simulating ? (
              <>
                <span className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} />
                Analyzing Ledger...
              </>
            ) : (
              'Run Trust Analysis'
            )}
          </button>
        </div>
      </div>

      <div style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--bg-glass-border)', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--bg-glass-border)', background: 'rgba(255,255,255,0.02)' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 500 }}>Detected Anomalies</h2>
        </div>
        
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>
        ) : anomalies.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--status-green)' }}>
            No anomalies detected. Ledger integrity verified.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--bg-glass-border)', textAlign: 'left' }}>
                <th style={{ padding: '12px 20px', fontWeight: 500 }}>Time Detected</th>
                <th style={{ padding: '12px 20px', fontWeight: 500 }}>Facility</th>
                <th style={{ padding: '12px 20px', fontWeight: 500 }}>Drug</th>
                <th style={{ padding: '12px 20px', fontWeight: 500 }}>Rule Triggered</th>
                <th style={{ padding: '12px 20px', fontWeight: 500 }}>Confidence</th>
                <th style={{ padding: '12px 20px', fontWeight: 500 }}>Note</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.map((a) => (
                <tr key={a.id} style={{ borderBottom: '1px solid var(--bg-glass-border)' }}>
                  <td style={{ padding: '12px 20px', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>
                    {new Date(a.detectedAt).toLocaleString()}
                  </td>
                  <td style={{ padding: '12px 20px', fontWeight: 500, color: 'var(--text-primary)' }}>
                    {a.facilityName}
                  </td>
                  <td style={{ padding: '12px 20px', color: 'var(--text-secondary)' }}>
                    {a.drugName || '—'}
                  </td>
                  <td style={{ padding: '12px 20px' }}>
                    <span style={{ 
                      padding: '2px 8px', 
                      borderRadius: '4px', 
                      fontSize: '0.75rem', 
                      background: 'var(--status-amber-dim)', 
                      color: 'var(--status-amber)',
                      fontFamily: 'monospace'
                    }}>
                      {a.rule}
                    </span>
                  </td>
                  <td style={{ padding: '12px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '40px', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{ 
                          height: '100%', 
                          width: `${a.confidence * 100}%`,
                          background: a.confidence > 0.8 ? 'var(--status-red)' : 'var(--status-amber)'
                        }} />
                      </div>
                      <span style={{ color: a.confidence > 0.8 ? 'var(--status-red)' : 'var(--status-amber)' }}>
                        {Math.round(a.confidence * 100)}%
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '12px 20px', color: 'var(--text-secondary)' }}>
                    {a.note}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
