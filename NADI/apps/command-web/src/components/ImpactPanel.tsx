import type { PlanImpact } from '../api/client';

export function ImpactPanel({ impact }: { impact: PlanImpact }) {
  return (
    <div className="panel" style={{ padding: '16px', background: 'var(--bg-card)' }}>
      <h3 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Projected Impact</h3>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Breaches */}
        <div style={{ background: 'var(--bg-glass)', padding: '12px', borderRadius: 'var(--radius-md)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Stockout Breaches</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '4px' }}>
            <span style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-muted)', textDecoration: 'line-through' }}>
              {impact.breachesBefore}
            </span>
            <span style={{ fontSize: '1.2rem', color: 'var(--text-secondary)' }}>→</span>
            <span style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--healthy)' }}>
              {impact.breachesAfter}
            </span>
          </div>
        </div>

        {/* Cost & Savings */}
        <div style={{ background: 'var(--bg-glass)', padding: '12px', borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Transfer Cost</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--warning)' }}>
              Rs. {(impact.totalCostPaise / 100).toFixed(2)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Expiry Saved</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--healthy)' }}>
              Rs. {(impact.expiryAvoidedPaise / 100).toFixed(2)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
