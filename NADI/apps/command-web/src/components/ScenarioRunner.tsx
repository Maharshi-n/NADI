import { useState } from 'react';
import { fireScenario, resetDemo } from '../api/client';

interface ScenarioRunnerProps {
  onScenarioFired: () => void;
}

const CONDITIONS = [
  { value: 'dengue', label: 'Dengue' },
  { value: 'malaria', label: 'Malaria' },
  { value: 'diarrhoeal', label: 'Diarrhoeal' },
  { value: 'respiratory_infection', label: 'Respiratory Infection' },
  { value: 'tuberculosis', label: 'Tuberculosis' },
];

/**
 * Scenario runner — fire outbreak scenarios and reset.
 * Phase 2: "Run outbreak scenario" wired to the demo endpoint.
 */
export function ScenarioRunner({ onScenarioFired }: ScenarioRunnerProps) {
  const [condition, setCondition] = useState('dengue');
  const [multiplier, setMultiplier] = useState(3);
  const [firing, setFiring] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleFire = async () => {
    setFiring(true);
    setResult(null);
    try {
      const res = await fireScenario({
        condition,
        multiplier,
        district: 'Dhar',
      });
      setResult(`🔥 ${res.condition} outbreak (${res.multiplier}×) — ${res.affected} facilities affected`);
      onScenarioFired();
    } catch (err) {
      setResult(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setFiring(false);
    }
  };

  const handleReset = async () => {
    setResetting(true);
    setResult(null);
    try {
      await resetDemo();
      setResult('✓ Seed state restored');
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
          >
            {firing ? 'Injecting…' : '🔥 Fire Outbreak'}
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
        <div className={`scenario-runner__result ${result.startsWith('Error') ? 'scenario-runner__result--error' : ''}`}>
          {result}
        </div>
      )}
    </div>
  );
}
