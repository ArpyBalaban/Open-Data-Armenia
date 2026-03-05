from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = BASE_DIR / "data" / "clean"

EXPORTS_PATH = CLEAN_DIR / "exports_country_products.csv"
IMPORTS_PATH = CLEAN_DIR / "imports_country_products.csv"
COUNTRY_TRANSLATIONS_PATH = CLEAN_DIR / "country_translations.csv"

EXPORT_COLOR = "#1f77b4"
IMPORT_COLOR = "#d62728"


def format_value(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.1f}"


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    exports_df = pd.read_csv(EXPORTS_PATH)
    imports_df = pd.read_csv(IMPORTS_PATH)
    country_tr = pd.read_csv(COUNTRY_TRANSLATIONS_PATH)

    # Clean / normalize
    text_cols = ["period_label", "country_name", "product_code", "product_name", "unit"]
    numeric_cols = ["year_from", "year_to", "quantity_from", "value_from", "quantity_to", "value_to"]

    for df in (exports_df, imports_df):
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype("string").str.strip()
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    country_tr["country_name_am"] = country_tr["country_name_am"].astype("string").str.strip()
    country_tr["country_name_en"] = country_tr["country_name_en"].astype("string").str.strip()
    country_tr["iso3"] = country_tr["iso3"].astype("string").str.strip()

    return exports_df, imports_df, country_tr


def aggregate_countries_value(df: pd.DataFrame) -> pd.DataFrame:
    """Country totals by value_to (safe to aggregate)."""
    return (
        df.groupby("country_name", dropna=False)["value_to"]
        .sum(min_count=1)
        .reset_index(name="total_value")
        .sort_values("total_value", ascending=False)
        .reset_index(drop=True)
    )


def aggregate_country_products_value(df: pd.DataFrame, country: str) -> pd.DataFrame:
    """Product totals within a country by value_to."""
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


def attach_country_en_iso(country_totals: pd.DataFrame, country_tr: pd.DataFrame) -> pd.DataFrame:
    """Attach English country name + ISO3 to an Armenian country totals table."""
    out = country_totals.merge(
        country_tr[["country_name_am", "country_name_en", "iso3"]],
        left_on="country_name",
        right_on="country_name_am",
        how="left",
    )
    out["country_name_en"] = out["country_name_en"].fillna(out["country_name"])  # fallback
    return out


st.set_page_config(page_title="Partner Countries", layout="wide")

exports_df, imports_df, country_tr = load_data()

st.title("Partner Countries")
st.caption(
    "Explore Armenia’s trade partners using country–product trade tables. "
    "All totals are based on trade value (value_to)."
)

# -----------------------------
# Filters
# -----------------------------
all_periods = sorted(
    set(exports_df["period_label"].dropna().unique()).union(
        set(imports_df["period_label"].dropna().unique())
    )
)

filter_col1, filter_col2 = st.columns([2, 1])
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

# Country totals
exports_countries_am = aggregate_countries_value(exports_filtered)
imports_countries_am = aggregate_countries_value(imports_filtered)

exports_countries = attach_country_en_iso(exports_countries_am, country_tr)
imports_countries = attach_country_en_iso(imports_countries_am, country_tr)

# KPIs
exports_total = exports_filtered["value_to"].sum()
imports_total = imports_filtered["value_to"].sum()
export_country_count = exports_filtered["country_name"].nunique()
import_country_count = imports_filtered["country_name"].nunique()

kpi_cols = st.columns(4)
kpi_cols[0].metric("Selected Period", selected_period)
kpi_cols[1].metric("Total Exports (value_to)", format_value(exports_total))
kpi_cols[2].metric("Total Imports (value_to)", format_value(imports_total))
kpi_cols[3].metric(
    "Distinct Countries",
    f"{export_country_count:,} exports / {import_country_count:,} imports",
)

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3 = st.tabs(["Top Countries", "Country Detail", "Map"])

