import { useState } from 'react';
import type { TransferProposalItem } from '../api/client';

interface TransferTableProps {
  transfers: TransferProposalItem[];
  onApprove: (selectedIds: number[]) => void;
  isApproving: boolean;
}

export function TransferTable({ transfers, onApprove, isApproving }: TransferTableProps) {
  // Store indices of selected transfers
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelected(new Set(transfers.map((_, i) => i)));
    } else {
      setSelected(new Set());
    }
  };

  const handleSelectOne = (index: number, checked: boolean) => {
    const newSet = new Set(selected);
    if (checked) {
      newSet.add(index);
    } else {
      newSet.delete(index);
    }
    setSelected(newSet);
  };

  const handleApprove = () => {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    onApprove(ids);
    setSelected(new Set()); // Clear selection after approve attempt
  };

  const handleApproveAll = () => {
    const allIds = transfers.map((_, i) => i);
    onApprove(allIds);
    setSelected(new Set());
  };

  return (
    <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--bg-card)', padding: '16px', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ fontSize: '1.1rem' }}>Proposed Transfers</h3>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          {transfers.length} total
        </span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', marginBottom: '16px', border: '1px solid var(--bg-glass-border)', borderRadius: 'var(--radius-md)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead style={{ background: 'var(--bg-glass)', position: 'sticky', top: 0, zIndex: 1 }}>
            <tr>
              <th style={{ padding: '10px 8px', textAlign: 'left', borderBottom: '1px solid var(--bg-glass-border)' }}>
                <input 
                  type="checkbox" 
                  checked={transfers.length > 0 && selected.size === transfers.length}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                />
              </th>
              <th style={{ padding: '10px 8px', textAlign: 'left', borderBottom: '1px solid var(--bg-glass-border)' }}>Route</th>
              <th style={{ padding: '10px 8px', textAlign: 'left', borderBottom: '1px solid var(--bg-glass-border)' }}>Item</th>
              <th style={{ padding: '10px 8px', textAlign: 'right', borderBottom: '1px solid var(--bg-glass-border)' }}>Qty</th>
              <th style={{ padding: '10px 8px', textAlign: 'right', borderBottom: '1px solid var(--bg-glass-border)' }}>Dist.</th>
            </tr>
          </thead>
          <tbody>
            {transfers.length === 0 && (
              <tr>
                <td colSpan={5} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No transfers proposed or all approved.
                </td>
              </tr>
            )}
            {transfers.map((t, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid var(--bg-glass-border)', background: selected.has(idx) ? 'var(--bg-glass)' : 'transparent' }}>
                <td style={{ padding: '10px 8px' }}>
                  <input 
                    type="checkbox" 
                    checked={selected.has(idx)}
                    onChange={(e) => handleSelectOne(idx, e.target.checked)}
                  />
                </td>
                <td style={{ padding: '10px 8px' }}>
                  <div style={{ fontWeight: 500 }}>{t.fromName}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>↓ {t.distanceKm} km</div>
                  <div style={{ fontWeight: 500 }}>{t.toName}</div>
                </td>
                <td style={{ padding: '10px 8px' }}>
                  <div>{t.drugName}</div>
                  {t.isColdChain && <div style={{ fontSize: '0.7rem', color: '#38bdf8', marginTop: '2px' }}>❄️ Cold Chain</div>}
                  <div style={{ fontSize: '0.75rem', color: 'var(--healthy)', marginTop: '2px' }}>
                    +{t.coverRestoredDays}d cover
                  </div>
                </td>
                <td style={{ padding: '10px 8px', textAlign: 'right', fontWeight: 600 }}>
                  {t.quantity} <span style={{ fontSize: '0.75rem', fontWeight: 400, color: 'var(--text-secondary)' }}>{t.unit}</span>
                </td>
                <td style={{ padding: '10px 8px', textAlign: 'right', color: 'var(--text-secondary)' }}>
                  {t.distanceKm}km
                  <div style={{ fontSize: '0.75rem', color: 'var(--warning)', marginTop: '2px' }}>
                    Rs. {(t.costPaise / 100).toFixed(2)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'flex', gap: '12px' }}>
        <button 
          className="btn-primary" 
          disabled={selected.size === 0 || isApproving}
          onClick={handleApprove}
          style={{ flex: 1, padding: '10px' }}
        >
          {isApproving ? 'Approving...' : `Approve Selected (${selected.size})`}
        </button>
        <button 
          onClick={handleApproveAll}
          disabled={transfers.length === 0 || isApproving}
          style={{ 
            flex: 1, 
            padding: '10px', 
            background: 'transparent', 
            border: '1px solid var(--accent)', 
            color: 'var(--accent)',
            borderRadius: 'var(--radius-md)',
            cursor: transfers.length === 0 ? 'not-allowed' : 'pointer',
            opacity: transfers.length === 0 ? 0.5 : 1
          }}
        >
          Approve All
        </button>
      </div>

      <div style={{ marginTop: '16px', fontSize: '0.75rem', textAlign: 'center', color: 'var(--warning)' }}>
        ⚠️ Requires CMHO sign-off — nothing ships automatically
      </div>
    </div>
  );
}
