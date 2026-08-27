import { useState } from 'react';
import { fireScenario, resetDemo, simulateTwin } from '../api/client';
import type { TwinSimulateResponse, TwinSimulateRequest } from '../api/client';

interface ScenarioRunnerProps {
  onScenarioFired: () => void;
  onTwinResult?: (res: TwinSimulateResponse | null) => void;
  onModeChange?: (mode: 'macro' | 'micro') => void;
}

const CONDITIONS = [
  { value: 'dengue', label: 'Dengue' },
  { value: 'malaria', label: 'Malaria' },
  { value: 'diarrhoeal', label: 'Diarrhoeal' },
  { value: 'respiratory_infection', label: 'Respiratory Infection' },
  { value: 'tuberculosis', label: 'Tuberculosis' },
];

export function ScenarioRunner({ onScenarioFired, onTwinResult, onModeChange }: ScenarioRunnerProps) {
  const [condition, setCondition] = useState('dengue');
  const [multiplier, setMultiplier] = useState(3);
  const [mode, setMode] = useState<'macro' | 'micro'>('macro');
  const [firing, setFiring] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleModeSwitch = (newMode: 'macro' | 'micro') => {
    if (mode === newMode) return; // Prevent double-clicks

    setMode(newMode);
    if (onModeChange) onModeChange(newMode);

    // Unconditionally trigger a full reset when switching modes.
    // This clears the Macro results (onTwinResult(null)) AND wipes the DB
    // (resetDemo()), guaranteeing a perfectly clean "normal" state.
    handleReset();
  };

  const handleFire = async () => {
    setFiring(true);
    setResult(null);
    try {
      if (mode === 'micro') {
        const res = await fireScenario({
          condition,
          multiplier,
          district: 'Dhar',
        });
        setResult(`🔥 ${res.condition} outbreak injected (${res.multiplier}×) — DB altered.`);
        if (onTwinResult) onTwinResult(null);
        onScenarioFired();
      } else {
        const req: TwinSimulateRequest = { condition, multiplier, district: 'Dhar' };
        const res = await simulateTwin(req);
        setResult(`📊 Prediction complete: ${res.counterfactualImpact.stockoutDaysPrevented} stockout days preventable.`);
        if (onTwinResult) onTwinResult(res);
      }
    } catch (err) {
      setResult(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setFiring(false);
    }
  };

  const handleReset = async () => {
    setResetting(true);
    setResult(null);
    if (onTwinResult) onTwinResult(null);
    try {
      await resetDemo();
      setResult('✓ Base state restored');
      onScenarioFired();
    } catch (err) {
      setResult(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="scenario-runner" id="scenario-runner">
      <div className="scenario-runner__header">
        <span className="scenario-runner__icon">⚡</span>
        Outbreak Scenario
      </div>

      <div className="scenario-runner__controls">
        
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', background: 'var(--bg-dark)', padding: '4px', borderRadius: '6px' }}>
          <button 
            style={{ flex: 1, padding: '6px', borderRadius: '4px', border: 'none', background: mode === 'macro' ? 'var(--accent)' : 'transparent', color: mode === 'macro' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer' }}
            onClick={() => handleModeSwitch('macro')}
          >
            Predict (Macro)
          </button>
          <button 
            style={{ flex: 1, padding: '6px', borderRadius: '4px', border: 'none', background: mode === 'micro' ? 'var(--critical)' : 'transparent', color: mode === 'micro' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer' }}
            onClick={() => handleModeSwitch('micro')}
          >
            Inject (Micro)
          </button>
        </div>

        <div className="scenario-runner__field">
          <label className="scenario-runner__label" htmlFor="scenario-condition">Condition</label>
          <select
            id="scenario-condition"
            className="scenario-runner__select"
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            disabled={firing}
          >
            {CONDITIONS.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        <div className="scenario-runner__field">
          <label className="scenario-runner__label" htmlFor="scenario-multiplier">
            Surge: {multiplier}×
          </label>
          <input
            id="scenario-multiplier"
            type="range"
            className="scenario-runner__slider"
            min={2}
            max={5}
            step={0.5}
            value={multiplier}
            onChange={(e) => setMultiplier(Number(e.target.value))}
            disabled={firing}
          />
          <div className="scenario-runner__range-labels">
            <span>2×</span>
            <span>5×</span>
          </div>
        </div>

        <div className="scenario-runner__actions">
          <button
            id="scenario-fire-btn"
            className="scenario-runner__btn scenario-runner__btn--fire"
            onClick={handleFire}
            disabled={firing || resetting}
            style={mode === 'macro' ? { background: 'var(--accent)' } : undefined}
          >
            {firing ? 'Processing…' : (mode === 'macro' ? 'Run Simulation' : '🔥 Inject Outbreak')}
          </button>
          <button
            id="scenario-reset-btn"
            className="scenario-runner__btn scenario-runner__btn--reset"
            onClick={handleReset}
            disabled={firing || resetting}
          >
            {resetting ? 'Resetting…' : '↺ Reset'}
          </button>
        </div>
      </div>

      {result && (
        <div className={`scenario-runner__result ${result.startsWith('Error') ? 'scenario-runner__result--error' : ''}`} style={{ fontSize: '0.85rem' }}>
          {result}
        </div>
      )}
    </div>
  );
}