# -----------------------------
# Tab 1: Top Countries
# -----------------------------
with tab1:
    st.markdown("Ranked view of top partner countries by trade value.")

    top_export_countries = exports_countries.head(top_n).sort_values("total_value", ascending=True)
    top_import_countries = imports_countries.head(top_n).sort_values("total_value", ascending=True)

    export_country_chart = px.bar(
        top_export_countries,
        x="total_value",
        y="country_name_en",
        orientation="h",
        title=f"Top {top_n} Export Destination Countries",
        labels={"total_value": "Export Value", "country_name_en": "Country"},
        color_discrete_sequence=[EXPORT_COLOR],
    )

    import_country_chart = px.bar(
        top_import_countries,
        x="total_value",
        y="country_name_en",
        orientation="h",
        title=f"Top {top_n} Import Source Countries",
        labels={"total_value": "Import Value", "country_name_en": "Country"},
        color_discrete_sequence=[IMPORT_COLOR],
    )

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(export_country_chart, use_container_width=True)
    with c2:
        st.plotly_chart(import_country_chart, use_container_width=True)

    # Combined comparison
    comparison = pd.merge(
        exports_countries[["country_name", "country_name_en", "total_value"]].rename(
            columns={"total_value": "exports_value"}
        ),
        imports_countries[["country_name", "country_name_en", "total_value"]].rename(
            columns={"total_value": "imports_value"}
        ),
        on="country_name",
        how="outer",
        suffixes=("_exp", "_imp"),
    )

    comparison["country_name_en"] = comparison["country_name_en_exp"].combine_first(
        comparison["country_name_en_imp"]
    )
    comparison = comparison.drop(columns=["country_name_en_exp", "country_name_en_imp"])

    comparison["exports_value"] = comparison["exports_value"].fillna(0)
    comparison["imports_value"] = comparison["imports_value"].fillna(0)
    comparison["total_activity"] = comparison["exports_value"] + comparison["imports_value"]

    top_combined = comparison.sort_values("total_activity", ascending=False).head(top_n).copy()

    comparison_long = top_combined.melt(
        id_vars=["country_name_en"],
        value_vars=["exports_value", "imports_value"],
        var_name="flow",
        value_name="value",
    )
    comparison_long["flow"] = comparison_long["flow"].replace(
        {"exports_value": "Exports", "imports_value": "Imports"}
    )

    comparison_chart = px.bar(
        comparison_long,
        x="country_name_en",
        y="value",
        color="flow",
        barmode="group",
        title=f"Top {top_n} Countries by Combined Trade Activity",
        labels={"country_name_en": "Country", "value": "Trade Value", "flow": "Flow"},
        color_discrete_map={"Exports": EXPORT_COLOR, "Imports": IMPORT_COLOR},
    )

    st.plotly_chart(comparison_chart, use_container_width=True)

