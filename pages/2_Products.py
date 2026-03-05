from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = BASE_DIR / "data" / "clean"

EXPORTS_PATH = CLEAN_DIR / "exports_products.csv"
IMPORTS_PATH = CLEAN_DIR / "imports_products.csv"

EXPORT_COLOR = "#1f77b4"
IMPORT_COLOR = "#d62728"


def format_value(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.1f}"


def shorten_label(text: str, max_len: int = 45) -> str:
    if pd.isna(text):
        return "Unknown"
    text = str(text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    exports_df = pd.read_csv(EXPORTS_PATH)
    imports_df = pd.read_csv(IMPORTS_PATH)

    text_cols = ["period_label", "product_code", "product_name", "unit"]
    numeric_cols = ["year_from", "year_to", "quantity_from", "value_from", "quantity_to", "value_to"]

    for df in (exports_df, imports_df):
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype("string").str.strip()

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    return exports_df, imports_df


def aggregate_products(df: pd.DataFrame, value_col: str = "value_to") -> pd.DataFrame:
    grouped = (
        df.groupby("product_code", dropna=False)
        .agg(
            product_name=("product_name", "first"),
            total_value=(value_col, "sum"),
        )
        .reset_index()
        .sort_values("total_value", ascending=False)
        .reset_index(drop=True)
    )

    grouped["full_label"] = grouped["product_name"].fillna(grouped["product_code"])
    grouped["short_label"] = grouped["full_label"].apply(shorten_label)
    return grouped


st.set_page_config(page_title="Products", layout="wide")

exports_df, imports_df = load_data()

st.title("Products")
st.caption(
    "Compare Armenia’s exported and imported product groups using the cleaned product-level trade tables. "
    "Products are grouped by 4-digit product code for stable aggregation."
)

# -----------------------------
# Filters
# -----------------------------
filter_col1, filter_col2 = st.columns([2, 1])

all_periods = sorted(
    set(exports_df["period_label"].dropna().unique()).union(
        set(imports_df["period_label"].dropna().unique())
    )
)

with filter_col1:
    selected_period = st.selectbox(
        "Comparison period",
        options=all_periods,
        index=len(all_periods) - 1 if all_periods else 0,
    )

with filter_col2:
    top_n = st.slider("Top N", min_value=5, max_value=25, value=10)

exports_filtered = exports_df[exports_df["period_label"] == selected_period].copy()
imports_filtered = imports_df[imports_df["period_label"] == selected_period].copy()

exports_agg = aggregate_products(exports_filtered)
imports_agg = aggregate_products(imports_filtered)

# -----------------------------
# KPIs
# -----------------------------
exports_total = exports_filtered["value_to"].sum()
imports_total = imports_filtered["value_to"].sum()
distinct_export_products = exports_filtered["product_code"].nunique()
distinct_import_products = imports_filtered["product_code"].nunique()

top_export_row = exports_agg.iloc[0] if not exports_agg.empty else None
top_import_row = imports_agg.iloc[0] if not imports_agg.empty else None

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Selected Period", selected_period)
kpi2.metric("Total Export Value", format_value(exports_total))
kpi3.metric("Total Import Value", format_value(imports_total))
kpi4.metric(
    "Distinct Products",
    f"{distinct_export_products:,} / {distinct_import_products:,}",
    help="Exports / Imports",
)

# -----------------------------
# Shared comparison data
# -----------------------------
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
comparison["total_activity"] = comparison["exports_value"] + comparison["imports_value"]
comparison["full_label"] = comparison["product_name"].fillna(comparison["product_code"])
comparison["short_label"] = comparison["full_label"].apply(shorten_label)

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3 = st.tabs(["Top Products", "Treemaps", "Comparison"])

with tab1:
    st.markdown("Ranked view of the largest product groups by trade value.")

    top_exports = exports_agg.head(top_n).sort_values("total_value", ascending=True)
    top_imports = imports_agg.head(top_n).sort_values("total_value", ascending=True)

    export_chart = px.bar(
        top_exports,
        x="total_value",
        y="short_label",
        orientation="h",
        title=f"Top {top_n} Export Products",
        labels={"total_value": "Export Value", "short_label": "Product"},
        color_discrete_sequence=[EXPORT_COLOR],
    )
    export_chart.update_traces(
        customdata=top_exports[["product_code", "full_label"]].values,
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>"
            "Code: %{customdata[0]}<br>"
            "Export Value: %{x:,.1f}<extra></extra>"
        )
    )
    export_chart.update_layout(yaxis={"categoryorder": "total ascending"})

    import_chart = px.bar(
        top_imports,
        x="total_value",
        y="short_label",
        orientation="h",
        title=f"Top {top_n} Import Products",
        labels={"total_value": "Import Value", "short_label": "Product"},
        color_discrete_sequence=[IMPORT_COLOR],
    )
    import_chart.update_traces(
        customdata=top_imports[["product_code", "full_label"]].values,
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>"
            "Code: %{customdata[0]}<br>"
            "Import Value: %{x:,.1f}<extra></extra>"
        )
    )
    import_chart.update_layout(yaxis={"categoryorder": "total ascending"})

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(export_chart, use_container_width=True)
    with c2:
        st.plotly_chart(import_chart, use_container_width=True)

