from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = BASE_DIR / "data" / "clean"

EXPORTS_PATH = CLEAN_DIR / "exports_country_products.csv"
IMPORTS_PATH = CLEAN_DIR / "imports_country_products.csv"


def format_value(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.1f}"


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    exports_df = pd.read_csv(EXPORTS_PATH)
    imports_df = pd.read_csv(IMPORTS_PATH)

    text_cols = ["period_label", "country_name", "product_code", "product_name", "unit"]
    numeric_cols = ["year_from", "year_to", "quantity_from", "value_from", "quantity_to", "value_to"]

    for df in (exports_df, imports_df):
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype("string").str.strip()

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    return exports_df, imports_df


def aggregate_countries(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("country_name", dropna=False)["value_to"]
        .sum(min_count=1)
        .reset_index(name="total_value")
        .sort_values("total_value", ascending=False)
        .reset_index(drop=True)
    )


def aggregate_country_products(df: pd.DataFrame, country: str) -> pd.DataFrame:
    filtered = df[df["country_name"] == country].copy()

    grouped = (
        filtered.groupby("product_code", dropna=False)
        .agg(
            product_name=("product_name", "first"),
            total_value=("value_to", "sum"),
        )
        .reset_index()
        .sort_values("total_value", ascending=False)
        .reset_index(drop=True)
    )

    grouped["display_label"] = grouped["product_name"].fillna(grouped["product_code"])
    return grouped


st.set_page_config(page_title="Partner Countries", layout="wide")

exports_df, imports_df = load_data()

st.title("Partner Countries")
st.write(
    "This page explores Armenia's trade partners using the flattened country-product tables. "
    "Country totals are based on `value_to`, and country product mixes are grouped by 4-digit product code."
)

# Shared filters
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

top_n = st.slider("Number of top countries/products to display", min_value=5, max_value=25, value=10)

exports_filtered = exports_df[exports_df["period_label"] == selected_period].copy()
imports_filtered = imports_df[imports_df["period_label"] == selected_period].copy()

exports_countries = aggregate_countries(exports_filtered)
imports_countries = aggregate_countries(imports_filtered)

# KPIs
exports_total = exports_filtered["value_to"].sum()
imports_total = imports_filtered["value_to"].sum()
export_country_count = exports_filtered["country_name"].nunique()
import_country_count = imports_filtered["country_name"].nunique()

kpi_cols = st.columns(4)
kpi_cols[0].metric("Period", selected_period)
kpi_cols[1].metric("Export Value (value_to)", format_value(exports_total))
kpi_cols[2].metric("Import Value (value_to)", format_value(imports_total))
kpi_cols[3].metric(
    "Distinct Countries",
    f"{export_country_count:,} exports / {import_country_count:,} imports",
)

# Top countries charts
top_export_countries = exports_countries.head(top_n).sort_values("total_value", ascending=True)
top_import_countries = imports_countries.head(top_n).sort_values("total_value", ascending=True)

export_country_chart = px.bar(
    top_export_countries,
    x="total_value",
    y="country_name",
    orientation="h",
    title=f"Top {top_n} Export Destination Countries",
    labels={"total_value": "Export Value", "country_name": "Country"},
)

import_country_chart = px.bar(
    top_import_countries,
    x="total_value",
    y="country_name",
    orientation="h",
    title=f"Top {top_n} Import Source Countries",
    labels={"total_value": "Import Value", "country_name": "Country"},
)

chart_cols = st.columns(2)
with chart_cols[0]:
    st.plotly_chart(export_country_chart, use_container_width=True)
with chart_cols[1]:
    st.plotly_chart(import_country_chart, use_container_width=True)

# Combined top-country comparison
comparison = pd.merge(
    exports_countries.rename(columns={"total_value": "exports_value"}),
    imports_countries.rename(columns={"total_value": "imports_value"}),
    on="country_name",
    how="outer",
)

comparison["exports_value"] = comparison["exports_value"].fillna(0)
comparison["imports_value"] = comparison["imports_value"].fillna(0)
comparison["total_activity"] = comparison["exports_value"] + comparison["imports_value"]

