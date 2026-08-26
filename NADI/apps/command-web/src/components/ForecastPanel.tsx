import { useEffect, useState } from 'react';
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer
} from 'recharts';
import { fetchForecast } from '../api/client';
import type { ForecastResponse } from '../api/client';

interface ForecastPanelProps {
  facilityId: number;
  drugId: number;
  facilityName: string;
  drugName: string;
  onClose?: () => void;
}

/**
 * Forecast panel — history line + forecast band + reorder line + stockout marker.
 * Phase 2: the chart that shows the future.
 */
export function ForecastPanel({ facilityId, drugId, facilityName, drugName, onClose }: ForecastPanelProps) {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchForecast({ facilityId, drugId })
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [facilityId, drugId]);

  if (loading) {
    return (
      <div className="forecast-panel" id="forecast-panel">
        <div className="forecast-panel__header">
          <div className="forecast-panel__title-row" style={{ justifyContent: 'space-between' }}>
            <span className="forecast-panel__title">Forecast</span>
            {onClose && (
              <button className="forecast-panel__close" onClick={onClose} aria-label="Close">
                ✕
              </button>
            )}
          </div>
        </div>
        <div className="forecast-panel__loading">
          <div className="skeleton skeleton--chart" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="forecast-panel" id="forecast-panel">
        <div className="forecast-panel__header">
          <div className="forecast-panel__title-row" style={{ justifyContent: 'space-between' }}>
            <span className="forecast-panel__title">Forecast</span>
            {onClose && (
              <button className="forecast-panel__close" onClick={onClose} aria-label="Close">
                ✕
              </button>
            )}
          </div>
        </div>
        <div className="forecast-panel__empty">
          {error || 'No forecast data available'}
        </div>
      </div>
    );
  }

  // Build unified chart data: history + forecast
  const chartData = [
    ...data.history.map((h) => ({
      date: h.date,
      actual: h.quantity,
      predicted: null as number | null,
      lower: null as number | null,
      upper: null as number | null,
    })),
    // Bridge point: last history connects to first forecast
    ...(data.history.length > 0 && data.forecast.length > 0
      ? [{
          date: data.forecast[0].date,
          actual: null as number | null,
          predicted: data.forecast[0].predicted,
          lower: data.forecast[0].lower,
          upper: data.forecast[0].upper,
        }]
      : []),
    ...data.forecast.slice(1).map((f) => ({
      date: f.date,
      actual: null as number | null,
      predicted: f.predicted,
      lower: f.lower,
      upper: f.upper,
    })),
  ];

  // Format date for axis
  const formatDate = (dateStr: any) => {
    const d = new Date(dateStr);
    return `${d.getDate()}/${d.getMonth() + 1}`;
  };

  const confidencePct = Math.round(data.confidence * 100);
  const methodLabel = data.methodUsed === 'croston_sba' ? 'Croston SBA' : 'Exp. Smoothing';

  return (
    <div className="forecast-panel" id="forecast-panel">
      <div className="forecast-panel__header">
        <div className="forecast-panel__title-row" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className="forecast-panel__title">
              Forecast — {drugName}
            </span>
            <span className="forecast-panel__driver-chip">{data.driver}</span>
          </div>
          {onClose && (
            <button className="forecast-panel__close" onClick={onClose} aria-label="Close">
              ✕
            </button>
          )}
        </div>
        <div className="forecast-panel__meta">
          <span className="forecast-panel__method-badge">{methodLabel}</span>
          <span className="forecast-panel__confidence">
            Confidence: <strong>{confidencePct}%</strong>
          </span>
          {data.daysToStockout != null && (
            <span className={`forecast-panel__stockout ${data.daysToStockout < 15 ? 'forecast-panel__stockout--critical' : data.daysToStockout < 30 ? 'forecast-panel__stockout--warning' : ''}`}>
              Stockout in {Math.round(data.daysToStockout)} days
            </span>
          )}
        </div>
      </div>

      <div className="forecast-panel__chart">
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 16, bottom: 4, left: 0 }}>
            <defs>
              <linearGradient id="forecastBand" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.25} />
                <stop offset="100%" stopColor="var(--accent)" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              stroke="var(--text-muted)"
              fontSize={11}
              interval="preserveStartEnd"
              tickCount={8}
            />
            <YAxis stroke="var(--text-muted)" fontSize={11} width={40} />
            <Tooltip
              contentStyle={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--bg-glass-border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: '0.8rem',
              }}
              labelFormatter={formatDate}
            />

            {/* Forecast confidence band */}
            <Area
              type="monotone"
              dataKey="upper"
              stroke="none"
              fill="url(#forecastBand)"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="lower"
              stroke="none"
              fill="var(--bg-primary)"
              isAnimationActive={false}
            />

            {/* Forecast line */}
            <Line
              type="monotone"
              dataKey="predicted"
              stroke="var(--accent)"
              strokeWidth={2}
              strokeDasharray="6 3"
              dot={false}
              isAnimationActive={false}
            />

            {/* History line */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="var(--text-primary)"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />

            {/* Reorder line */}
            <ReferenceLine
              y={data.reorderPoint}
              stroke="var(--warning)"
              strokeDasharray="4 4"
              label={{
                value: `Reorder: ${data.reorderPoint}`,
                position: 'right',
                fill: 'var(--warning)',
                fontSize: 10,
              }}
            />

            {/* Stockout marker */}
            {data.stockoutDate && (
              <ReferenceLine
                x={data.stockoutDate}
                stroke="var(--critical)"
                strokeWidth={2}
                label={{
                  value: 'Stockout',
                  position: 'top',
                  fill: 'var(--critical)',
                  fontSize: 10,
                }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="forecast-panel__footer">
        <span>Facility: {facilityName}</span>
        {data.stockoutDate && (
          <span className="forecast-panel__stockout-date">
            Projected stockout: {data.stockoutDate}
          </span>
        )}
      </div>
    </div>
  );
}
