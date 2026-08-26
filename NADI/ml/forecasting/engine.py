"""
NADI Forecasting Engine — Pure NumPy implementation.

ADR-009: No statsforecast dependency. SES and Croston SBA implemented
in ~200 lines for a lightweight Docker image.

SKU classification routes each facility-drug pair to the right method:
- Smooth/erratic → Simple Exponential Smoothing
- Intermittent/lumpy → Croston SBA

Season factors and outbreak factors are applied on top of the base
forecast as multiplicative adjustments per CONTEXT.md:
  predicted_rate = burn_rate * season_factor * outbreak_factor
"""

import math
from typing import List, Tuple, Optional, Dict

# ── SKU Classification ────────────────────────────────────────────────────

def classify_demand(values: List[float]) -> str:
    """
    Classify demand pattern using CV and ADI thresholds.
    Matches the generator's classify_demand() thresholds exactly.
    
    CV < 0.49 and ADI < 1.32 → smooth
    CV >= 0.49 and ADI < 1.32 → erratic
    CV < 0.49 and ADI >= 1.32 → intermittent
    CV >= 0.49 and ADI >= 1.32 → lumpy
    """
    non_zero = [v for v in values if v > 0]
    if len(non_zero) < 3:
        return "lumpy"
    
    mean_nz = sum(non_zero) / len(non_zero)
    if mean_nz == 0:
        return "lumpy"
    
    variance = sum((x - mean_nz) ** 2 for x in non_zero) / len(non_zero)
    cv = math.sqrt(variance) / mean_nz
    adi = len(values) / max(len(non_zero), 1)
    
    if cv < 0.49 and adi < 1.32:
        return "smooth"
    elif cv >= 0.49 and adi < 1.32:
        return "erratic"
    elif cv < 0.49 and adi >= 1.32:
        return "intermittent"
    else:
        return "lumpy"


# ── Simple Exponential Smoothing ──────────────────────────────────────────

def ses_forecast(
    values: List[float],
    alpha: float = 0.3,
    horizon: int = 30,
) -> Tuple[float, List[float], List[float], List[float]]:
    """
    Simple Exponential Smoothing.
    Returns (level, predicted, lower, upper) for the horizon.
    
    For smooth/erratic demand where zeros are rare.
    """
    if not values or all(v == 0 for v in values):
        return 0.0, [0.0] * horizon, [0.0] * horizon, [0.0] * horizon
    
    # Initialize level to the mean of first 10 values
    init_window = min(10, len(values))
    level = sum(values[:init_window]) / init_window
    
    # Fit
    residuals = []
    for v in values:
        residuals.append(v - level)
        level = alpha * v + (1 - alpha) * level
    
    # Forecast: flat at last level
    predicted = [max(0, level)] * horizon
    
    # Prediction interval using residual std
    if len(residuals) > 2:
        res_mean = sum(residuals) / len(residuals)
        res_var = sum((r - res_mean) ** 2 for r in residuals) / (len(residuals) - 1)
        res_std = math.sqrt(res_var)
    else:
        res_std = level * 0.3  # fallback
    
    lower = []
    upper = []
    for h in range(1, horizon + 1):
        # Widening interval
        width = 1.96 * res_std * math.sqrt(1 + (h - 1) * alpha ** 2)
        lower.append(max(0, level - width))
        upper.append(level + width)
    
    return level, predicted, lower, upper


# ── Croston SBA ───────────────────────────────────────────────────────────

