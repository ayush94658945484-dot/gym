import pandas as pd
import streamlit as st

import charts
import energy
import queries

st.sidebar.title("Welcome")
st.sidebar.info("Ayush – Ayush946589454.84@gmail.com")

st.set_page_config(page_title="Gym Tracker – Ayush", layout="wide", page_icon="🏋️")


def fmt(v, suffix="", nd=0):
    return "—" if v is None or pd.isna(v) else f"{v:,.{nd}f}{suffix}"


def main():
    queries.ensure_db()
    daily = queries.load_daily()
    if daily.empty:
        st.warning("No data. Import a day with `python3 scripts/import_json.py data/<date>.json`.")
        return
    df = energy.energy_frame(daily)
    sets_df = queries.load_sets()

    last7 = df.iloc[-7:]
    tdee_now = energy.latest_tdee(df)
    trend_now = df["trend_weight"].dropna().iloc[-1] if df["trend_weight"].notna().any() else None
    trend_7ago = df["trend_weight"].shift(7).dropna()
    weekly_change = (trend_now - trend_7ago.iloc[-1]) if trend_now is not None and not trend_7ago.empty else None

    # ── Header ──────────────────────────────────────────────────────────────
    st.title("Ayush's Progress Tracker")
    c = st.columns(6)
    c[0].metric("Trend weight", fmt(trend_now, " kg", 2),
                delta=fmt(weekly_change, " kg/wk", 2) if weekly_change is not None else None,
                delta_color="inverse")
    c[1].metric("Empirical TDEE", fmt(tdee_now, " kcal"),
                help="From your weight trend + logged intake (21-day window), in logged-calorie units. "
                     "NOT the Apple Watch number.")
    c[2].metric("Intake (7d avg)", fmt(last7["intake"].mean(), " kcal"))
    deficit7 = (tdee_now - last7["intake"].mean()) if tdee_now is not None else None
    c[3].metric("Deficit (7d avg)", fmt(deficit7, " kcal"),
                delta="in deficit" if deficit7 and deficit7 > 0 else "at/over maintenance",
                delta_color="normal" if deficit7 and deficit7 > 0 else "off")
    c[4].metric("Protein (7d avg)", fmt(last7["protein"].mean(), " g"))
    c[5].metric("Sleep (7d avg)", fmt(last7["total_sleep_minutes"].mean() / 60
                                      if last7["total_sleep_minutes"].notna().any() else None, " h", 1))

    tab_energy, tab_nutrition, tab_training, tab_sleep, tab_activity, tab_body = st.tabs(
        ["⚖️ Energy & Goal", "🍽️ Nutrition", "🏋️ Training", "😴 Sleep & Recovery",
         "🚶 Activity", "🧬 Body Comp"])

    # ── Energy & Goal ───────────────────────────────────────────────────────
    with tab_energy:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(charts.weight_trend(df), use_container_width=True)
        with col2:
            st.plotly_chart(charts.tdee_history(df), use_container_width=True)
        fig = charts.deficit_bars(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Goal projection")
        g1, g2, g3 = st.columns(3)
        goal_kg = g1.number_input("Goal weight (kg)", value=70.0, step=0.5)
        planned_intake = g2.number_input("Planned daily intake (logged kcal)", value=1700, step=50)
        if tdee_now and trend_now:
            planned_deficit = tdee_now - planned_intake
            days = energy.project_goal(trend_now, goal_kg, planned_deficit)
            with g3:
                st.metric("Planned deficit", fmt(planned_deficit, " kcal/day"))
                if days:
                    eta = df.index[-1] + pd.Timedelta(days=days)
                    st.metric("Projected goal date", eta.strftime("%d %b %Y"),
                              delta=f"{days / 7:.0f} weeks")
                elif planned_deficit <= 0:
                    st.warning("Planned intake is at/above TDEE — no loss projected.")
                else:
                    st.success("Already at or below goal weight.")
        else:
            st.info("Not enough history yet to compute TDEE.")

    # ── Nutrition ───────────────────────────────────────────────────────────
    with tab_nutrition:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(charts.protein_chart(df), use_container_width=True)
        with col2:
            st.plotly_chart(charts.fiber_chart(df), use_container_width=True)
            st.plotly_chart(charts.macro_split(df), use_container_width=True)

        st.subheader("Micronutrients")
        micros = queries.load_micros()
        if micros.empty:
            st.info("No micronutrient data logged yet — /log-day records estimates from Jul 3 onward.")
        else:
            nutrient = st.selectbox("Nutrient", list(charts.MICRO_TARGETS))
            fig = charts.micro_chart(micros, nutrient)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No {nutrient} data logged yet.")

        with st.expander("Recent meals (14 days)"):
            meals = queries.load_recent_meals()
            st.dataframe(meals, use_container_width=True, hide_index=True)

    # ── Training ────────────────────────────────────────────────────────────
    with tab_training:
        if sets_df.empty:
            st.info("No lifting sets logged yet.")
        else:
            st.plotly_chart(charts.weekly_sets_by_muscle(sets_df), use_container_width=True)
            col1, col2 = st.columns([2, 1])
            with col1:
                names = sorted(sets_df["exercise_name"].unique())
                default_ix = 0
                counts = sets_df["exercise_name"].value_counts()
                if not counts.empty:
                    default_ix = names.index(counts.index[0])
                exercise = st.selectbox("Exercise", names, index=default_ix)
                fig = charts.exercise_progression(sets_df, exercise)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.plotly_chart(charts.gym_frequency(df), use_container_width=True)
            with st.expander("All-time PRs"):
                prs = (sets_df.groupby("exercise_name")
                       .agg(pr_kg=("weight", "max"), best_1rm=("est_1rm", "max"),
                            sets=("weight", "size"),
                            last_done=("date", "max"))
                       .sort_values("last_done", ascending=False).reset_index())
                prs["best_1rm"] = prs["best_1rm"].round(1)
                prs["last_done"] = prs["last_done"].dt.strftime("%Y-%m-%d")
                st.dataframe(prs, use_container_width=True, hide_index=True)

    # ── Sleep & Recovery ────────────────────────────────────────────────────
    with tab_sleep:
        st.plotly_chart(charts.sleep_chart(df, days=90), use_container_width=True)

    # ── Activity ────────────────────────────────────────────────────────────
    with tab_activity:
        steps_series = df["steps"].dropna()
        dist_series = df["distance_km"].dropna()
        if steps_series.empty:
            st.info("No activity data logged yet.")
        else:
            latest_date = steps_series.index[-1]
            latest_steps = steps_series.iloc[-1]
            latest_dist = df.loc[latest_date, "distance_km"] if latest_date in df.index else None
            a = st.columns(4)
            a[0].metric(f"Steps ({latest_date.strftime('%b %d')})", fmt(latest_steps, "", 0))
            a[1].metric(f"Distance ({latest_date.strftime('%b %d')})", fmt(latest_dist, " km", 2))
            a[2].metric("Steps (7d avg)", fmt(last7["steps"].mean(), "", 0))
            a[3].metric("Distance (7d avg)", fmt(last7["distance_km"].mean(), " km", 2))
            fig = charts.steps_chart(df, days=60)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

    # ── Body Comp ───────────────────────────────────────────────────────────
    with tab_body:
        bia = df[df["body_fat_pct"].notna()]
        if bia.empty:
            st.info("No BIA readings yet.")
        else:
            latest, first = bia.iloc[-1], bia.iloc[0]
            b = st.columns(4)
            b[0].metric("Body fat %", fmt(latest["body_fat_pct"], "%", 1),
                        delta=fmt(latest["body_fat_pct"] - first["body_fat_pct"], "%", 1),
                        delta_color="inverse")
            b[1].metric("Skeletal muscle", fmt(latest["skeletal_muscle_mass_kg"], " kg", 1),
                        delta=fmt(latest["skeletal_muscle_mass_kg"] - first["skeletal_muscle_mass_kg"], " kg", 1))
            b[2].metric("Fat mass", fmt(latest["fat_mass_kg"], " kg", 1),
                        delta=fmt(latest["fat_mass_kg"] - first["fat_mass_kg"], " kg", 1),
                        delta_color="inverse")
            b[3].metric("Visceral fat", fmt(latest["visceral_fat"], "", 0))
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(charts.body_comp(df), use_container_width=True)
            with col2:
                fig = charts.body_fat_pct(df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

    if st.button("Refresh data"):
        queries.ensure_db(force=True)
        st.cache_data.clear()
        st.rerun()


if __name__ == "__main__":
    main()
