from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "clean" / "trade_overview.csv"

SELECTION_COLOR = "#0F766E"
EXPORT_COLOR = "#1f77b4"
IMPORT_COLOR = "#d62728"
SURPLUS_COLOR = "#1f77b4"
DEFICIT_COLOR = "#d62728"


def format_value(value: float) -> str:
    """Format large KPI values with separators and no unnecessary decimals."""
    if pd.isna(value):
        return "—"
    return f"{value:,.0f}"


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values("year").reset_index(drop=True)

    numeric_cols = ["year", "exports", "imports", "balance", "turnover"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


st.set_page_config(page_title="Trade Overview", layout="wide")

df = load_data()

st.title("Trade Overview")
st.write(
    "This page shows Armenia's yearly trade overview, including exports, imports, "
    "trade balance, and total turnover from the cleaned historical archive."
)

# -----------------------------
# Selected year controls
# -----------------------------
available_years = sorted(df["year"].dropna().astype(int).unique().tolist())

selected_year = st.selectbox(
    "Select year for KPI snapshot",
    options=available_years,
    index=len(available_years) - 1 if available_years else 0,
)

selected_row = df.loc[df["year"] == selected_year].iloc[0]

st.caption(
    f"In **{int(selected_row['year'])}**, exports were {format_value(selected_row['exports'])}, "
    f"imports were {format_value(selected_row['imports'])}, and trade balance was "
    f"{format_value(selected_row['balance'])}."
)

# -----------------------------
# KPI cards for selected year
# -----------------------------
metric_cols = st.columns(5)
metric_cols[0].metric("Year", str(int(selected_row["year"])))
metric_cols[1].metric("Exports", format_value(selected_row["exports"]))
metric_cols[2].metric("Imports", format_value(selected_row["imports"]))
metric_cols[3].metric("Balance", format_value(selected_row["balance"]))
metric_cols[4].metric("Turnover", format_value(selected_row["turnover"]))

# -----------------------------
# Chart 1: full-history line chart + highlighted selected year
# -----------------------------
line_chart = go.Figure()

line_chart.add_trace(
    go.Scatter(
        x=df["year"],
        y=df["exports"],
        mode="lines+markers",
        name="Exports",
        line=dict(color=EXPORT_COLOR, width=3),
        marker=dict(size=7, color=EXPORT_COLOR),
        hovertemplate="Year: %{x}<br>Exports: %{y:,.0f}<extra></extra>",
    )
)

line_chart.add_trace(
    go.Scatter(
        x=df["year"],
        y=df["imports"],
        mode="lines+markers",
        name="Imports",
        line=dict(color=IMPORT_COLOR, width=3),
        marker=dict(size=7, color=IMPORT_COLOR),
        hovertemplate="Year: %{x}<br>Imports: %{y:,.0f}<extra></extra>",
    )
)

selected_year_df = df[df["year"] == selected_year]

# Highlight selected year on exports line
line_chart.add_trace(
    go.Scatter(
        x=selected_year_df["year"],
        y=selected_year_df["exports"],
        mode="markers",
        name="Selected year (Exports)",
        marker=dict(
            size=16,
            color=SELECTION_COLOR,
            line=dict(color="white", width=2),
        ),
        hovertemplate="Year: %{x}<br>Exports: %{y:,.0f}<extra></extra>",
        showlegend=False,
    )
)

# Highlight selected year on imports line
line_chart.add_trace(
    go.Scatter(
        x=selected_year_df["year"],
        y=selected_year_df["imports"],
        mode="markers",
        name="Selected year (Imports)",
        marker=dict(
            size=16,
            color=SELECTION_COLOR,
            line=dict(color="white", width=2),
        ),
        hovertemplate="Year: %{x}<br>Imports: %{y:,.0f}<extra></extra>",
        showlegend=False,
    )
)

line_chart.update_layout(
    title="Exports vs Imports Over Time",
    xaxis_title="Year",
    yaxis_title="USD (thousands)",
    hovermode="x unified",
)

# -----------------------------
# Chart 2: balance chart with selected year highlighted
# -----------------------------
balance_df = df.copy()
balance_df["bar_color"] = balance_df["balance"].apply(
    lambda x: SURPLUS_COLOR if x >= 0 else DEFICIT_COLOR
)
balance_df.loc[balance_df["year"] == selected_year, "bar_color"] = SELECTION_COLOR

bar_chart = px.bar(
    balance_df,
    x="year",
    y="balance",
    title="Trade Balance by Year",
    labels={"balance": "USD (thousands)", "year": "Year"},
)

bar_chart.update_traces(
    marker_color=balance_df["bar_color"],
    hovertemplate="Year: %{x}<br>Balance: %{y:,.0f}<extra></extra>",
)

# -----------------------------
# Chart 3: turnover trend
# -----------------------------
turnover_chart = px.line(
    df,
    x="year",
    y="turnover",
    title="Total Trade Turnover Over Time",
    markers=True,
    labels={"turnover": "USD (thousands)", "year": "Year"},
)

turnover_chart.update_traces(
    line=dict(width=3),
    marker=dict(size=7),
    hovertemplate="Year: %{x}<br>Turnover: %{y:,.0f}<extra></extra>",
)

chart_cols = st.columns(2)
with chart_cols[0]:
    st.plotly_chart(line_chart, use_container_width=True)
with chart_cols[1]:
    st.plotly_chart(bar_chart, use_container_width=True)

st.plotly_chart(turnover_chart, use_container_width=True)

with st.expander("Show underlying yearly data", expanded=False):
    st.dataframe(
        df.style.format(
            {
                "exports": "{:,.0f}",
                "imports": "{:,.0f}",
                "balance": "{:,.0f}",
                "turnover": "{:,.0f}",
            }
        ),
        use_container_width=True,
    )