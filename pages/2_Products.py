from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = BASE_DIR / "data" / "clean"

EXPORTS_PATH = CLEAN_DIR / "exports_products.csv"
IMPORTS_PATH = CLEAN_DIR / "imports_products.csv"


def format_value(value: float) -> str:
    """Format numeric values for display."""
    if pd.isna(value):
        return "—"
    return f"{value:,.1f}"


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    exports_df = pd.read_csv(EXPORTS_PATH)
    imports_df = pd.read_csv(IMPORTS_PATH)

    # Clean text columns
    text_cols = ["period_label", "product_code", "product_name", "unit"]
    for df in (exports_df, imports_df):
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype("string").str.strip()

    # Clean numeric columns
    numeric_cols = ["year_from", "year_to", "quantity_from", "value_from", "quantity_to", "value_to"]
    for df in (exports_df, imports_df):
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    return exports_df, imports_df


def aggregate_products(df: pd.DataFrame, value_col: str = "value_to") -> pd.DataFrame:
    """
    Aggregate by product_code (stable key) and attach one representative product_name.
    We group by product_code and use the first non-null name as the display label.
    """
    grouped = (
        df.groupby("product_code", dropna=False)
        .agg(
            product_name=("product_name", "first"),
            total_value=(value_col, "sum"),
        )
        .reset_index()
    )

    grouped["display_label"] = grouped["product_name"].fillna(grouped["product_code"])
    return grouped.sort_values("total_value", ascending=False).reset_index(drop=True)


st.set_page_config(page_title="Products", layout="wide")

exports_df, imports_df = load_data()

st.title("Products")
st.write(
    "This page compares Armenia's exported and imported product groups using the cleaned "
    "`apr` product-level trade tables. Products are grouped by the 4-digit product code, "
    "and product names are shown as display labels."
)

# Shared period filter
all_periods = sorted(
    set(exports_df["period_label"].dropna().unique()).union(
        set(imports_df["period_label"].dropna().unique())
    )
)

selected_period = st.selectbox(
    "Select comparison period",
    options=all_periods,
    index=len(all_periods) - 1 if all_periods else 0,
)

top_n = st.slider("Number of top products to display", min_value=5, max_value=25, value=10)

exports_filtered = exports_df[exports_df["period_label"] == selected_period].copy()
imports_filtered = imports_df[imports_df["period_label"] == selected_period].copy()

exports_agg = aggregate_products(exports_filtered)
imports_agg = aggregate_products(imports_filtered)

# KPI row
exports_total = exports_filtered["value_to"].sum()
imports_total = imports_filtered["value_to"].sum()
distinct_export_products = exports_filtered["product_code"].nunique()
distinct_import_products = imports_filtered["product_code"].nunique()

kpi_cols = st.columns(4)
kpi_cols[0].metric("Period", selected_period)
kpi_cols[1].metric("Total Exports (value_to)", format_value(exports_total))
kpi_cols[2].metric("Total Imports (value_to)", format_value(imports_total))
kpi_cols[3].metric(
    "Distinct Products",
    f"{distinct_export_products:,} exports / {distinct_import_products:,} imports",
)

# Top products charts
top_exports = exports_agg.head(top_n).sort_values("total_value", ascending=True)
top_imports = imports_agg.head(top_n).sort_values("total_value", ascending=True)

export_chart = px.bar(
    top_exports,
    x="total_value",
    y="display_label",
    orientation="h",
    title=f"Top {top_n} Export Products by Value",
    labels={
        "total_value": "Export Value (value_to)",
        "display_label": "Product",
    },
    hover_data={"product_code": True, "product_name": True},
)

import_chart = px.bar(
    top_imports,
    x="total_value",
    y="display_label",
    orientation="h",
    title=f"Top {top_n} Import Products by Value",
    labels={
        "total_value": "Import Value (value_to)",
        "display_label": "Product",
    },
    hover_data={"product_code": True, "product_name": True},
)

chart_cols = st.columns(2)
with chart_cols[0]:
    st.plotly_chart(export_chart, use_container_width=True)
with chart_cols[1]:
    st.plotly_chart(import_chart, use_container_width=True)

# Side-by-side comparison table and chart
comparison = pd.merge(
    exports_agg[["product_code", "product_name", "total_value"]].rename(
        columns={"total_value": "exports_value"}
    ),
    imports_agg[["product_code", "product_name", "total_value"]].rename(
        columns={"total_value": "imports_value"}
    ),
    on="product_code",
    how="outer",
    suffixes=("_exp", "_imp"),
)

comparison["product_name"] = comparison["product_name_exp"].combine_first(comparison["product_name_imp"])
comparison = comparison.drop(columns=["product_name_exp", "product_name_imp"])

comparison["exports_value"] = comparison["exports_value"].fillna(0)
comparison["imports_value"] = comparison["imports_value"].fillna(0)
comparison["net_trade"] = comparison["exports_value"] - comparison["imports_value"]
comparison["display_label"] = comparison["product_name"].fillna(comparison["product_code"])

comparison_top = (
    comparison.assign(total_activity=comparison["exports_value"] + comparison["imports_value"])
    .sort_values("total_activity", ascending=False)
    .head(top_n)
    .copy()
)

comparison_long = comparison_top.melt(
    id_vars=["product_code", "product_name", "display_label"],
    value_vars=["exports_value", "imports_value"],
    var_name="flow",
    value_name="value",
)

comparison_long["flow"] = comparison_long["flow"].replace(
    {
        "exports_value": "Exports",
        "imports_value": "Imports",
    }
)

comparison_chart = px.bar(
    comparison_long,
    x="display_label",
    y="value",
    color="flow",
    barmode="group",
    title=f"Top {top_n} Products by Combined Trade Activity",
    labels={
        "display_label": "Product",
        "value": "Trade Value",
        "flow": "Flow",
    },
    hover_data={"product_code": True, "product_name": True},
)

st.plotly_chart(comparison_chart, use_container_width=True)

# Comparison table
st.subheader("Product Comparison Table")

display_table = comparison.sort_values("exports_value", ascending=False).copy()
display_table = display_table[
    ["product_code", "product_name", "exports_value", "imports_value", "net_trade"]
]

st.dataframe(
    display_table.style.format(
        {
            "exports_value": "{:,.1f}",
            "imports_value": "{:,.1f}",
            "net_trade": "{:,.1f}",
        }
    ),
    use_container_width=True,
)