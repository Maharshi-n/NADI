import { useState } from 'react';
import { Search } from 'lucide-react';
import { useLiveQuery } from 'dexie-react-hooks';
import { db } from '../db/db';

export function StockTab() {
  const [search, setSearch] = useState('');
  
  // Use indexeddb data, but if empty, show a mock for demonstration
  const stockItems = useLiveQuery(() => db.stock.toArray(), []) || [];
  
  const displayItems = stockItems.length > 0 ? stockItems : [
    { drugId: 1, name: 'Paracetamol 500mg', quantity: 1200, unit: 'tab', daysOfCover: 45, status: 'healthy', expiryDate: '2027-01-01' },
    { drugId: 2, name: 'Amoxicillin 250mg', quantity: 45, unit: 'cap', daysOfCover: 12, status: 'critical', expiryDate: '2026-10-15' },
    { drugId: 3, name: 'ORS Sachet', quantity: 300, unit: 'sachet', daysOfCover: 22, status: 'warning', expiryDate: '2027-05-20' },
  ];

  const filtered = displayItems.filter(i => (i.name || '').toLowerCase().includes((search || '').toLowerCase()));

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input 
          type="text" 
          placeholder="Search stock..." 
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-surface border border-gray-700 rounded-xl pl-10 pr-4 py-3 focus:outline-none focus:border-primary text-gray-100 placeholder-gray-500 transition-colors"
        />
      </div>

      <div className="space-y-3">
        {filtered.map(item => (
          <div key={item.drugId} className="bg-surface p-4 rounded-xl border border-gray-800 flex justify-between items-center">
            <div>
              <h3 className="font-semibold">{item.name}</h3>
              <p className="text-sm text-gray-400 mt-1">{item.quantity} {item.unit} • Expires {item.expiryDate}</p>
            </div>
            <div className="flex flex-col items-end">
              <span className={`px-2.5 py-1 rounded-full text-xs font-semibold mb-2 ${
                item.status === 'critical' ? 'bg-danger/20 text-danger border border-danger/30' :
                item.status === 'warning' ? 'bg-warning/20 text-warning border border-warning/30' :
                'bg-success/20 text-success border border-success/30'
              }`}>
                {item.daysOfCover === 999 ? '> 90' : Math.round(item.daysOfCover)} days
              </span>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="text-center p-8 text-gray-500">
            No stock items found.
          </div>
        )}
      </div>
    </div>
  );
}
