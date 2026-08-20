"""
Energy-balance math: smoothed weight trend and empirical TDEE.

Method (and why): calorie estimates for meals carry a systematic bias
(restaurant oil, portion guesses), so a TDEE guessed from formulas or the
Apple Watch cannot be compared against logged intake. Instead we compute
TDEE *empirically in logged-calorie units*:

    TDEE(t) = mean logged intake over last w days
              - (trend_weight(t) - trend_weight(t-w)) * 7700 / w

Because the estimation bias is roughly consistent day-to-day, it cancels:
eating N logged-kcal below this TDEE produces a real ~N kcal/day deficit,
even if neither number matches a lab measurement. Weight change is the
ground truth that anchors everything.
"""

import pandas as pd

KCAL_PER_KG = 7700
TREND_ALPHA = 0.10  # Hacker's Diet style exponential smoothing


def trend_weight(weight_series):
    """Exponentially smoothed weight over a daily-indexed series with gaps.

    Iterative EMA that simply carries the trend across missing days
    (no interpolation, no lookahead).
    """
    trend = []
    current = None
    for w in weight_series:
        if pd.notna(w):
            current = w if current is None else current + TREND_ALPHA * (w - current)
        trend.append(current)
    return pd.Series(trend, index=weight_series.index)


def energy_frame(daily_df):
    """Add trend weight and rolling empirical TDEE columns.

    daily_df: DataFrame indexed by consecutive calendar dates with columns
    'intake' (kcal, NaN when no meals logged) and 'weight' (kg, NaN when
    not measured).
    """
    df = daily_df.copy()
    df["trend_weight"] = trend_weight(df["weight"])
    for w in (14, 21, 28):
        intake_avg = df["intake"].rolling(w, min_periods=max(5, int(w * 0.7))).mean()
        dkg = df["trend_weight"] - df["trend_weight"].shift(w)
        df[f"tdee_{w}"] = intake_avg - dkg * KCAL_PER_KG / w
    # headline TDEE: prefer the 21-day window, fall back to 14
    df["tdee"] = df["tdee_21"].fillna(df["tdee_14"])
    df["deficit"] = df["tdee"] - df["intake"]
    return df


def latest_tdee(df):
    """Most recent non-null headline TDEE value (or None)."""
    s = df["tdee"].dropna()
    return float(s.iloc[-1]) if not s.empty else None


def project_goal(current_kg, goal_kg, daily_deficit):
    """Days to reach goal_kg at a given real daily deficit (logged units)."""
    if daily_deficit <= 0 or current_kg <= goal_kg:
        return None
    return (current_kg - goal_kg) * KCAL_PER_KG / daily_deficit
