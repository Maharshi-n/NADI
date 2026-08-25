"""
NADI Forecasting Engine — Phase 2.

Computes predicted demand rates for every facility-drug pair using:
  - SES (Simple Exponential Smoothing) for smooth / erratic demand
  - Croston SBA for intermittent / lumpy demand
  - Season factors (from the season_factor table)
  - Outbreak factors (from recent disease_signal spikes)

Produces: predicted_rate, days_to_stockout, confidence, driver_label,
method_used — all written to the forecasts table.

This module is called:
  1. On API startup to populate forecasts if empty
  2. After POST /api/demo/scenario to recompute affected forecasts
  3. After POST /api/demo/reset to restore baseline
"""

import math
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# SES (Simple Exponential Smoothing)
# ---------------------------------------------------------------------------

def ses_forecast(
    values: List[float],
    alpha: float = 0.3,
    horizon: int = 14,
) -> Tuple[float, List[float], float]:
    """
    Simple Exponential Smoothing.

    Returns:
        (level, forecast_values, residual_std)
    """
    if not values or all(v == 0 for v in values):
        return 0.0, [0.0] * horizon, 0.0

    # Initialize level with first non-zero value or mean of first 7
    init_window = values[:7] if len(values) >= 7 else values
    level = sum(init_window) / len(init_window)

    residuals = []
    for v in values:
        error = v - level
        residuals.append(error)
        level = alpha * v + (1 - alpha) * level

    # Forecast is flat at the final level
    forecast_values = [max(0.0, level)] * horizon

    # Residual std for confidence bands
    if len(residuals) > 1:
        mean_res = sum(residuals) / len(residuals)
        var = sum((r - mean_res) ** 2 for r in residuals) / (len(residuals) - 1)
        residual_std = math.sqrt(var)
    else:
        residual_std = 0.0

    return max(0.0, level), forecast_values, residual_std


# ---------------------------------------------------------------------------
# Croston SBA (Syntetos-Boylan Approximation)
# ---------------------------------------------------------------------------

def croston_sba_forecast(
    values: List[float],
    alpha: float = 0.3,
    horizon: int = 14,
) -> Tuple[float, List[float], float]:
    """
    Croston's method with SBA (Syntetos-Boylan Approximation) debiasing.
    Designed for intermittent/lumpy demand with many zero periods.

    Returns:
        (predicted_rate, forecast_values, residual_std)
    """
    if not values or all(v == 0 for v in values):
        return 0.0, [0.0] * horizon, 0.0

    # Extract non-zero demand sizes and inter-demand intervals
    demand_sizes = []
    intervals = []
    periods_since_last = 0

    for v in values:
        periods_since_last += 1
        if v > 0:
            demand_sizes.append(v)
            intervals.append(periods_since_last)
            periods_since_last = 0

    if len(demand_sizes) < 2:
        # Too few non-zero observations — fall back to simple average
        avg = sum(values) / len(values) if values else 0
        return max(0.0, avg), [max(0.0, avg)] * horizon, 0.0

    # Initialize smoothed values
    z = demand_sizes[0]  # smoothed demand size
    p = intervals[0]     # smoothed inter-demand interval

    for i in range(1, len(demand_sizes)):
        z = alpha * demand_sizes[i] + (1 - alpha) * z
        p = alpha * intervals[i] + (1 - alpha) * p

    # SBA debiasing factor
    sba_factor = 1 - alpha / 2

    if p > 0:
        predicted_rate = (z / p) * sba_factor
    else:
        predicted_rate = 0.0

    predicted_rate = max(0.0, predicted_rate)
    forecast_values = [predicted_rate] * horizon

    # Residual std from demand sizes
    if len(demand_sizes) > 1:
        mean_d = sum(demand_sizes) / len(demand_sizes)
        var = sum((d - mean_d) ** 2 for d in demand_sizes) / (len(demand_sizes) - 1)
        residual_std = math.sqrt(var) / max(p, 1.0)
    else:
        residual_std = 0.0

    return predicted_rate, forecast_values, residual_std


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def compute_confidence(
    history_len: int,
    cv: float,
    demand_class: str,
) -> float:
    """
    Confidence score in [0, 1] derived from:
      - History length (≥90 days → full credit, linearly scaled below)
      - Demand variance (lower CV → higher confidence)
      - Demand class (smooth > erratic > intermittent > lumpy)
    """
    # History component: 0-0.4
    history_score = min(history_len / 90.0, 1.0) * 0.4

    # Variance component: 0-0.3  (CV of 0 → 0.3, CV of 1+ → 0)
    variance_score = max(0.0, 1.0 - cv) * 0.3

    # Class component: 0-0.3
    class_scores = {
        "smooth": 0.30,
        "erratic": 0.20,
        "intermittent": 0.15,
        "lumpy": 0.05,
    }
    class_score = class_scores.get(demand_class, 0.1)

    return round(min(1.0, history_score + variance_score + class_score), 2)


