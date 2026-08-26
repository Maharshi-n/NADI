import { useState } from 'react';
import { Camera, Check, Upload, AlertTriangle, X } from 'lucide-react';
import { useLiveQuery } from 'dexie-react-hooks';
import { db } from '../db/db';

interface ScannedRow {
  drugId: number | null;
  matchedName: string | null;
  rawText: string;
  batchNo: string;
  quantity: number;
  expiryDate: string;
  confidence: number;
  uncertainFields: string[];
}

export function ScanTab() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [results, setResults] = useState<ScannedRow[] | null>(null);
  const [editingRowIndex, setEditingRowIndex] = useState<number | null>(null);

  const stockItems = useLiveQuery(() => db.stock.toArray(), []) || [];
  const masterDrugs = stockItems.length > 0 ? stockItems : [
    { drugId: 1, name: 'Paracetamol 500mg' },
    { drugId: 2, name: 'Amoxicillin 250mg' },
    { drugId: 3, name: 'ORS Sachet' },
  ];

  const updateRow = (index: number, field: keyof ScannedRow, value: any) => {
    if (!results) return;
    const newResults = [...results];
    newResults[index] = { ...newResults[index], [field]: value };
    setResults(newResults);
  };

  const handleNameChange = (index: number, newName: string) => {
    if (!results) return;
    const newResults = [...results];
    const drug = masterDrugs.find(d => d.name.toLowerCase() === newName.toLowerCase());
    if (drug) {
      newResults[index].drugId = drug.drugId;
      newResults[index].matchedName = drug.name;
    } else {
      newResults[index].drugId = null;
      newResults[index].matchedName = newName;
    }
    setResults(newResults);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setResults(null);
    }
  };

  const scanDocument = async () => {
    if (!file) return;
    setIsScanning(true);
    try {
      const formData = new FormData();
      formData.append('image', file);

      const res = await fetch('/api/scan', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Scan failed');
      }
      const data = await res.json();
      setResults(data.rows);
    } catch (err: any) {
      console.error(err);
      alert(`Failed to scan document: ${err.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  const confirmRows = async () => {
    if (!results) return;
    const validRows = results
      .filter(r => r.drugId !== null || (r.matchedName ?? r.rawText))
      .map(r => ({
        ...r,
        matchedName: r.matchedName ?? r.rawText
      }));

    
    // Save to backend or local indexeddb
    try {
      const res = await fetch('/api/scan/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows: validRows })
      });
      if (!res.ok) throw new Error('Confirmation failed');
      
      // Update local db.stock from backend so the Stock tab updates
      const { fetchStockFromServer } = await import('../services/sync');
      await fetchStockFromServer();

      alert('Stock updated successfully!');
      setFile(null);
      setPreview(null);
      setResults(null);
    } catch (err) {
      console.error(err);
      alert('Failed to confirm rows');
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold">Register Scan</h2>
        <p className="text-gray-400">Capture a paper register to ingest stock</p>
      </div>

      {!preview ? (
        <div className="relative border-2 border-dashed border-gray-700 rounded-2xl p-10 flex flex-col items-center justify-center bg-surface/50 hover:bg-surface transition-colors">
          <input 
            type="file" 
            accept="image/*" 
            capture="environment"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={handleFileChange}
          />
          <Camera className="w-12 h-12 text-primary mb-4" />
          <span className="font-semibold text-lg">Tap to Capture</span>
          <span className="text-sm text-gray-400 mt-1">or select from gallery</span>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="relative rounded-xl overflow-hidden border border-gray-800">
            <img src={preview} alt="Document Preview" className="w-full h-48 object-cover" />
            <button 
              onClick={() => { setPreview(null); setFile(null); setResults(null); }}
              className="absolute top-2 right-2 bg-black/50 p-2 rounded-full text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          {!results && (
            <button 
              onClick={scanDocument}
              disabled={isScanning}
              className="w-full py-3 bg-primary text-white font-bold rounded-xl flex items-center justify-center space-x-2 disabled:opacity-70"
            >
              {isScanning ? (
                <>
                  <span className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"></span>
                  Processing with Gemini...
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  <span>Analyze Document</span>
                </>
              )}
            </button>
          )}
        </div>
      )}

      {results && (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4">
          <div className="flex justify-between items-end">
            <h3 className="font-bold text-lg">Extracted Rows</h3>
            <span className="text-sm text-gray-400">{results.length} items found</span>
          </div>
          
          <div className="space-y-3">
            {results.map((row, idx) => {
              const isValid = row.drugId !== null;
              const hasUncertainty = row.uncertainFields.length > 0;
              
              return (
                <div key={idx} className={`p-4 rounded-xl border ${isValid ? (hasUncertainty ? 'bg-warning/10 border-warning/30' : 'bg-surface border-gray-800') : 'bg-danger/10 border-danger/30'}`}>
                  <div className="flex justify-between items-start mb-2">
                    <div className="w-full mr-2">
                      <div 
                        className={`cursor-pointer w-full font-bold border rounded-md py-2 px-3 focus:outline-none transition-colors ${
                          isValid 
                            ? 'bg-surface-lighter text-gray-100 border-gray-700 hover:border-gray-500' 
                            : 'bg-danger/20 text-danger border-danger/50 hover:border-danger'
                        }`}
                        onClick={() => setEditingRowIndex(idx)}
                      >
                        {row.matchedName ?? row.rawText ?? 'Medicine Name'}
                        {!isValid && (
                          <span className="ml-2 text-xs opacity-90 font-bold px-2 py-0.5 rounded-full bg-danger/20 text-danger border border-danger/50">
                            UNRECOGNIZED DRUG
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 font-mono mt-1">Raw text: "{row.rawText}"</p>
                    </div>
                    {hasUncertainty && (
                      <AlertTriangle className="w-5 h-5 text-warning shrink-0 mt-1" />
                    )}
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm mt-3 pt-3 border-t border-gray-800/50">
                    <div>
                      <span className="text-gray-500 text-xs uppercase block mb-1">Qty</span>
                      <input 
                        type="number"
                        className={`w-full bg-transparent border-b border-gray-700 pb-1 focus:border-primary focus:outline-none ${row.uncertainFields.includes('quantity') ? 'text-warning font-bold' : 'text-gray-200'}`}
                        value={row.quantity}
                        onChange={(e) => updateRow(idx, 'quantity', parseInt(e.target.value) || 0)}
                      />
                    </div>
                    <div>
                      <span className="text-gray-500 text-xs uppercase block mb-1">Expiry (YYYY-MM-DD)</span>
                      <input 
                        type="text"
                        placeholder="2027-01-01"
                        className={`w-full bg-transparent border-b border-gray-700 pb-1 focus:border-primary focus:outline-none ${row.uncertainFields.includes('expiryDate') ? 'text-warning font-bold' : 'text-gray-200'}`}
                        value={row.expiryDate || ""}
                        onChange={(e) => updateRow(idx, 'expiryDate', e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <button 
            onClick={confirmRows}
            disabled={!results.some(r => r.drugId !== null || (r.matchedName ?? r.rawText))}
            className="w-full py-3 mt-4 bg-success text-white font-bold rounded-xl flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <Check className="w-5 h-5" />
            <span>Confirm & Update Stock</span>
          </button>
        </div>
      )}

      {/* Edit Medicine Name Modal */}
      {editingRowIndex !== null && results && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-surface border border-gray-700 rounded-xl w-full max-w-sm overflow-hidden flex flex-col shadow-2xl">
            <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-surface-lighter">
              <h3 className="font-bold">Edit Medicine Name</h3>
              <button onClick={() => setEditingRowIndex(null)} className="p-1 rounded-full hover:bg-gray-700 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="text-xs text-gray-400 uppercase font-semibold mb-2 block">Detected Text</label>
                <div className="bg-gray-900 px-3 py-2 rounded-lg font-mono text-sm border border-gray-800">
                  {results[editingRowIndex].rawText}
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 uppercase font-semibold mb-2 block">Map to Drug</label>
                <div className="relative">
                  <input 
                    type="text"
                    list="modal-drugs-datalist"
                    value={results[editingRowIndex].matchedName ?? results[editingRowIndex].rawText ?? ''}
                    onChange={(e) => handleNameChange(editingRowIndex, e.target.value)}
                    placeholder="Type to search or add new..."
                    className="w-full font-bold bg-gray-900 border border-gray-600 rounded-lg py-3 px-3 focus:outline-none focus:border-primary text-white placeholder-gray-500"
                    autoFocus
                  />
                  <datalist id="modal-drugs-datalist">
                    {masterDrugs.map(d => (
                      <option key={d.drugId} value={d.name} />
                    ))}
                  </datalist>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Select an existing medicine from the list, or type a new name to add it to the database.
                </p>
              </div>
            </div>
            <div className="p-4 border-t border-gray-800 bg-surface-lighter">
              <button 
                onClick={() => setEditingRowIndex(null)}
                className="w-full py-3 bg-primary text-white font-bold rounded-xl flex justify-center items-center"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
