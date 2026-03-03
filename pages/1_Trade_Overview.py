from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "clean" / "trade_overview.csv"


def format_value(value: float) -> str:
    """Format large KPI values with separators and no unnecessary decimals."""
    return f"{value:,.0f}"


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values("year").reset_index(drop=True)
    return df


st.set_page_config(page_title="Trade Overview", layout="wide")

df = load_data()
latest_row = df.iloc[-1]

st.title("Trade Overview")
st.write(
    "This page shows Armenia's yearly trade overview, including exports, imports, "
    "trade balance, and total turnover from the cleaned historical archive."
)

# Show the latest available year as quick top-line indicators.
metric_cols = st.columns(5)
metric_cols[0].metric("Year", str(int(latest_row["year"])))
metric_cols[1].metric("Exports", format_value(latest_row["exports"]))
metric_cols[2].metric("Imports", format_value(latest_row["imports"]))
metric_cols[3].metric("Balance", format_value(latest_row["balance"]))
metric_cols[4].metric("Turnover", format_value(latest_row["turnover"]))

line_chart = px.line(
    df,
    x="year",
    y=["exports", "imports"],
    title="Exports vs Imports Over Time",
    markers=True,
    labels={"value": "USD (thousands)", "year": "Year", "variable": "Series"},
)

bar_chart = px.bar(
    df,
    x="year",
    y="balance",
    title="Trade Balance by Year",
    labels={"balance": "USD (thousands)", "year": "Year"},
)

chart_cols = st.columns(2)
with chart_cols[0]:
    st.plotly_chart(line_chart, use_container_width=True)
with chart_cols[1]:
    st.plotly_chart(bar_chart, use_container_width=True)

st.subheader("Cleaned Trade Overview Data")
st.dataframe(df, use_container_width=True)
