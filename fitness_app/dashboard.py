"""
Fitness Tracker Dashboard
=========================
Works with both Streamlit (default) and Dash.
See instructions at the bottom of this file.

Install dependencies:
    pip install streamlit plotly psycopg2-binary pandas
    # or for Dash:
    pip install dash plotly psycopg2-binary pandas

Set environment variables before running (or edit the DB dict below):
    DB_HOST     your PostgreSQL host      (default: localhost)
    DB_PORT     your PostgreSQL port      (default: 5432)
    DB_NAME     your database name        (default: fitness)
    DB_USER     your database user        (default: postgres)
    DB_PASSWORD your database password    (default: empty)

Run (Streamlit):
    streamlit run dashboard.py

Run (Dash):
    python dashboard.py
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from psycopg2.extras import RealDictCursor

# ── Database connection ──────────────────────────────────────────────────────

DB = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME",     "fitness"),
    "user":     os.getenv("DB_USER",     "leom.johnson"),
    "password": os.getenv("DB_PASSWORD", ""),
}


def get_df(query: str) -> pd.DataFrame:
    """Run a SQL query and return a DataFrame."""
    with psycopg2.connect(**DB, cursor_factory=RealDictCursor) as conn:
        return pd.read_sql(query, conn)


# ── Targets (83 kg, cut phase) ───────────────────────────────────────────────
# Update these when you move to bridge / lean bulk phases.

TARGETS = {
    "kcal":    2258,
    "protein": 183,
    "carbs":   146,
    "fat":     75,
}

# ── Data loaders ─────────────────────────────────────────────────────────────

def load_data():
    nutrition = get_df("SELECT * FROM daily_nutrition ORDER BY log_date")
    weight    = get_df("SELECT * FROM rolling_weight   ORDER BY log_date")
    workouts  = get_df(
        "SELECT log_date, session_type, duration_min, rpe, notes "
        "FROM workouts ORDER BY log_date DESC LIMIT 30"
    )
    sets = get_df(
        "SELECT ws.exercise, ws.set_number, ws.reps, ws.weight_kg, ws.notes, "
        "       w.log_date, w.session_type "
        "FROM workout_sets ws "
        "JOIN workouts w ON ws.workout_id = w.id "
        "ORDER BY w.log_date DESC, ws.exercise, ws.set_number "
        "LIMIT 200"
    )
    return nutrition, weight, workouts, sets


# ── Charts ────────────────────────────────────────────────────────────────────

def weight_chart(weight: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weight["log_date"], y=weight["weight_kg"],
        mode="markers", name="Daily weight",
        marker=dict(color="#B5D4F4", size=6),
        opacity=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=weight["log_date"], y=weight["rolling_7d_avg"],
        mode="lines", name="7-day rolling avg",
        line=dict(color="#185FA5", width=2),
    ))
    fig.update_layout(
        title="Weight trend — 7-day rolling average",
        xaxis_title="Date", yaxis_title="kg",
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def kcal_chart(nutrition: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        nutrition, x="log_date", y="total_kcal",
        title="Daily calories",
        color_discrete_sequence=["#378ADD"],
    )
    fig.add_hline(
        y=TARGETS["kcal"], line_dash="dash", line_color="#E24B4A",
        annotation_text=f"Cut target {TARGETS['kcal']:,} kcal",
        annotation_position="top left",
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="kcal")
    return fig


def protein_chart(nutrition: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        nutrition, x="log_date", y="total_protein_g",
        title="Daily protein",
        color_discrete_sequence=["#1D9E75"],
    )
    fig.add_hline(
        y=TARGETS["protein"], line_dash="dash", line_color="#E24B4A",
        annotation_text=f"Target {TARGETS['protein']}g",
        annotation_position="top left",
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="g")
    return fig


def macro_pie(nutrition: pd.DataFrame) -> go.Figure:
    """Pie chart of average macro split over all logged days."""
    if nutrition.empty:
        return go.Figure()
    avg = nutrition[["total_protein_g", "total_carbs_g", "total_fat_g"]].mean()
    # calories per gram: protein=4, carbs=4, fat=9
    kcal_from = [avg["total_protein_g"] * 4,
                 avg["total_carbs_g"]   * 4,
                 avg["total_fat_g"]     * 9]
    fig = go.Figure(go.Pie(
        labels=["Protein", "Carbs", "Fat"],
        values=[round(v, 1) for v in kcal_from],
        hole=0.4,
        marker_colors=["#1D9E75", "#378ADD", "#EF9F27"],
    ))
    fig.update_layout(title="Average macro split (% of calories)")
    return fig


def rpe_chart(workouts: pd.DataFrame) -> go.Figure:
    df = workouts.dropna(subset=["rpe"])
    fig = px.scatter(
        df, x="log_date", y="rpe",
        color="session_type", size_max=10,
        title="Workout RPE over time",
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="RPE (1–10)",
                      legend_title="Session type")
    return fig


# ════════════════════════════════════════════════════════════════════════════
#  STREAMLIT VERSION  ← default
# ════════════════════════════════════════════════════════════════════════════

def run_streamlit():
    import streamlit as st

    st.set_page_config(page_title="Fitness Tracker", layout="wide")
    st.title("Fitness Tracker Dashboard")
    st.caption("83 kg · Cut phase")

    try:
        nutrition, weight, workouts, sets = load_data()
    except Exception as e:
        st.error(f"Could not connect to database: {e}")
        st.stop()

    # ── KPI row ──
    col1, col2, col3, col4 = st.columns(4)
    if not nutrition.empty:
        latest = nutrition.iloc[-1]
        col1.metric("Calories (latest day)",
                    f"{int(latest.total_kcal):,} kcal",
                    f"target {TARGETS['kcal']:,}")
        col2.metric("Protein (latest day)",
                    f"{latest.total_protein_g}g",
                    f"target {TARGETS['protein']}g")
    if not weight.empty:
        latest_w = weight.iloc[-1]
        col3.metric("Weight", f"{latest_w.weight_kg} kg")
        col4.metric("7-day avg", f"{latest_w.rolling_7d_avg} kg")

    st.divider()

    # ── Charts ──
    col_l, col_r = st.columns(2)
    with col_l:
        if not weight.empty:
            st.plotly_chart(weight_chart(weight), use_container_width=True)
        else:
            st.info("No weight data yet.")

    with col_r:
        if not nutrition.empty:
            st.plotly_chart(macro_pie(nutrition), use_container_width=True)
        else:
            st.info("No nutrition data yet.")

    if not nutrition.empty:
        st.plotly_chart(kcal_chart(nutrition), use_container_width=True)
        st.plotly_chart(protein_chart(nutrition), use_container_width=True)

    if not workouts.empty:
        st.plotly_chart(rpe_chart(workouts), use_container_width=True)

    st.divider()
    st.subheader("Recent workouts")
    if not workouts.empty:
        st.dataframe(workouts, use_container_width=True)
    else:
        st.info("No workouts logged yet.")

    st.subheader("Recent sets")
    if not sets.empty:
        st.dataframe(sets, use_container_width=True)
    else:
        st.info("No sets logged yet.")


# ════════════════════════════════════════════════════════════════════════════
#  DASH VERSION  ← uncomment this block and comment out run_streamlit() below
# ════════════════════════════════════════════════════════════════════════════

# def run_dash():
#     from dash import Dash, dcc, html
#
#     nutrition, weight, workouts, sets = load_data()
#     app = Dash(__name__)
#
#     app.layout = html.Div([
#         html.H1("Fitness Tracker Dashboard"),
#         html.P("83 kg · Cut phase"),
#         dcc.Graph(figure=weight_chart(weight))    if not weight.empty    else html.P("No weight data"),
#         dcc.Graph(figure=macro_pie(nutrition))    if not nutrition.empty else html.P("No nutrition data"),
#         dcc.Graph(figure=kcal_chart(nutrition))   if not nutrition.empty else html.P(""),
#         dcc.Graph(figure=protein_chart(nutrition))if not nutrition.empty else html.P(""),
#         dcc.Graph(figure=rpe_chart(workouts))     if not workouts.empty  else html.P("No workout data"),
#     ], style={"fontFamily": "sans-serif", "maxWidth": "1100px", "margin": "0 auto"})
#
#     app.run(debug=True)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_streamlit()
    # run_dash()  # ← swap to this for Dash
