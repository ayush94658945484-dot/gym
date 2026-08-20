"""Plotly figures for the dashboard. Each function takes DataFrames and returns a figure."""

import pandas as pd
import plotly.graph_objects as go

TEMPLATE = "plotly_dark"
GREEN = "#2ecc71"
RED = "#e74c3c"
BLUE = "#3498db"
ORANGE = "#f39c12"
PURPLE = "#9b59b6"
GRAY = "#7f8c8d"


def _base_layout(fig, title, y_title=None, height=380):
    fig.update_layout(
        template=TEMPLATE, height=height,
        title=dict(text=title, y=0.98, yanchor="top"),
        margin=dict(l=40, r=20, t=85, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_xaxes(tickformat="%b %d", hoverformat="%a %b %d")
    if y_title:
        fig.update_yaxes(title=y_title)
    return fig


# ── Energy & Weight ─────────────────────────────────────────────────────────

def weight_trend(df):
    """Raw weigh-ins as dots + smoothed trend line."""
    fig = go.Figure()
    raw = df["weight"].dropna()
    fig.add_trace(go.Scatter(x=raw.index, y=raw, mode="markers", name="Scale reading",
                             marker=dict(size=6, color=GRAY, opacity=0.7)))
    trend = df["trend_weight"].dropna()
    fig.add_trace(go.Scatter(x=trend.index, y=trend, mode="lines", name="Trend (smoothed)",
                             line=dict(color=BLUE, width=3)))
    return _base_layout(fig, "Weight: scale noise vs real trend", "kg")


def tdee_history(df):
    """Rolling empirical TDEE with daily intake context."""
    fig = go.Figure()
    intake = df["intake"].dropna()
    fig.add_trace(go.Bar(x=intake.index, y=intake, name="Daily intake (logged)",
                         marker_color=GRAY, opacity=0.35))
    for w, color in ((14, ORANGE), (21, GREEN), (28, PURPLE)):
        s = df[f"tdee_{w}"].dropna()
        fig.add_trace(go.Scatter(x=s.index, y=s, mode="lines", name=f"TDEE ({w}d window)",
                                 line=dict(color=color, width=3 if w == 21 else 1.5,
                                           dash=None if w == 21 else "dot")))
    return _base_layout(fig, "Empirical TDEE (in logged-calorie units) vs intake", "kcal/day")


def deficit_bars(df, days=28):
    """Daily estimated deficit vs the rolling TDEE, recent window."""
    recent = df.iloc[-days:]
    d = recent["deficit"].dropna()
    if d.empty:
        return None
    colors = [GREEN if v > 0 else RED for v in d]
    fig = go.Figure(go.Bar(x=d.index, y=d, marker_color=colors, name="Deficit"))
    fig.add_hline(y=0, line_color="white", line_width=1)
    fig.add_hline(y=500, line_dash="dash", line_color=GREEN,
                  annotation_text="500 target", annotation_position="top left")
    return _base_layout(fig, f"Daily deficit vs empirical TDEE (last {days}d) — green = deficit", "kcal")


# ── Nutrition ───────────────────────────────────────────────────────────────

def protein_chart(df, days=60):
    recent = df.iloc[-days:]
    p = recent["protein"].dropna()
    trend_w = recent["trend_weight"].ffill()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=p.index, y=p, name="Protein", marker_color=BLUE, opacity=0.7))
    lo = (trend_w * 1.6).dropna()
    hi = (trend_w * 2.0).dropna()
    fig.add_trace(go.Scatter(x=lo.index, y=lo, name="1.6 g/kg", mode="lines",
                             line=dict(color=ORANGE, dash="dash", width=1.5)))
    fig.add_trace(go.Scatter(x=hi.index, y=hi, name="2.0 g/kg", mode="lines",
                             line=dict(color=GREEN, dash="dash", width=1.5)))
    return _base_layout(fig, f"Protein vs bodyweight targets (last {days}d)", "g")