# -----------------------------
# Tab 2: Country Detail
# -----------------------------
with tab2:
    st.markdown("Select a country to explore product composition for exports and imports.")

    all_countries_am = sorted(
        set(exports_filtered["country_name"].dropna().unique()).union(
            set(imports_filtered["country_name"].dropna().unique())
        )
    )

    # Show the dropdown in English, but keep Armenian key internally
    country_dropdown = country_tr[country_tr["country_name_am"].isin(all_countries_am)].copy()
    # Keep unknowns too (may have blank iso3)
    missing_in_tr = [c for c in all_countries_am if c not in set(country_dropdown["country_name_am"])]
    if missing_in_tr:
        country_dropdown = pd.concat(
            [
                country_dropdown,
                pd.DataFrame(
                    {
                        "country_name_am": missing_in_tr,
                        "country_name_en": missing_in_tr,
                        "iso3": ["" for _ in missing_in_tr],
                    }
                ),
            ],
            ignore_index=True,
        )

    country_dropdown = country_dropdown.sort_values("country_name_en")
    options_en = country_dropdown["country_name_en"].tolist()
    en_to_am = dict(zip(country_dropdown["country_name_en"], country_dropdown["country_name_am"]))

    selected_country_en = st.selectbox("Select a country", options=options_en, index=0 if options_en else None)
    selected_country_am = en_to_am.get(selected_country_en)

    if selected_country_am:
        exports_country_value = exports_filtered.loc[
            exports_filtered["country_name"] == selected_country_am, "value_to"
        ].sum()
        imports_country_value = imports_filtered.loc[
            imports_filtered["country_name"] == selected_country_am, "value_to"
        ].sum()
        total_trade = exports_country_value + imports_country_value

        k1, k2, k3 = st.columns(3)
        k1.metric("Exports (value_to)", format_value(exports_country_value))
        k2.metric("Imports (value_to)", format_value(imports_country_value))
        k3.metric("Total Trade", format_value(total_trade))

        export_products = aggregate_country_products_value(exports_filtered, selected_country_am).head(top_n)
        import_products = aggregate_country_products_value(imports_filtered, selected_country_am).head(top_n)

        # Charts
        c1, c2 = st.columns(2)

        export_products_chart = px.bar(
            export_products.sort_values("total_value", ascending=True),
            x="total_value",
            y="display_label",
            orientation="h",
            title=f"Top {top_n} Export Products — {selected_country_en}",
            labels={"total_value": "Export Value", "display_label": "Product"},
            color_discrete_sequence=[EXPORT_COLOR],
        )

        import_products_chart = px.bar(
            import_products.sort_values("total_value", ascending=True),
            x="total_value",
            y="display_label",
            orientation="h",
            title=f"Top {top_n} Import Products — {selected_country_en}",
            labels={"total_value": "Import Value", "display_label": "Product"},
            color_discrete_sequence=[IMPORT_COLOR],
        )

        with c1:
            st.plotly_chart(export_products_chart, use_container_width=True)
        with c2:
            st.plotly_chart(import_products_chart, use_container_width=True)

        with st.expander("Show country product comparison table", expanded=False):
            country_comparison = pd.merge(
                export_products[["product_code", "product_name", "total_value"]].rename(
                    columns={"total_value": "exports_value"}
                ),
                import_products[["product_code", "product_name", "total_value"]].rename(
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
                    {"exports_value": "{:,.1f}", "imports_value": "{:,.1f}", "net_trade": "{:,.1f}"}
                ),
                use_container_width=True,
            )

# -----------------------------
# Tab 3: Map (choropleth)
# -----------------------------
with tab3:
    st.markdown("Geographic distribution of trade value by partner country.")

    flow = st.radio("Flow", options=["Exports", "Imports"], horizontal=True)

    if flow == "Exports":
        map_df = exports_countries.copy()
        value_label = "Export Value"
        color_scale = "Blues"
    else:
        map_df = imports_countries.copy()
        value_label = "Import Value"
        color_scale = "Reds"

    # Keep only mappable countries
    map_df["iso3"] = map_df["iso3"].fillna("").astype(str).str.strip()
    mappable = map_df[map_df["iso3"] != ""].copy()

    st.caption(
        f"Showing {flow.lower()} totals for period: {selected_period}. "
        "Countries without ISO codes (e.g., 'Unknown country') are excluded from the map."
    )

    if mappable.empty:
        st.warning("No mappable countries found for this selection.")
    else:
        choropleth = px.choropleth(
            mappable,
            locations="iso3",
            color="total_value",
            hover_name="country_name_en",
            color_continuous_scale=color_scale,
            labels={"total_value": value_label},
        )

        choropleth.update_traces(
            hovertemplate="<b>%{hovertext}</b><br>"
            + f"{value_label}: %{{z:,.1f}}<extra></extra>"
        )

        choropleth.update_layout(
            margin=dict(l=0, r=0, t=30, b=0),
        )

        st.plotly_chart(choropleth, use_container_width=True)

        with st.expander("Show top countries for this map", expanded=False):
            st.dataframe(
                mappable.sort_values("total_value", ascending=False)[
                    ["country_name_en", "iso3", "total_value"]
                ].head(25).style.format({"total_value": "{:,.1f}"}),
                use_container_width=True,
            )