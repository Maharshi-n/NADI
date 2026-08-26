import { useEffect, useState, useCallback } from 'react';
import { fetchFederationStatus, runFederationSimulation } from '../api/client';
import type { FlRoundResponse, FlClientResponse } from '../api/client';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

export function FederationDashboard() {
  const [rounds, setRounds] = useState<FlRoundResponse[]>([]);
  const [clients, setClients] = useState<FlClientResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const res = await fetchFederationStatus();
      setRounds(res.rounds);
      setClients(res.clients);
    } catch (err) {
      console.error('Failed to load federation status', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunSimulation = async () => {
    setSimulating(true);
    setRounds([]); // Clear visual data
    
    try {
      await runFederationSimulation();
      const res = await fetchFederationStatus();
      setClients(res.clients);
      
      // Animate rounds appearing one by one to simulate live training
      for (let i = 0; i < res.rounds.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 400));
        setRounds(prev => [...prev, res.rounds[i]]);
      }
    } catch (err) {
      console.error(err);
      alert('Simulation failed.');
    } finally {
      setSimulating(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '24px', color: 'var(--text-secondary)' }}>Loading federation status...</div>;
  }

  // Format chart data
  const chartData = rounds.map(r => ({
    round: r.roundNo,
    federated: r.globalAccuracy ? parseFloat((r.globalAccuracy * 100).toFixed(1)) : 0,
    baseline: r.baselineAccuracy ? parseFloat((r.baselineAccuracy * 100).toFixed(1)) : 0,
  }));

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
            State Federation Network
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Cross-state predictive modelling via Federated Learning (FedProx)
          </p>
        </div>
        <button 
          onClick={handleRunSimulation} 
          disabled={simulating}
          style={{
            background: 'var(--accent-glow)',
            color: 'var(--accent-hover)',
            border: '1px solid var(--accent-border)',
            padding: '8px 16px',
            borderRadius: 'var(--radius-md)',
            cursor: simulating ? 'wait' : 'pointer',
            fontWeight: 500
          }}
        >
          {simulating ? 'Running Simulation...' : 'Run Demo Simulation'}
        </button>
      </div>

      {/* State Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px' }}>
        {clients.map(client => (
          <div key={client.id} style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--bg-glass-border)',
            borderRadius: 'var(--radius-md)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            position: 'relative',
            overflow: 'hidden'
          }}>
            {client.stateName === 'Chhattisgarh' && (
              <div style={{
                position: 'absolute',
                top: 0,
                right: 0,
                background: 'var(--status-warning)',
                color: '#fff',
                fontSize: '0.6rem',
                fontWeight: 600,
                padding: '2px 8px',
                borderBottomLeftRadius: 'var(--radius-md)'
              }}>
                COLD START
              </div>
            )}
            <div style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-primary)' }}>{client.stateName}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {client.sampleCount?.toLocaleString() || 0} samples
            </div>
            <div style={{
              marginTop: 'auto',
              display: 'inline-block',
              fontSize: '0.7rem',
              fontWeight: 500,
              padding: '4px 8px',
              borderRadius: '12px',
              background: client.status === 'Training' ? 'rgba(56, 189, 248, 0.1)' : 'rgba(52, 211, 153, 0.1)',
              color: client.status === 'Training' ? '#38bdf8' : 'var(--status-healthy)',
              width: 'max-content'
            }}>
              {client.status || 'Idle'}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Accuracy Chart */}
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--bg-glass-border)',
          borderRadius: 'var(--radius-md)',
          padding: '20px',
        }}>
          <h3 style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '24px' }}>
            Model Accuracy (FedProx vs Single-State Baseline)
          </h3>
          <div style={{ height: '280px', width: '100%' }}>
            <ResponsiveContainer>
              <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-glass-border)" vertical={false} />
                <XAxis dataKey="round" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} domain={[50, 100]} tickFormatter={(val) => `${val}%`} />
                <Tooltip 
                  contentStyle={{ background: 'var(--bg-tertiary)', border: '1px solid var(--bg-glass-border)', borderRadius: '8px' }}
                  itemStyle={{ fontSize: '0.8rem' }}
                  labelStyle={{ color: 'var(--text-secondary)', marginBottom: '4px', fontSize: '0.8rem' }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '0.8rem' }} />
                <Line type="monotone" name="Federated (FedProx)" dataKey="federated" stroke="#38bdf8" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                <Line type="monotone" name="Baseline (Single-State)" dataKey="baseline" stroke="var(--status-warning)" strokeWidth={2} strokeDasharray="5 5" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Transfer Log */}
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--bg-glass-border)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--bg-glass-border)' }}>
            <h3 style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-primary)' }}>
              Federation Transfer Log
            </h3>
          </div>
          <div style={{
            padding: '16px 20px',
            fontFamily: 'monospace',
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            background: 'rgba(0, 0, 0, 0.2)',
            flex: 1,
            overflowY: 'auto',
            maxHeight: '320px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            {rounds.length === 0 ? (
              <div style={{ opacity: 0.5 }}>Waiting for training rounds...</div>
            ) : (
              rounds.map(r => (
                <div key={r.id} style={{ display: 'flex', gap: '16px' }}>
                  <span style={{ color: 'var(--status-healthy)' }}>[Round {r.roundNo.toString().padStart(2, '0')}]</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <span style={{ color: '#e2e8f0' }}>Aggregated {r.tensorCount} tensors ({r.bytesTransferred ? Math.round(r.bytesTransferred / 1024) : 0} KB)</span>
                    <span style={{ color: 'var(--status-warning)' }}>Raw patient records transferred: {r.patientRecordsTransferred}</span>
                    <span style={{ color: 'var(--status-warning)' }}>Raw stock rows transferred: {r.stockRowsTransferred}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      
      {/* Cold-start callout */}
      <div style={{
        background: 'rgba(56, 189, 248, 0.05)',
        border: '1px solid rgba(56, 189, 248, 0.2)',
        borderRadius: 'var(--radius-md)',
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px'
      }}>
        <div style={{ color: '#38bdf8', fontSize: '1.2rem', marginTop: '-2px' }}>❄️</div>
        <div>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
            Cold-Start Transfer: Chhattisgarh
          </h4>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            State joined with only 120 samples (under 90 days history). Seasonal response curves were successfully 
            borrowed from states with similar disease profiles (Madhya Pradesh) without receiving their raw data.
          </p>
        </div>
      </div>
    </div>
  );
}