top_combined = comparison.sort_values("total_activity", ascending=False).head(top_n).copy()

comparison_long = top_combined.melt(
    id_vars=["country_name"],
    value_vars=["exports_value", "imports_value"],
    var_name="flow",
    value_name="value",
)

comparison_long["flow"] = comparison_long["flow"].replace(
    {"exports_value": "Exports", "imports_value": "Imports"}
)

comparison_chart = px.bar(
    comparison_long,
    x="country_name",
    y="value",
    color="flow",
    barmode="group",
    title=f"Top {top_n} Countries by Combined Trade Activity",
    labels={"country_name": "Country", "value": "Trade Value", "flow": "Flow"},
)

st.plotly_chart(comparison_chart, use_container_width=True)

# Country selector
all_countries = sorted(
    set(exports_filtered["country_name"].dropna().unique()).union(
        set(imports_filtered["country_name"].dropna().unique())
    )
)

default_country = all_countries[0] if all_countries else None
selected_country = st.selectbox("Select a country to inspect", options=all_countries, index=0 if default_country else None)

if selected_country:
    st.subheader(f"Country Detail: {selected_country}")

    export_country_products = aggregate_country_products(exports_filtered, selected_country)
    import_country_products = aggregate_country_products(imports_filtered, selected_country)

    detail_cols = st.columns(2)
    with detail_cols[0]:
        st.metric(
            "Exports to selected country",
            format_value(exports_filtered.loc[exports_filtered["country_name"] == selected_country, "value_to"].sum()),
        )
    with detail_cols[1]:
        st.metric(
            "Imports from selected country",
            format_value(imports_filtered.loc[imports_filtered["country_name"] == selected_country, "value_to"].sum()),
        )

    top_export_products = export_country_products.head(top_n).sort_values("total_value", ascending=True)
    top_import_products = import_country_products.head(top_n).sort_values("total_value", ascending=True)

    export_products_chart = px.bar(
        top_export_products,
        x="total_value",
        y="display_label",
        orientation="h",
        title=f"Top {top_n} Export Products for {selected_country}",
        labels={"total_value": "Export Value", "display_label": "Product"},
        hover_data={"product_code": True, "product_name": True},
    )

    import_products_chart = px.bar(
        top_import_products,
        x="total_value",
        y="display_label",
        orientation="h",
        title=f"Top {top_n} Import Products for {selected_country}",
        labels={"total_value": "Import Value", "display_label": "Product"},
        hover_data={"product_code": True, "product_name": True},
    )

    product_chart_cols = st.columns(2)
    with product_chart_cols[0]:
        st.plotly_chart(export_products_chart, use_container_width=True)
    with product_chart_cols[1]:
        st.plotly_chart(import_products_chart, use_container_width=True)

    st.subheader("Country Comparison Table")

    country_comparison = pd.merge(
        export_country_products[["product_code", "product_name", "total_value"]].rename(
            columns={"total_value": "exports_value"}
        ),
        import_country_products[["product_code", "product_name", "total_value"]].rename(
            columns={"total_value": "imports_value"}
        ),
        on="product_code",
        how="outer",
        suffixes=("_exp", "_imp"),
    )

    country_comparison["product_name"] = country_comparison["product_name_exp"].combine_first(
        country_comparison["product_name_imp"]
    )
    country_comparison = country_comparison.drop(columns=["product_name_exp", "product_name_imp"])

    country_comparison["exports_value"] = country_comparison["exports_value"].fillna(0)
    country_comparison["imports_value"] = country_comparison["imports_value"].fillna(0)
    country_comparison["net_trade"] = country_comparison["exports_value"] - country_comparison["imports_value"]

    country_comparison = country_comparison.sort_values(
        ["exports_value", "imports_value"], ascending=False
    )

    st.dataframe(
        country_comparison.style.format(
            {
                "exports_value": "{:,.1f}",
                "imports_value": "{:,.1f}",
                "net_trade": "{:,.1f}",
            }
        ),
        use_container_width=True,
    )