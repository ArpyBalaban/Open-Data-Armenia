from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.i18n import t, get_lang


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "clean" / "trade_overview.csv"

SELECTION_COLOR = "#0F766E"
EXPORT_COLOR = "#1f77b4"
IMPORT_COLOR = "#d62728"
SURPLUS_COLOR = "#1f77b4"
DEFICIT_COLOR = "#d62728"


def usd_m(value_thousand: float) -> float:
    """Convert thousand USD -> million USD."""
    return value_thousand / 1000 if pd.notna(value_thousand) else float("nan")


def format_usd_m(value_thousand: float) -> str:
    """Format thousand USD as $X.XM."""
    if pd.isna(value_thousand):
        return "—"
    return f"${usd_m(value_thousand):,.1f}M"


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values("year").reset_index(drop=True)
    for col in ["year", "exports", "imports", "balance", "turnover"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Display columns in million USD
    df["exports_m"] = df["exports"] / 1000
    df["imports_m"] = df["imports"] / 1000
    df["balance_m"] = df["balance"] / 1000
    df["turnover_m"] = df["turnover"] / 1000

    return df


st.set_page_config(page_title=t("trade_overview_title"), layout="wide")

lang = get_lang()
df = load_data()

st.title(t("trade_overview_title"))
st.write(
    {
        "en": "Yearly overview of exports, imports, trade balance, and total turnover.",
        "hy": "Տարեկան ամփոփ պատկեր՝ արտահանում, ներմուծում, հաշվեկշիռ և ընդհանուր շրջանառություն։",
    }[lang]
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
        "en": f"In {int(selected_row['year'])}, exports were {format_usd_m(selected_row['exports'])}, "
              f"imports were {format_usd_m(selected_row['imports'])}, and balance was {format_usd_m(selected_row['balance'])}.",
        "hy": f"{int(selected_row['year'])}-ին արտահանումը եղել է {format_usd_m(selected_row['exports'])}, "
              f"ներմուծումը՝ {format_usd_m(selected_row['imports'])}, հաշվեկշիռը՝ {format_usd_m(selected_row['balance'])}։",
    }[lang]
)

metric_cols = st.columns(5)
metric_cols[0].metric(t("year"), str(int(selected_row["year"])))
metric_cols[1].metric(t("exports"), format_usd_m(selected_row["exports"]))
metric_cols[2].metric(t("imports"), format_usd_m(selected_row["imports"]))
metric_cols[3].metric(t("balance"), format_usd_m(selected_row["balance"]))
metric_cols[4].metric(t("turnover"), format_usd_m(selected_row["turnover"]))

# Chart 1: exports vs imports (million USD) + highlighted selected year
line_chart = go.Figure()
line_chart.add_trace(
    go.Scatter(
        x=df["year"], y=df["exports_m"],
        mode="lines+markers",
        name=t("exports"),
        line=dict(color=EXPORT_COLOR, width=3),
        marker=dict(size=7, color=EXPORT_COLOR),
        hovertemplate=f"{t('year')}: %{{x}}<br>{t('exports')}: $%{{y:,.1f}}M<extra></extra>",
    )
)
line_chart.add_trace(
    go.Scatter(
        x=df["year"], y=df["imports_m"],
        mode="lines+markers",
        name=t("imports"),
        line=dict(color=IMPORT_COLOR, width=3),
        marker=dict(size=7, color=IMPORT_COLOR),
        hovertemplate=f"{t('year')}: %{{x}}<br>{t('imports')}: $%{{y:,.1f}}M<extra></extra>",
    )
)

sel = df[df["year"] == selected_year]
line_chart.add_trace(
    go.Scatter(
        x=sel["year"], y=sel["exports_m"],
        mode="markers",
        marker=dict(size=16, color=SELECTION_COLOR, line=dict(color="white", width=2)),
        hovertemplate=f"{t('year')}: %{{x}}<br>{t('exports')}: $%{{y:,.1f}}M<extra></extra>",
        showlegend=False,
    )
)
line_chart.add_trace(
    go.Scatter(
        x=sel["year"], y=sel["imports_m"],
        mode="markers",
        marker=dict(size=16, color=SELECTION_COLOR, line=dict(color="white", width=2)),
        hovertemplate=f"{t('year')}: %{{x}}<br>{t('imports')}: $%{{y:,.1f}}M<extra></extra>",
        showlegend=False,
    )
)

line_chart.update_layout(
    title={"en": "Exports vs Imports Over Time", "hy": "Արտահանումն ընդդեմ Ներմուծման (Ժամանակի Ընթացքում)"}[lang],
    xaxis_title=t("year"),
    yaxis_title={"en": "USD (millions)", "hy": "ԱՄՆ դոլար (միլիոն)"}[lang],
    hovermode="x unified",
)

# Chart 2: balance (million USD) with selected bar highlighted
balance_df = df.copy()
balance_df["bar_color"] = balance_df["balance"].apply(lambda x: SURPLUS_COLOR if x >= 0 else DEFICIT_COLOR)
balance_df.loc[balance_df["year"] == selected_year, "bar_color"] = SELECTION_COLOR

bar_chart = px.bar(
    balance_df,
    x="year",
    y="balance_m",
    title={"en": "Trade Balance by Year", "hy": "Առևտրային Հաշվեկշիռը՝ ըստ Տարու"}[lang],
    labels={"balance_m": {"en": "USD (millions)", "hy": "ԱՄՆ դոլար (միլիոն)"}[lang], "year": t("year")},
)
bar_chart.update_traces(
    marker_color=balance_df["bar_color"],
    hovertemplate=f"{t('year')}: %{{x}}<br>{t('balance')}: $%{{y:,.1f}}M<extra></extra>",
)

# Chart 3: turnover (million USD)
turnover_chart = px.line(
    df,
    x="year",
    y="turnover_m",
    title={"en": "Total Trade Turnover Over Time", "hy": "Ընդհանուր Շրջանառություն՝ Ժամանակի Ընթացքում"}[lang],
    markers=True,
    labels={"turnover_m": {"en": "USD (millions)", "hy": "ԱՄՆ դոլար (միլիոն)"}[lang], "year": t("year")},
)
turnover_chart.update_traces(
    line=dict(width=3),
    marker=dict(size=7),
    hovertemplate=f"{t('year')}: %{{x}}<br>{t('turnover')}: $%{{y:,.1f}}M<extra></extra>",
)

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(line_chart, use_container_width=True)
with c2:
    st.plotly_chart(bar_chart, use_container_width=True)

st.plotly_chart(turnover_chart, use_container_width=True)

with st.expander({"en": "Show underlying yearly data (thousand USD)", "hy": "Ցույց տալ տարեկան տվյալները (հազար ԱՄՆ դոլար)"}[lang], expanded=False):
    st.dataframe(
        df[["year", "exports", "imports", "balance", "turnover"]].style.format(
            {"exports": "{:,.0f}", "imports": "{:,.0f}", "balance": "{:,.0f}", "turnover": "{:,.0f}"}
        ),
        use_container_width=True,
    )