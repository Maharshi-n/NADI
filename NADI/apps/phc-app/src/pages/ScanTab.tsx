import { useState } from 'react';
import { Camera, Check, Upload, AlertTriangle, X } from 'lucide-react';
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
    // Only process valid rows
    const validRows = results.filter(r => r.drugId !== null);
    
    // Save to backend or local indexeddb
    try {
      const res = await fetch('/api/scan/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows: validRows })
      });
      if (!res.ok) throw new Error('Confirmation failed');
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
                    <div>
                      {isValid ? (
                        <h4 className="font-bold text-gray-100">{row.matchedName}</h4>
                      ) : (
                        <h4 className="font-bold text-danger">Unrecognized Drug</h4>
                      )}
                      <p className="text-xs text-gray-400 font-mono mt-1">Raw text: "{row.rawText}"</p>
                    </div>
                    {hasUncertainty && (
                      <AlertTriangle className="w-5 h-5 text-warning shrink-0" />
                    )}
                  </div>
                  
                  {isValid && (
                    <div className="grid grid-cols-2 gap-2 text-sm mt-3 pt-3 border-t border-gray-800/50">
                      <div>
                        <span className="text-gray-500 text-xs uppercase block">Qty</span>
                        <span className={row.uncertainFields.includes('quantity') ? 'text-warning' : 'text-gray-200'}>
                          {row.quantity}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 text-xs uppercase block">Batch</span>
                        <span className={row.uncertainFields.includes('batchNo') ? 'text-warning' : 'text-gray-200'}>
                          {row.batchNo}
                        </span>
                      </div>
                      <div className="col-span-2 mt-1">
                        <span className="text-gray-500 text-xs uppercase block">Expiry</span>
                        <span className={row.uncertainFields.includes('expiryDate') ? 'text-warning' : 'text-gray-200'}>
                          {row.expiryDate}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <button 
            onClick={confirmRows}
            disabled={!results.some(r => r.drugId !== null)}
            className="w-full py-3 mt-4 bg-success text-white font-bold rounded-xl flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <Check className="w-5 h-5" />
            <span>Confirm & Update Stock</span>
          </button>
        </div>
      )}
    </div>
  );
}