def fiber_chart(df, days=60):
    recent = df.iloc[-days:]
    f = recent["fiber"].dropna()
    colors = [GREEN if v >= 25 else (ORANGE if v >= 15 else RED) for v in f]
    fig = go.Figure(go.Bar(x=f.index, y=f, marker_color=colors, name="Fiber"))
    fig.add_hline(y=25, line_dash="dash", line_color=GREEN, annotation_text="25g RDA")
    return _base_layout(fig, f"Fiber (last {days}d) — red under 15g", "g", height=300)


def macro_split(df):
    """Weekly average of calories from each macro."""
    wk = df[["protein", "carbs", "fat"]].resample("W-MON").mean()
    fig = go.Figure()
    for col, kcal_per_g, color in (("protein", 4, BLUE), ("carbs", 4, ORANGE), ("fat", 9, RED)):
        fig.add_trace(go.Bar(x=wk.index, y=wk[col] * kcal_per_g, name=f"{col} kcal", marker_color=color))
    fig.update_layout(barmode="stack")
    return _base_layout(fig, "Weekly avg calories by macro", "kcal/day")


# ── Training ────────────────────────────────────────────────────────────────

def weekly_sets_by_muscle(sets_df):
    d = sets_df.copy()
    d["week"] = d["date"].dt.to_period("W-SUN").dt.start_time
    agg = d.groupby(["week", "muscle_group"]).size().unstack(fill_value=0)
    fig = go.Figure()
    for mg in agg.columns:
        fig.add_trace(go.Bar(x=agg.index, y=agg[mg], name=str(mg)))
    fig.update_layout(barmode="stack")
    return _base_layout(fig, "Weekly working sets per muscle group", "sets", height=420)


def exercise_progression(sets_df, exercise):
    d = sets_df[sets_df["exercise_name"] == exercise]
    if d.empty:
        return None
    per_day = d.groupby("date").agg(top_weight=("weight", "max"), best_1rm=("est_1rm", "max"))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=per_day.index, y=per_day["top_weight"], mode="lines+markers",
                             name="Top set weight", line=dict(color=BLUE, width=2.5)))
    fig.add_trace(go.Scatter(x=per_day.index, y=per_day["best_1rm"], mode="lines+markers",
                             name="Est. 1RM (Epley)", line=dict(color=ORANGE, dash="dot")))
    # PR markers: sessions where top weight beat all history before them
    running_max = per_day["top_weight"].cummax()
    is_pr = per_day["top_weight"] > running_max.shift(1).fillna(-1)
    prs = per_day[is_pr]
    if not prs.empty:
        fig.add_trace(go.Scatter(x=prs.index, y=prs["top_weight"], mode="markers", name="PR",
                                 marker=dict(symbol="star", size=14, color=GREEN)))
    return _base_layout(fig, f"{exercise} progression", "kg")


def gym_frequency(daily_df):
    gym = (daily_df["gym_minutes"].fillna(0) > 0).resample("W-MON").sum()
    colors = [GREEN if v >= 3 else (ORANGE if v >= 2 else RED) for v in gym]
    fig = go.Figure(go.Bar(x=gym.index, y=gym, marker_color=colors))
    fig.add_hline(y=3, line_dash="dash", line_color=GREEN, annotation_text="3/week target")
    return _base_layout(fig, "Gym sessions per week", "days", height=300)


# ── Sleep & recovery ────────────────────────────────────────────────────────

def sleep_chart(df, days=60):
    recent = df.iloc[-days:]
    s = (recent["total_sleep_minutes"] / 60).dropna()
    colors = [GREEN if v >= 7 else (ORANGE if v >= 6 else RED) for v in s]
    fig = go.Figure(go.Bar(x=s.index, y=s, marker_color=colors, name="Sleep"))
    avg7 = (recent["total_sleep_minutes"] / 60).rolling(7, min_periods=3).mean().dropna()
    fig.add_trace(go.Scatter(x=avg7.index, y=avg7, mode="lines", name="7d avg",
                             line=dict(color="white", width=2)))
    fig.add_hline(y=7, line_dash="dash", line_color=GREEN)
    return _base_layout(fig, f"Sleep (last {days}d) — red under 6h", "hours")