# ---------------------------------------------------------------------------
# Driver attribution
# ---------------------------------------------------------------------------

def compute_driver(
    season_factor: float,
    outbreak_factor: float,
    outbreak_condition: Optional[str],
    outbreak_pct_change: float,
) -> str:
    """
    Determine which factor moved the forecast most and produce
    a human-readable driver string.
    """
    season_impact = abs(season_factor - 1.0)
    outbreak_impact = abs(outbreak_factor - 1.0)

    if outbreak_impact > 0.1 and outbreak_impact >= season_impact:
        pct = round(outbreak_pct_change * 100)
        condition_name = (outbreak_condition or "disease").replace("_", " ").title()
        return f"{condition_name} cases +{pct}% in district"

    if season_impact > 0.1:
        direction = "increase" if season_factor > 1.0 else "decrease"
        pct = round(season_impact * 100)
        return f"Seasonal {direction} (+{pct}%)"

    return "Stable demand"


# ---------------------------------------------------------------------------
# Main forecasting function (operates on database data)
# ---------------------------------------------------------------------------

def forecast_facility_drug(
    daily_dispensing: List[Tuple[str, float]],  # [(date_str, qty), ...]
    current_stock: float,
    season_factor: float,
    outbreak_factor: float,
    outbreak_condition: Optional[str],
    outbreak_pct_change: float,
    demand_class: str,
    horizon: int = 14,
    lead_time_days: int = 7,
) -> dict:
    """
    Compute the full forecast for one facility-drug pair.

    Returns dict with keys:
        predicted_daily_rate, days_to_stockout, confidence,
        driver_label, method_used, history, forecast_band,
        reorder_point, stockout_date
    """
    # Extract just quantities for the model
    quantities = [q for _, q in daily_dispensing]

    # Choose model
    if demand_class in ("smooth", "erratic"):
        method = "ses"
        base_rate, forecast_vals, residual_std = ses_forecast(quantities, horizon=horizon)
    else:
        method = "croston_sba"
        base_rate, forecast_vals, residual_std = croston_sba_forecast(quantities, horizon=horizon)

    # Apply factors
    predicted_rate = base_rate * season_factor * outbreak_factor

    # Forecast band with factors applied
    band_center = [v * season_factor * outbreak_factor for v in forecast_vals]
    band_width = residual_std * 1.5 * season_factor * outbreak_factor
    band_lower = [max(0.0, v - band_width) for v in band_center]
    band_upper = [v + band_width for v in band_center]

    # Days to stockout
    if predicted_rate > 0:
        days_to_stockout = current_stock / predicted_rate
    else:
        days_to_stockout = None  # no demand → no stockout

    # Reorder point
    reorder_point = predicted_rate * lead_time_days

    # Stockout date
    stockout_date = None
    if days_to_stockout is not None and days_to_stockout < 365:
        stockout_date = (date.today() + timedelta(days=int(days_to_stockout))).isoformat()

    # Confidence
    cv = 0.0
    non_zero = [v for v in quantities if v > 0]
    if len(non_zero) >= 2:
        mean_nz = sum(non_zero) / len(non_zero)
        if mean_nz > 0:
            variance = sum((x - mean_nz) ** 2 for x in non_zero) / len(non_zero)
            cv = math.sqrt(variance) / mean_nz

    confidence = compute_confidence(len(quantities), cv, demand_class)

    # Driver
    driver_label = compute_driver(
        season_factor, outbreak_factor,
        outbreak_condition, outbreak_pct_change,
    )

    # Build history array (last 90 days max for the API)
    history = []
    for date_str, qty in daily_dispensing[-90:]:
        history.append({"date": date_str, "quantity": int(qty)})

    # Build forecast band array
    today = date.today()
    forecast_band = []
    for i in range(horizon):
        d = (today + timedelta(days=i + 1)).isoformat()
        forecast_band.append({
            "date": d,
            "predicted": round(band_center[i], 1),
            "lower": round(band_lower[i], 1),
            "upper": round(band_upper[i], 1),
        })

    return {
        "predicted_daily_rate": round(predicted_rate, 2),
        "days_to_stockout": round(days_to_stockout, 1) if days_to_stockout is not None else None,
        "confidence": confidence,
        "driver_label": driver_label,
        "method_used": method,
        "history": history,
        "forecast_band": forecast_band,
        "reorder_point": round(reorder_point, 1),
        "stockout_date": stockout_date,
    }
