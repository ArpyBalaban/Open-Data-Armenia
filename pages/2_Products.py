from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.i18n import get_lang, t


BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = BASE_DIR / "data" / "clean"

EXPORTS_PATH = CLEAN_DIR / "exports_products.csv"
IMPORTS_PATH = CLEAN_DIR / "imports_products.csv"
PRODUCT_TR_PATH = CLEAN_DIR / "product_translations.csv"

EXPORT_COLOR = "#1f77b4"
IMPORT_COLOR = "#d62728"


def format_value(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.1f}"


def shorten_label(text: str, max_len: int = 45) -> str:
    if pd.isna(text):
        return "Unknown"
    s = str(text).strip()
    return s if len(s) <= max_len else s[: max_len - 1].rstrip() + "…"


def normalize_period_label(raw: str) -> str:
    return str(raw).strip().replace("-", "–")


def period_display_label(raw: str, lang: str) -> str:
    raw = str(raw).strip()
    if "կիսամյակ" in raw:
        # e.g., "I կիսամյակ 2020-2021" -> "2020–2021 (H1)"
        base = normalize_period_label(raw.split()[-1])
        suffix = "I կիսամյակ" if lang == "hy" else "H1"
    else:
        base = normalize_period_label(raw)
        suffix = "Ամբողջ տարի" if lang == "hy" else "Full year"
    return f"{base} ({suffix})"


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    exports_df = pd.read_csv(EXPORTS_PATH, dtype={"product_code": str})
    imports_df = pd.read_csv(IMPORTS_PATH, dtype={"product_code": str})

    # product_translations has an extra first line: "product_translations"
    prod_tr = pd.read_csv(
        PRODUCT_TR_PATH,
        sep=";",
        skiprows=1,
        encoding="utf-8-sig",
        dtype=str,
    )
    prod_tr.columns = prod_tr.columns.str.strip()

    # Normalize trade tables
    for df in (exports_df, imports_df):
        df["period_label"] = df["period_label"].astype("string").str.strip()
        df["product_code"] = df["product_code"].astype(str).str.strip().str.zfill(4)
        df["product_name"] = df["product_name"].astype("string").str.strip()
        for col in ["year_from", "year_to", "quantity_from", "value_from", "quantity_to", "value_to"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalize translations
    prod_tr["product_code"] = prod_tr["product_code"].astype(str).str.strip().str.zfill(4)
    prod_tr["product_name_am"] = prod_tr["product_name_am"].astype("string").str.strip()
    prod_tr["product_name_en"] = prod_tr["product_name_en"].astype("string").str.strip()

    return exports_df, imports_df, prod_tr


def aggregate_products_value(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("product_code", dropna=False)["value_to"]
        .sum(min_count=1)
        .reset_index(name="total_value")
        .sort_values("total_value", ascending=False)
        .reset_index(drop=True)
    )


st.set_page_config(page_title=t("products_title"), layout="wide")

lang = get_lang()
exports_df, imports_df, prod_tr = load_data()
name_col = "product_name_en" if lang == "en" else "product_name_am"

st.title(t("products_title"))
st.caption(
    {
        "en": "Products are grouped by 4-digit HS code. Labels switch by language.",
        "hy": "Ապրանքները խմբավորված են 4-նիշ HS կոդով։ Պիտակները փոխվում են լեզվի ընտրությունից կախված։",
    }[lang]
)

# --- Period dropdown with display labels (Style A)
all_periods_raw = sorted(
    set(exports_df["period_label"].dropna().unique()).union(
        set(imports_df["period_label"].dropna().unique())
    )
)
period_options = {period_display_label(p, lang): p for p in all_periods_raw}
default_key = period_display_label(all_periods_raw[-1], lang) if all_periods_raw else None

col1, col2 = st.columns([2, 1])
with col1:
    selected_period_key = st.selectbox(
        t("comparison_period"),
        options=list(period_options.keys()),
        index=list(period_options.keys()).index(default_key) if default_key in period_options else 0,
    )
with col2:
    top_n = st.slider(t("top_n"), min_value=5, max_value=25, value=10)

selected_period = period_options[selected_period_key]

exports_f = exports_df[exports_df["period_label"] == selected_period].copy()
imports_f = imports_df[imports_df["period_label"] == selected_period].copy()

# Aggregate and attach translations
exports_agg = aggregate_products_value(exports_f).merge(
    prod_tr[["product_code", "product_name_am", "product_name_en"]],
    on="product_code",
    how="left",
)
imports_agg = aggregate_products_value(imports_f).merge(
    prod_tr[["product_code", "product_name_am", "product_name_en"]],
    on="product_code",
    how="left",
)

exports_agg["full_label"] = exports_agg[name_col].fillna(exports_agg["product_code"])
imports_agg["full_label"] = imports_agg[name_col].fillna(imports_agg["product_code"])
exports_agg["short_label"] = exports_agg["full_label"].apply(shorten_label)
imports_agg["short_label"] = imports_agg["full_label"].apply(shorten_label)

# KPIs
exports_total = exports_f["value_to"].sum()
imports_total = imports_f["value_to"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric(t("selected_period"), selected_period_key)
k2.metric(t("total_exports_value"), format_value(exports_total))
k3.metric(t("total_imports_value"), format_value(imports_total))
k4.metric(
    t("distinct_products"),
    f"{exports_f['product_code'].nunique():,} / {imports_f['product_code'].nunique():,}",
    help={"en": "Exports / Imports", "hy": "Արտահանում / Ներմուծում"}[lang],
)

# Shared comparison frame
comparison = pd.merge(
    exports_agg[["product_code", "full_label", "short_label", "total_value"]].rename(columns={"total_value": "exports_value"}),
    imports_agg[["product_code", "full_label", "short_label", "total_value"]].rename(columns={"total_value": "imports_value"}),
    on="product_code",
    how="outer",
    suffixes=("_exp", "_imp"),
)

comparison["exports_value"] = comparison["exports_value"].fillna(0)
comparison["imports_value"] = comparison["imports_value"].fillna(0)
comparison["net_trade"] = comparison["exports_value"] - comparison["imports_value"]
comparison["total_activity"] = comparison["exports_value"] + comparison["imports_value"]

comparison["full_label"] = (
    comparison["full_label_exp"].combine_first(comparison["full_label_imp"]).fillna(comparison["product_code"])
)
comparison["short_label"] = (
    comparison["short_label_exp"].combine_first(comparison["short_label_imp"]).fillna(comparison["product_code"])
)
comparison = comparison.drop(columns=["full_label_exp", "full_label_imp", "short_label_exp", "short_label_imp"])

tab1, tab2, tab3 = st.tabs(
    [
        {"en": "Top Products", "hy": "Թոփ Ապրանքներ"}[lang],
        {"en": "Treemaps", "hy": "Թրիմափներ"}[lang],
        {"en": "Comparison", "hy": "Համեմատություն"}[lang],
    ]
)

with tab1:
    top_exports = exports_agg.head(top_n).sort_values("total_value", ascending=True)
    top_imports = imports_agg.head(top_n).sort_values("total_value", ascending=True)

    export_chart = px.bar(
        top_exports,
        x="total_value",
        y="short_label",
        orientation="h",
        title={"en": f"Top {top_n} Export Products", "hy": f"Թոփ {top_n} արտահանվող ապրանքներ"}[lang],
        labels={"total_value": t("exports_value"), "short_label": {"en": "Product", "hy": "Ապրանք"}[lang]},
        color_discrete_sequence=[EXPORT_COLOR],
    )
    export_chart.update_traces(
        customdata=top_exports[["product_code", "full_label"]].values,
        hovertemplate="<b>%{customdata[1]}</b><br>"
        "Code: %{customdata[0]}<br>"
        + f"{t('exports_value')}: %{{x:,.1f}}<extra></extra>",
    )
    export_chart.update_layout(yaxis=dict(automargin=True))

    import_chart = px.bar(
        top_imports,
        x="total_value",
        y="short_label",
        orientation="h",
        title={"en": f"Top {top_n} Import Products", "hy": f"Թոփ {top_n} ներմուծվող ապրանքներ"}[lang],
        labels={"total_value": t("imports_value"), "short_label": {"en": "Product", "hy": "Ապրանք"}[lang]},
        color_discrete_sequence=[IMPORT_COLOR],
    )
    import_chart.update_traces(
        customdata=top_imports[["product_code", "full_label"]].values,
        hovertemplate="<b>%{customdata[1]}</b><br>"
        "Code: %{customdata[0]}<br>"
        + f"{t('imports_value')}: %{{x:,.1f}}<extra></extra>",
    )
    import_chart.update_layout(yaxis=dict(automargin=True))

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(export_chart, use_container_width=True)
    with c2:
        st.plotly_chart(import_chart, use_container_width=True)

with tab2:
    export_tm_data = exports_agg.head(top_n).copy()
    import_tm_data = imports_agg.head(top_n).copy()

    export_tm = px.treemap(
        export_tm_data,
        path=["short_label"],
        values="total_value",
        title={"en": f"Export Composition (Top {top_n})", "hy": f"Արտահանման կառուցվածք (Թոփ {top_n})"}[lang],
        color="total_value",
        color_continuous_scale="Blues",
    )
    export_tm.update_traces(
        customdata=export_tm_data[["product_code", "full_label"]].values,
        hovertemplate="<b>%{customdata[1]}</b><br>Code: %{customdata[0]}<br>"
        + f"{t('exports_value')}: %{{value:,.1f}}<extra></extra>",
    )
    st.plotly_chart(export_tm, use_container_width=True)

    import_tm = px.treemap(
        import_tm_data,
        path=["short_label"],
        values="total_value",
        title={"en": f"Import Composition (Top {top_n})", "hy": f"Ներմուծման կառուցվածք (Թոփ {top_n})"}[lang],
        color="total_value",
        color_continuous_scale="Reds",
    )
    import_tm.update_traces(
        customdata=import_tm_data[["product_code", "full_label"]].values,
        hovertemplate="<b>%{customdata[1]}</b><br>Code: %{customdata[0]}<br>"
        + f"{t('imports_value')}: %{{value:,.1f}}<extra></extra>",
    )
    st.plotly_chart(import_tm, use_container_width=True)

with tab3:
    top_comp = comparison.sort_values("total_activity", ascending=False).head(top_n).copy()
    comp_long = top_comp.melt(
        id_vars=["product_code", "full_label", "short_label"],
        value_vars=["exports_value", "imports_value"],
        var_name="flow",
        value_name="value",
    )
    comp_long["flow"] = comp_long["flow"].replace({"exports_value": t("exports"), "imports_value": t("imports")})

    value_lbl = {"en": "Value", "hy": "Արժեք"}[lang]
    comp_chart = px.bar(
        comp_long,
        x="short_label",
        y="value",
        color="flow",
        barmode="group",
        title={"en": f"Top {top_n} Products by Combined Activity", "hy": f"Թոփ {top_n} ապրանքներ՝ ընդհանուր ակտիվությամբ"}[lang],
        labels={"short_label": {"en": "Product", "hy": "Ապրանք"}[lang], "value": value_lbl, "flow": t("flow")},
        color_discrete_map={t("exports"): EXPORT_COLOR, t("imports"): IMPORT_COLOR},
    )
    comp_chart.update_traces(
        customdata=comp_long[["product_code", "full_label"]].values,
        hovertemplate="<b>%{customdata[1]}</b><br>"
        "Code: %{customdata[0]}<br>"
        + f"{t('flow')}: %{{fullData.name}}<br>"
        + f"{value_lbl}: %{{y:,.1f}}<extra></extra>",
    )

    st.plotly_chart(comp_chart, use_container_width=True)

    with st.expander({"en": "Show comparison table", "hy": "Ցույց տալ համեմատության աղյուսակը"}[lang], expanded=False):
        st.dataframe(
            top_comp[["product_code", "full_label", "exports_value", "imports_value", "net_trade"]]
            .rename(columns={"full_label": {"en": "Product", "hy": "Ապրանք"}[lang]})
            .style.format({"exports_value": "{:,.1f}", "imports_value": "{:,.1f}", "net_trade": "{:,.1f}"}),
            use_container_width=True,
        )

st.markdown("---")
st.subheader(t("key_takeaways"))

ins1, ins2, ins3 = st.columns(3)
top_export = exports_agg.iloc[0] if not exports_agg.empty else None
top_import = imports_agg.iloc[0] if not imports_agg.empty else None

with ins1:
    if top_export is not None:
        st.info(
            f"**{t('exports')}**\n\n{top_export['full_label']} (`{top_export['product_code']}`)\n\n{format_value(top_export['total_value'])}"
        )

with ins2:
    if top_import is not None:
        st.info(
            f"**{t('imports')}**\n\n{top_import['full_label']} (`{top_import['product_code']}`)\n\n{format_value(top_import['total_value'])}"
        )

with ins3:
    net = exports_total - imports_total
    if net >= 0:
        st.success(f"**{t('balance')}**\n\n{format_value(net)}")
    else:
        st.warning(f"**{t('balance')}**\n\n{format_value(net)}")