def croston_sba_forecast(
    values: List[float],
    alpha: float = 0.15,
    horizon: int = 30,
) -> Tuple[float, List[float], List[float], List[float]]:
    """
    Croston's method with Syntetos-Boylan Approximation (SBA).
    
    For intermittent/lumpy demand where many days have zero demand.
    Separately smooths demand size and inter-demand interval.
    """
    if not values or all(v == 0 for v in values):
        return 0.0, [0.0] * horizon, [0.0] * horizon, [0.0] * horizon
    
    # Extract non-zero demands and their intervals
    demands = []
    intervals = []
    gap = 0
    for v in values:
        gap += 1
        if v > 0:
            demands.append(v)
            intervals.append(gap)
            gap = 0
    
    if len(demands) < 2:
        # Too few non-zero values — return simple average
        avg = sum(values) / len(values)
        return avg, [max(0, avg)] * horizon, [0.0] * horizon, [avg * 2] * horizon
    
    # Initialize
    z = sum(demands[:3]) / min(3, len(demands))  # demand size level
    p = sum(intervals[:3]) / min(3, len(intervals))  # interval level
    
    # Smooth
    for i in range(len(demands)):
        z = alpha * demands[i] + (1 - alpha) * z
        p = alpha * intervals[i] + (1 - alpha) * p
    
    # SBA adjustment: multiply by (1 - alpha/2) to correct bias
    sba_rate = (z / p) * (1 - alpha / 2) if p > 0 else 0
    
    predicted = [max(0, sba_rate)] * horizon
    
    # Confidence band — wider than SES due to intermittency
    demand_std = math.sqrt(
        sum((d - z) ** 2 for d in demands) / max(len(demands) - 1, 1)
    ) if len(demands) > 1 else z * 0.5
    
    lower = []
    upper = []
    for h in range(1, horizon + 1):
        width = 1.96 * (demand_std / max(p, 1)) * math.sqrt(1 + h * 0.05)
        lower.append(max(0, sba_rate - width))
        upper.append(sba_rate + width)
    
    return sba_rate, predicted, lower, upper


# ── Forecast Orchestrator ─────────────────────────────────────────────────

# Condition → drug categories mapping for outbreak factor
CONDITION_DRUG_MAP: Dict[str, List[str]] = {
    "dengue": ["antimalarial", "ors_zinc", "analgesic", "antibiotic"],
    "malaria": ["antimalarial", "analgesic"],
    "diarrhoeal": ["ors_zinc", "antibiotic", "gastrointestinal"],
    "respiratory_infection": ["respiratory", "antibiotic", "analgesic"],
    "tuberculosis": ["antibiotic", "nutritional"],
}


def compute_outbreak_factor(
    disease_signals: List[dict],
    drug_category: str,
) -> Tuple[float, Optional[str]]:
    """
    Compute outbreak factor from recent disease signals.
    
    Compares last 2 weeks of case counts to the prior 4 weeks.
    Returns (factor, driver_string or None).
    
    disease_signals: list of {condition, week_start, case_count} dicts,
                     sorted by week_start desc.
    """
    if not disease_signals:
        return 1.0, None
    
    best_factor = 1.0
    best_driver = None
    
    for condition, affected_categories in CONDITION_DRUG_MAP.items():
        if drug_category not in affected_categories:
            continue
        
        # Filter signals for this condition
        cond_signals = [s for s in disease_signals if s.get("condition") == condition]
        if len(cond_signals) < 4:
            continue
        
        # Recent (last 2 entries) vs baseline (next 4 entries)
        recent = cond_signals[:2]
        baseline = cond_signals[2:6]
        
        if not baseline:
            continue
        
        recent_avg = sum(float(s.get("case_count", 0)) for s in recent) / len(recent)
        baseline_avg = sum(float(s.get("case_count", 0)) for s in baseline) / len(baseline)
        
        # Guard against tiny baselines
        if baseline_avg < 5:
            continue
        
        ratio = recent_avg / baseline_avg
        
        if ratio > 1.2:  # Significant increase
            factor = min(ratio, 5.0)  # Cap at 5x
            if factor > best_factor:
                # Use capped factor for display, not raw ratio
                pct_change = round((factor - 1) * 100)
                best_factor = factor
                best_driver = f"{condition.replace('_', ' ').title()} cases +{pct_change}% in this block"
    
    return best_factor, best_driver


def compute_season_factor(
    season_factors: List[dict],
    drug_category: str,
    month: int,
) -> float:
    """
    Look up the season factor for a drug category and month.
    season_factors: list of {drug_category, month, factor} dicts.
    """
    for sf in season_factors:
        if sf["drug_category"] == drug_category and sf["month"] == month:
            return sf["factor"]
    return 1.0


def compute_confidence(
    history: List[float],
    method: str,
    demand_class: str,
) -> float:
    """
    Confidence score [0, 1] based on:
    - History length (more data = higher confidence)
    - Data density (fewer zeros = higher for non-intermittent)
    - Method appropriateness
    """
    n = len(history)
    non_zero = sum(1 for v in history if v > 0)
    density = non_zero / max(n, 1)
    
    # Base confidence from history length (plateaus around 90 days)
    length_score = min(n / 90, 1.0)
    
    # Density score — for intermittent, low density is expected
    if demand_class in ("intermittent", "lumpy"):
        density_score = min(density / 0.3, 1.0)  # 30%+ density is good for intermittent
    else:
        density_score = density  # Higher is better for smooth
    
    # Combined
    confidence = 0.5 * length_score + 0.4 * density_score + 0.1
    return round(min(max(confidence, 0.1), 0.99), 2)


