from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.i18n import t


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "clean" / "trade_overview.csv"

SELECTION_COLOR = "#0F766E"
EXPORT_COLOR = "#1f77b4"
IMPORT_COLOR = "#d62728"
SURPLUS_COLOR = "#1f77b4"
DEFICIT_COLOR = "#d62728"


def format_value(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.0f}"


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values("year").reset_index(drop=True)
    for col in ["year", "exports", "imports", "balance", "turnover"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


st.set_page_config(page_title=t("trade_overview_title"), layout="wide")

df = load_data()

st.title(t("trade_overview_title"))
st.write(
    {
        "en": "Yearly overview of exports, imports, trade balance, and total turnover.",
        "hy": "Տարեկան ամփոփ պատկեր՝ արտահանում, ներմուծում, հաշվեկշիռ և ընդհանուր շրջանառություն։",
    }.get(st.session_state.get("lang", "en"), "Yearly overview of exports, imports, trade balance, and total turnover.")
)

available_years = sorted(df["year"].dropna().astype(int).unique().tolist())
selected_year = st.selectbox(
    t("select_year"),
    options=available_years,
    index=len(available_years) - 1 if available_years else 0,
)

selected_row = df.loc[df["year"] == selected_year].iloc[0]

st.caption(
    {
        "en": f"In {int(selected_row['year'])}, exports were {format_value(selected_row['exports'])}, "
              f"imports were {format_value(selected_row['imports'])}, and balance was {format_value(selected_row['balance'])}.",
        "hy": f"{int(selected_row['year'])}-ին արտահանումը եղել է {format_value(selected_row['exports'])}, "
              f"ներմուծումը՝ {format_value(selected_row['imports'])}, հաշվեկշիռը՝ {format_value(selected_row['balance'])}։",
    }.get(st.session_state.get("lang", "en"))
)

metric_cols = st.columns(5)
metric_cols[0].metric(t("year"), str(int(selected_row["year"])))
metric_cols[1].metric(t("exports"), format_value(selected_row["exports"]))
metric_cols[2].metric(t("imports"), format_value(selected_row["imports"]))
metric_cols[3].metric(t("balance"), format_value(selected_row["balance"]))
metric_cols[4].metric(t("turnover"), format_value(selected_row["turnover"]))

# Chart 1: exports vs imports + highlighted selected year
line_chart = go.Figure()
line_chart.add_trace(
    go.Scatter(
        x=df["year"], y=df["exports"],
        mode="lines+markers",
        name=t("exports"),
        line=dict(color=EXPORT_COLOR, width=3),
        marker=dict(size=7, color=EXPORT_COLOR),
        hovertemplate=f"{t('year')}: %{{x}}<br>{t('exports')}: %{{y:,.0f}}<extra></extra>",
    )
)
line_chart.add_trace(
    go.Scatter(
        x=df["year"], y=df["imports"],
        mode="lines+markers",
        name=t("imports"),
        line=dict(color=IMPORT_COLOR, width=3),
        marker=dict(size=7, color=IMPORT_COLOR),
        hovertemplate=f"{t('year')}: %{{x}}<br>{t('imports')}: %{{y:,.0f}}<extra></extra>",
    )
)

sel = df[df["year"] == selected_year]
line_chart.add_trace(
    go.Scatter(
        x=sel["year"], y=sel["exports"],
        mode="markers",
        marker=dict(size=16, color=SELECTION_COLOR, line=dict(color="white", width=2)),
        hovertemplate=f"{t('year')}: %{{x}}<br>{t('exports')}: %{{y:,.0f}}<extra></extra>",
        showlegend=False,
    )
)
line_chart.add_trace(
    go.Scatter(
        x=sel["year"], y=sel["imports"],
        mode="markers",
        marker=dict(size=16, color=SELECTION_COLOR, line=dict(color="white", width=2)),
        hovertemplate=f"{t('year')}: %{{x}}<br>{t('imports')}: %{{y:,.0f}}<extra></extra>",
        showlegend=False,
    )
)

line_chart.update_layout(
    title={"en": "Exports vs Imports Over Time", "hy": "Արտահանումն ընդդեմ Ներմուծման (Ժամանակի Ընթացքում)"}[st.session_state.get("lang","en")],
    xaxis_title=t("year"),
    yaxis_title={"en": "USD (thousands)", "hy": "ԱՄՆ դոլար (հազար)"}[st.session_state.get("lang","en")],
    hovermode="x unified",
)

# Chart 2: balance with selected bar highlighted
balance_df = df.copy()
balance_df["bar_color"] = balance_df["balance"].apply(lambda x: SURPLUS_COLOR if x >= 0 else DEFICIT_COLOR)
balance_df.loc[balance_df["year"] == selected_year, "bar_color"] = SELECTION_COLOR

bar_chart = px.bar(
    balance_df,
    x="year",
    y="balance",
    title={"en": "Trade Balance by Year", "hy": "Առևտրային Հաշվեկշիռը՝ ըստ Տարու"}[st.session_state.get("lang","en")],
    labels={"balance": {"en": "USD (thousands)", "hy": "ԱՄՆ դոլար (հազար)"}[st.session_state.get("lang","en")], "year": t("year")},
)
bar_chart.update_traces(
    marker_color=balance_df["bar_color"],
    hovertemplate=f"{t('year')}: %{{x}}<br>{t('balance')}: %{{y:,.0f}}<extra></extra>",
)

# Chart 3: turnover
turnover_chart = px.line(
    df,
    x="year",
    y="turnover",
    title={"en": "Total Trade Turnover Over Time", "hy": "Ընդհանուր Շրջանառություն՝ Ժամանակի Ընթացքում"}[st.session_state.get("lang","en")],
    markers=True,
    labels={"turnover": {"en": "USD (thousands)", "hy": "ԱՄՆ դոլար (հազար)"}[st.session_state.get("lang","en")], "year": t("year")},
)
turnover_chart.update_traces(
    line=dict(width=3),
    marker=dict(size=7),
    hovertemplate=f"{t('year')}: %{{x}}<br>{t('turnover')}: %{{y:,.0f}}<extra></extra>",
)

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(line_chart, use_container_width=True)
with c2:
    st.plotly_chart(bar_chart, use_container_width=True)

st.plotly_chart(turnover_chart, use_container_width=True)

with st.expander({"en": "Show underlying yearly data", "hy": "Ցույց տալ տարեկան տվյալների աղյուսակը"}[st.session_state.get("lang","en")], expanded=False):
    st.dataframe(
        df.style.format({"exports": "{:,.0f}", "imports": "{:,.0f}", "balance": "{:,.0f}", "turnover": "{:,.0f}"}),
        use_container_width=True,
    )