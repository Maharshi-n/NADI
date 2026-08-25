import { useState } from 'react';
import { fireScenario, resetDemo } from '../api/client';
import type { ScenarioResponse } from '../api/client';

interface ScenarioRunnerProps {
  onScenarioChange: () => void;
}

const CONDITIONS = [
  { value: 'dengue', label: 'Dengue', emoji: '🦟' },
  { value: 'malaria', label: 'Malaria', emoji: '🦟' },
  { value: 'diarrhoeal', label: 'Diarrhoeal', emoji: '💧' },
  { value: 'respiratory_infection', label: 'Respiratory', emoji: '🫁' },
  { value: 'tuberculosis', label: 'TB', emoji: '🫁' },
];

/**
 * Scenario runner — "Run outbreak scenario" controls.
 * Fires POST /api/demo/scenario with the selected condition and multiplier,
 * then triggers a data reload via onScenarioChange callback.
 */
export function ScenarioRunner({ onScenarioChange }: ScenarioRunnerProps) {
  const [condition, setCondition] = useState('dengue');
  const [multiplier, setMultiplier] = useState(3);
  const [firing, setFiring] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [result, setResult] = useState<ScenarioResponse | null>(null);
  const [isActive, setIsActive] = useState(false);

  const handleFire = async () => {
    setFiring(true);
    setResult(null);
    try {
      const res = await fireScenario({ condition, multiplier });
      setResult(res);
      setIsActive(true);
      onScenarioChange();
    } catch (err) {
      console.error('Scenario failed:', err);
    } finally {
      setFiring(false);
    }
  };

  const handleReset = async () => {
    setResetting(true);
    setResult(null);
    try {
      const res = await resetDemo();
      setResult(res);
      setIsActive(false);
      onScenarioChange();
    } catch (err) {
      console.error('Reset failed:', err);
    } finally {
      setResetting(false);
    }
  };

  const selectedEmoji = CONDITIONS.find(c => c.value === condition)?.emoji || '🦠';

  return (
    <div className="scenario-runner glass-card" id="scenario-runner">
      <div className="scenario-runner__header">
        <span className="scenario-runner__title">
          {selectedEmoji} Outbreak Scenario
        </span>
        {isActive && (
          <span className="scenario-runner__active-badge">ACTIVE</span>
        )}
      </div>

      <div className="scenario-runner__controls">
        <div className="scenario-runner__row">
          <label className="scenario-runner__label">Condition</label>
          <select
            className="scenario-runner__select"
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            id="scenario-condition"
          >
            {CONDITIONS.map(c => (
              <option key={c.value} value={c.value}>
                {c.emoji} {c.label}
              </option>
            ))}
          </select>
        </div>

        <div className="scenario-runner__row">
          <label className="scenario-runner__label">
            Multiplier: {multiplier}×
          </label>
          <input
            type="range"
            className="scenario-runner__slider"
            min={2}
            max={5}
            step={0.5}
            value={multiplier}
            onChange={(e) => setMultiplier(parseFloat(e.target.value))}
            id="scenario-multiplier"
          />
        </div>

        <div className="scenario-runner__actions">
          <button
            className="scenario-runner__btn scenario-runner__btn--fire"
            onClick={handleFire}
            disabled={firing || resetting}
            id="scenario-fire"
          >
            {firing ? (
              <span className="scenario-runner__spinner" />
            ) : (
              '🔥 Fire Outbreak'
            )}
          </button>
          <button
            className="scenario-runner__btn scenario-runner__btn--reset"
            onClick={handleReset}
            disabled={firing || resetting || !isActive}
            id="scenario-reset"
          >
            {resetting ? (
              <span className="scenario-runner__spinner" />
            ) : (
              '↺ Reset'
            )}
          </button>
        </div>
      </div>

      {result && (
        <div className={`scenario-runner__result ${isActive ? 'scenario-runner__result--active' : 'scenario-runner__result--reset'}`}>
          {result.message}
          {isActive && result.affectedFacilities > 0 && (
            <span className="scenario-runner__affected">
              {result.affectedFacilities} facilities affected
            </span>
          )}
        </div>
      )}
    </div>
  );
}
