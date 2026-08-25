import { useEffect, useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';
import { fetchForecast } from '../api/client';
import type { ForecastResponse } from '../api/client';
import { Skeleton } from './Skeleton';

interface ForecastPanelProps {
  facilityId: number;
  drugId: number;
  facilityName: string;
  drugName: string;
}

/**
 * Forecast panel — shows history line + forecast band + reorder line + stockout marker.
 * Displayed when a risk queue item is selected.
 */
export function ForecastPanel({ facilityId, drugId, facilityName, drugName }: ForecastPanelProps) {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchForecast(facilityId, drugId)
      .then(setForecast)
      .catch((err) => console.error('Failed to load forecast:', err))
      .finally(() => setLoading(false));
  }, [facilityId, drugId]);

  if (loading) {
    return (
      <div className="forecast-panel glass-card" id="forecast-panel">
        <div className="forecast-panel__header">
          <Skeleton width="250px" height="18px" />
        </div>
        <Skeleton height="200px" />
      </div>
    );
  }

  if (!forecast || (forecast.history.length === 0 && forecast.forecast.length === 0)) {
    return (
      <div className="forecast-panel glass-card" id="forecast-panel">
        <div className="forecast-panel__header">
          <span className="forecast-panel__title">{drugName}</span>
        </div>
        <div className="forecast-panel__empty">No forecast data available</div>
      </div>
    );
  }

  // Build unified chart data: history + forecast
  const chartData: Array<{
    date: string;
    label: string;
    actual?: number;
    predicted?: number;
    lower?: number;
    upper?: number;
  }> = [];

  // Take last 45 days of history to keep the chart readable
  const recentHistory = forecast.history.slice(-45);
  for (const h of recentHistory) {
    chartData.push({
      date: h.date,
      label: formatDate(h.date),
      actual: h.quantity,
    });
  }

  for (const f of forecast.forecast) {
    chartData.push({
      date: f.date,
      label: formatDate(f.date),
      predicted: f.predicted,
      lower: f.lower,
      upper: f.upper,
    });
  }

  // Driver emoji mapping
  const driverEmoji = getDriverEmoji(forecast.driver);

  return (
    <div className="forecast-panel glass-card" id="forecast-panel">
      <div className="forecast-panel__header">
        <div className="forecast-panel__title-row">
          <span className="forecast-panel__title">{drugName}</span>
          <span className="forecast-panel__driver-chip">
            {driverEmoji} {forecast.driver}
          </span>
        </div>
        <div className="forecast-panel__meta">
          <span className="forecast-panel__method">
            {forecast.methodUsed === 'croston_sba' ? 'Croston SBA' : 'SES'}
          </span>
          <span className="forecast-panel__confidence">
            Confidence: {Math.round(forecast.confidence * 100)}%
          </span>
          {forecast.daysToStockout != null && (
            <span className={`forecast-panel__stockout ${
              forecast.daysToStockout < 15 ? 'forecast-panel__stockout--critical' :
              forecast.daysToStockout < 30 ? 'forecast-panel__stockout--warning' :
              'forecast-panel__stockout--healthy'
            }`}>
              {Math.round(forecast.daysToStockout)}d to stockout
            </span>
          )}
        </div>
      </div>

      <div className="forecast-panel__chart">
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.06)"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              width={35}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--surface-glass)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 8,
                backdropFilter: 'blur(12px)',
                color: 'var(--text-primary)',
                fontSize: '0.75rem',
              }}
              labelStyle={{ color: 'var(--text-muted)', marginBottom: 4 }}
            />

            {/* Forecast confidence band */}
            <Area
              dataKey="upper"
              stroke="none"
              fill="rgba(99, 179, 237, 0.15)"
              fillOpacity={1}
              isAnimationActive={false}
            />
            <Area
              dataKey="lower"
              stroke="none"
              fill="var(--bg-primary)"
              fillOpacity={1}
              isAnimationActive={false}
            />

            {/* History line */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="var(--accent)"
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />

            {/* Forecast line */}
            <Line
              type="monotone"
              dataKey="predicted"
              stroke="#63b3ed"
              strokeWidth={2}
              strokeDasharray="6 3"
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />

            {/* Reorder point line */}
            <ReferenceLine
              y={forecast.reorderPoint}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{
                value: `Reorder: ${Math.round(forecast.reorderPoint)}`,
                position: 'right',
                fill: '#f59e0b',
                fontSize: 10,
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="forecast-panel__legend">
        <span className="forecast-panel__legend-item">
          <span className="forecast-panel__legend-line" style={{ background: 'var(--accent)' }} />
          History
        </span>
        <span className="forecast-panel__legend-item">
          <span className="forecast-panel__legend-line forecast-panel__legend-line--dashed" style={{ background: '#63b3ed' }} />
          Forecast
        </span>
        <span className="forecast-panel__legend-item">
          <span className="forecast-panel__legend-band" />
          Confidence band
        </span>
        <span className="forecast-panel__legend-item">
          <span className="forecast-panel__legend-line forecast-panel__legend-line--dashed" style={{ background: '#f59e0b' }} />
          Reorder point
        </span>
      </div>
    </div>
  );
}


function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getDate()}/${d.getMonth() + 1}`;
}

function getDriverEmoji(driver: string): string {
  const lower = driver.toLowerCase();
  if (lower.includes('dengue') || lower.includes('malaria')) return '🦟';
  if (lower.includes('diarrhoeal') || lower.includes('diarrhoe')) return '💧';
  if (lower.includes('respiratory')) return '🫁';
  if (lower.includes('seasonal')) return '📅';
  if (lower.includes('tuberculosis')) return '🫁';
  return '📊';
}