def identify_driver(
    season_factor: float,
    outbreak_factor: float,
    outbreak_driver: Optional[str],
    burn_trend: float,  # ratio of recent burn to historical average
) -> str:
    """
    Pick the single largest factor driving the forecast and return
    a human-readable string.
    """
    factors = {
        "outbreak": (outbreak_factor, outbreak_driver),
        "season": (season_factor, None),
        "trend": (burn_trend, None),
    }
    
    # Find the factor furthest from 1.0
    max_deviation = 0
    driver_key = "trend"
    for key, (factor, _) in factors.items():
        deviation = abs(factor - 1.0)
        if deviation > max_deviation:
            max_deviation = deviation
            driver_key = key
    
    if driver_key == "outbreak" and outbreak_driver:
        return outbreak_driver
    elif driver_key == "season":
        if season_factor > 1.1:
            pct = round((season_factor - 1) * 100)
            return f"Seasonal demand +{pct}% this month"
        elif season_factor < 0.9:
            pct = round((1 - season_factor) * 100)
            return f"Seasonal demand -{pct}% this month"
        else:
            return "Stable seasonal pattern"
    else:
        if burn_trend > 1.1:
            pct = round((burn_trend - 1) * 100)
            return f"Consumption trend rising +{pct}%"
        elif burn_trend < 0.9:
            pct = round((1 - burn_trend) * 100)
            return f"Consumption trend falling -{pct}%"
        else:
            return "Stable consumption pattern"


def forecast_facility_drug(
    daily_dispensing: List[dict],  # [{date, quantity}], last 180 days
    current_stock: int,
    drug_category: str,
    current_month: int,
    season_factors: List[dict],
    disease_signals: List[dict],
    horizon: int = 30,
    lead_time_days: int = 7,
) -> dict:
    """
    Full forecast pipeline for one facility-drug pair.
    
    Returns dict matching the API.md /forecast contract.
    """
    # Extract raw values
    values = [d["quantity"] for d in daily_dispensing]
    
    # 1. Classify
    demand_class = classify_demand(values)
    
    # 2. Choose method and forecast
    if demand_class in ("smooth", "erratic"):
        method = "ses"
        base_rate, predicted, lower, upper = ses_forecast(values, horizon=horizon)
    else:
        method = "croston_sba"
        base_rate, predicted, lower, upper = croston_sba_forecast(values, horizon=horizon)
    
    # 3. Season factor
    sf = compute_season_factor(season_factors, drug_category, current_month)
    
    # 4. Outbreak factor
    of, outbreak_driver = compute_outbreak_factor(disease_signals, drug_category)
    
    # 5. Apply factors
    combined_factor = sf * of
    predicted = [max(0, p * combined_factor) for p in predicted]
    lower = [max(0, lo * combined_factor) for lo in lower]
    upper = [u * combined_factor for u in upper]
    predicted_rate = base_rate * combined_factor
    
    # 6. Days to stockout
    if predicted_rate > 0:
        days_to_stockout = current_stock / predicted_rate
    else:
        days_to_stockout = None
    
    # 7. Reorder point: burn_rate × lead_time
    reorder_point = round(predicted_rate * lead_time_days) if predicted_rate > 0 else 0
    
    # 8. Burn trend (recent 14 days vs full history average)
    if len(values) > 14:
        recent_avg = sum(values[-14:]) / 14
        full_avg = sum(values) / len(values)
        burn_trend = recent_avg / full_avg if full_avg > 0 else 1.0
    else:
        burn_trend = 1.0
    
    # 9. Driver
    driver = identify_driver(sf, of, outbreak_driver, burn_trend)
    
    # 10. Confidence
    confidence = compute_confidence(values, method, demand_class)
    
    return {
        "predicted_daily_rate": round(predicted_rate, 2),
        "days_to_stockout": round(days_to_stockout, 1) if days_to_stockout is not None else None,
        "confidence": confidence,
        "driver": driver,
        "method_used": method,
        "demand_class": demand_class,
        "reorder_point": reorder_point,
        "forecast": [
            {"predicted": round(p, 1), "lower": round(lo, 1), "upper": round(u, 1)}
            for p, lo, u in zip(predicted, lower, upper)
        ],
    }