with tab2:
    st.markdown("A more visual view of product composition using treemaps.")

    export_treemap_data = exports_agg.head(top_n).copy()
    import_treemap_data = imports_agg.head(top_n).copy()

    export_treemap = px.treemap(
        export_treemap_data,
        path=["short_label"],
        values="total_value",
        title=f"Export Composition (Top {top_n})",
        color="total_value",
        color_continuous_scale="Blues",
    )
    export_treemap.update_traces(
        customdata=export_treemap_data[["product_code", "full_label"]].values,
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>"
            "Code: %{customdata[0]}<br>"
            "Export Value: %{value:,.1f}<extra></extra>"
        )
    )
    st.plotly_chart(export_treemap, use_container_width=True)

    import_treemap = px.treemap(
        import_treemap_data,
        path=["short_label"],
        values="total_value",
        title=f"Import Composition (Top {top_n})",
        color="total_value",
        color_continuous_scale="Reds",
    )
    import_treemap.update_traces(
        customdata=import_treemap_data[["product_code", "full_label"]].values,
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>"
            "Code: %{customdata[0]}<br>"
            "Import Value: %{value:,.1f}<extra></extra>"
        )
    )
    st.plotly_chart(import_treemap, use_container_width=True)

with tab3:
    st.markdown(
        "Compare exports and imports side by side. This view uses **value**, which is safe to aggregate "
        "even when quantity units differ."
    )

    comparison_top = comparison.sort_values("total_activity", ascending=False).head(top_n).copy()

    comparison_long = comparison_top.melt(
        id_vars=["product_code", "full_label", "short_label"],
        value_vars=["exports_value", "imports_value"],
        var_name="flow",
        value_name="value",
    )

    comparison_long["flow"] = comparison_long["flow"].replace(
        {"exports_value": "Exports", "imports_value": "Imports"}
    )

    comparison_chart = px.bar(
        comparison_long,
        x="short_label",
        y="value",
        color="flow",
        barmode="group",
        title=f"Top {top_n} Products by Combined Trade Activity",
        labels={"short_label": "Product", "value": "Trade Value", "flow": "Flow"},
        color_discrete_map={"Exports": EXPORT_COLOR, "Imports": IMPORT_COLOR},
    )
    comparison_chart.update_traces(
        customdata=comparison_long[["product_code", "full_label"]].values,
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>"
            "Code: %{customdata[0]}<br>"
            "Flow: %{fullData.name}<br>"
            "Value: %{y:,.1f}<extra></extra>"
        )
    )

    st.plotly_chart(comparison_chart, use_container_width=True)

    with st.expander("Show product comparison table", expanded=False):
        display_table = comparison[
            ["product_code", "product_name", "exports_value", "imports_value", "net_trade"]
        ].sort_values(["exports_value", "imports_value"], ascending=False)

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

# -----------------------------
# Bottom insight cards
# -----------------------------
st.markdown("---")
st.subheader("Key Takeaways")

insight1, insight2, insight3 = st.columns(3)

top_net_export = comparison.sort_values("net_trade", ascending=False).head(1)
top_net_import = comparison.sort_values("net_trade", ascending=True).head(1)

with insight1:
    if top_export_row is not None:
        st.info(
            f"**Top export product**\n\n{top_export_row['full_label']} "
            f"(`{top_export_row['product_code']}`)\n\n{format_value(top_export_row['total_value'])}"
        )

with insight2:
    if top_import_row is not None:
        st.info(
            f"**Top import product**\n\n{top_import_row['full_label']} "
            f"(`{top_import_row['product_code']}`)\n\n{format_value(top_import_row['total_value'])}"
        )

with insight3:
    net_balance = exports_total - imports_total
    if net_balance >= 0:
        st.success(f"**Net balance (Exports - Imports)**\n\n{format_value(net_balance)}")
    else:
        st.warning(f"**Net balance (Exports - Imports)**\n\n{format_value(net_balance)}")