# ── Activity ────────────────────────────────────────────────────────────────

def steps_chart(df, days=60):
    """Daily steps as bars with a 7-day rolling average; distance shown on hover."""
    recent = df.iloc[-days:]
    steps = recent["steps"].dropna()
    if steps.empty:
        return None
    dist = recent["distance_km"].reindex(steps.index)
    hover_dist = [f"{d:.2f} km" if pd.notna(d) else "—" for d in dist]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=steps.index, y=steps, name="Daily steps",
        marker_color=BLUE, opacity=0.7,
        customdata=hover_dist,
        hovertemplate="%{y:,.0f} steps<br>%{customdata}<extra></extra>",
    ))
    avg7 = recent["steps"].rolling(7, min_periods=3).mean().dropna()
    fig.add_trace(go.Scatter(x=avg7.index, y=avg7, mode="lines", name="7d avg",
                             line=dict(color="white", width=2)))
    fig.add_hline(y=10000, line_dash="dash", line_color=GREEN, annotation_text="10k target")
    return _base_layout(fig, f"Steps (last {days}d)", "steps")


# ── Micronutrients ──────────────────────────────────────────────────────────

# label: (column, target, unit, is_upper_limit)
MICRO_TARGETS = {
    "Calcium": ("calcium_mg", 1000, "mg", False),
    "Iron": ("iron_mg", 8, "mg", False),
    "Zinc": ("zinc_mg", 11, "mg", False),
    "Vitamin B12": ("b12_ug", 2.4, "µg", False),
    "Potassium": ("potassium_mg", 3400, "mg", False),
    "Sodium": ("sodium_mg", 2300, "mg", True),
    "Vitamin C": ("vitamin_c_mg", 90, "mg", False),
    "Vitamin D": ("vitamin_d_ug", 15, "µg", False),
    "Omega-3": ("omega3_g", 1.1, "g", False),
    "Magnesium": ("magnesium_mg", 400, "mg", False),
}


def micro_chart(micros_df, label, days=60):
    col, target, unit, upper = MICRO_TARGETS[label]
    if micros_df.empty or col not in micros_df:
        return None
    s = micros_df[col].dropna().iloc[-days:]
    if s.empty:
        return None
    if upper:  # limit: green under, red over
        colors = [GREEN if v <= target else RED for v in s]
        annotation = f"{target:g} {unit} upper limit"
    else:  # RDA: green at/above, orange within 60%, red below
        colors = [GREEN if v >= target else (ORANGE if v >= 0.6 * target else RED) for v in s]
        annotation = f"{target:g} {unit} RDA"
    fig = go.Figure(go.Bar(x=s.index, y=s, marker_color=colors, name=label))
    fig.add_hline(y=target, line_dash="dash", line_color=RED if upper else GREEN,
                  annotation_text=annotation)
    return _base_layout(fig, f"{label} — estimated daily intake", unit, height=340)


# ── Body composition ────────────────────────────────────────────────────────

def body_comp(df):
    fig = go.Figure()
    for col, name, color in (("skeletal_muscle_mass_kg", "Skeletal muscle", GREEN),
                             ("fat_mass_kg", "Fat mass", RED)):
        s = df[col].dropna()
        if not s.empty:
            fig.add_trace(go.Scatter(x=s.index, y=s, mode="lines+markers", name=name,
                                     line=dict(color=color, width=2.5)))
    return _base_layout(fig, "Body composition (Xiaomi BIA — trend-reliable, not absolute)", "kg")


def body_fat_pct(df):
    s = df["body_fat_pct"].dropna()
    if s.empty:
        return None
    fig = go.Figure(go.Scatter(x=s.index, y=s, mode="lines+markers",
                               line=dict(color=ORANGE, width=2.5), name="Body fat %"))
    return _base_layout(fig, "Body fat % (BIA)", "%", height=320)
