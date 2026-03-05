from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.i18n import get_lang, t


BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = BASE_DIR / "data" / "clean"

EXPORTS_PATH = CLEAN_DIR / "exports_country_products.csv"
IMPORTS_PATH = CLEAN_DIR / "imports_country_products.csv"
COUNTRY_TR_PATH = CLEAN_DIR / "country_translations.csv"
PRODUCT_TR_PATH = CLEAN_DIR / "product_translations.csv"

EXPORT_COLOR = "#1f77b4"
IMPORT_COLOR = "#d62728"

LEFT_MARGIN = 260  # for y-axis labels


def format_value(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.1f}"


def shorten_label(text: str, max_len: int = 55) -> str:
    if pd.isna(text):
        return "Unknown"
    s = str(text).strip()
    return s if len(s) <= max_len else s[: max_len - 1].rstrip() + "…"


def normalize_period_label(raw: str) -> str:
    return str(raw).strip().replace("-", "–")


def period_display_label(raw: str, lang: str) -> str:
    raw = str(raw).strip()
    if "կիսամյակ" in raw:
        base = normalize_period_label(raw.split()[-1])
        suffix = "I կիսամյակ" if lang == "hy" else "H1"
    else:
        base = normalize_period_label(raw)
        suffix = "Ամբողջ տարի" if lang == "hy" else "Full year"
    return f"{base} ({suffix})"


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    exports_df = pd.read_csv(EXPORTS_PATH, dtype={"product_code": str})
    imports_df = pd.read_csv(IMPORTS_PATH, dtype={"product_code": str})
    country_tr = pd.read_csv(COUNTRY_TR_PATH)

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
        df["country_name"] = df["country_name"].astype("string").str.strip()
        df["product_code"] = df["product_code"].astype(str).str.strip().str.zfill(4)
        df["product_name"] = df["product_name"].astype("string").str.strip()
        for col in ["year_from", "year_to", "quantity_from", "value_from", "quantity_to", "value_to"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalize country translations
    country_tr["country_name_am"] = country_tr["country_name_am"].astype("string").str.strip()
    country_tr["country_name_en"] = country_tr["country_name_en"].astype("string").str.strip()
    country_tr["iso3"] = country_tr["iso3"].fillna("").astype("string").str.strip()

    # Normalize product translations
    prod_tr["product_code"] = prod_tr["product_code"].astype(str).str.strip().str.zfill(4)
    prod_tr["product_name_am"] = prod_tr["product_name_am"].astype("string").str.strip()
    prod_tr["product_name_en"] = prod_tr["product_name_en"].astype("string").str.strip()

    return exports_df, imports_df, country_tr, prod_tr


def aggregate_countries_value(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("country_name", dropna=False)["value_to"]
        .sum(min_count=1)
        .reset_index(name="total_value")
        .sort_values("total_value", ascending=False)
        .reset_index(drop=True)
    )


def attach_country_labels(country_totals_am: pd.DataFrame, country_tr: pd.DataFrame) -> pd.DataFrame:
    out = country_totals_am.merge(
        country_tr[["country_name_am", "country_name_en", "iso3"]],
        left_on="country_name",
        right_on="country_name_am",
        how="left",
    )
    out["country_name_en"] = out["country_name_en"].fillna(out["country_name"])
    out["iso3"] = out["iso3"].fillna("").astype("string").str.strip()
    return out


def aggregate_country_products_value(
    df: pd.DataFrame,
    country_am: str,
    prod_tr: pd.DataFrame,
    lang: str,
) -> pd.DataFrame:
    filtered = df[df["country_name"] == country_am].copy()

    grouped = (
        filtered.groupby("product_code", dropna=False)
        .agg(total_value=("value_to", "sum"))
        .reset_index()
        .sort_values("total_value", ascending=False)
        .reset_index(drop=True)
    )
    grouped["product_code"] = grouped["product_code"].astype(str).str.strip().str.zfill(4)

    grouped = grouped.merge(
        prod_tr[["product_code", "product_name_am", "product_name_en"]],
        on="product_code",
        how="left",
    )

    name_col = "product_name_en" if lang == "en" else "product_name_am"
    grouped["display_label"] = grouped[name_col].fillna(grouped["product_code"])
    grouped["display_label_short"] = grouped["display_label"].apply(shorten_label)
    return grouped


st.set_page_config(page_title=t("partners_title"), layout="wide")

lang = get_lang()
exports_df, imports_df, country_tr, prod_tr = load_data()

st.title(t("partners_title"))
st.caption(
    {
        "en": "Explore partner countries. Totals use trade value (value_to).",
        "hy": "Ուսումնասիրեք գործընկեր երկրները։ Ընդհանուրները հաշվարկված են արժեքով (value_to)։",
    }[lang]
)

# --- Period dropdown with display labels (Style A)
all_periods_raw = sorted(
    set(exports_df["period_label"].dropna().unique()) | set(imports_df["period_label"].dropna().unique())
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

exports_c_am = aggregate_countries_value(exports_f)
imports_c_am = aggregate_countries_value(imports_f)

exports_c = attach_country_labels(exports_c_am, country_tr)
imports_c = attach_country_labels(imports_c_am, country_tr)

country_label_col = "country_name_en" if lang == "en" else "country_name_am"

# KPI strip
exports_total = exports_f["value_to"].sum()
imports_total = imports_f["value_to"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric(t("selected_period"), selected_period_key)
k2.metric(t("total_exports_value"), format_value(exports_total))
k3.metric(t("total_imports_value"), format_value(imports_total))
k4.metric(t("distinct_countries"), f"{exports_f['country_name'].nunique():,} / {imports_f['country_name'].nunique():,}")

tab1, tab2, tab3 = st.tabs([t("top_countries"), t("country_detail"), t("map")])

# --- Tab 1: Top Countries
with tab1:
    top_exp = exports_c.head(top_n).sort_values("total_value", ascending=True)
    top_imp = imports_c.head(top_n).sort_values("total_value", ascending=True)

    exp_chart = px.bar(
        top_exp,
        x="total_value",
        y=country_label_col,
        orientation="h",
        title={"en": f"Top {top_n} Export Destinations", "hy": f"Թոփ {top_n} արտահանման ուղղություններ"}[lang],
        labels={"total_value": t("exports_value"), country_label_col: {"en": "Country", "hy": "Երկիր"}[lang]},
        color_discrete_sequence=[EXPORT_COLOR],
    )
    exp_chart.update_layout(yaxis=dict(automargin=True), margin=dict(l=LEFT_MARGIN, r=20, t=60, b=20))

    imp_chart = px.bar(
        top_imp,
        x="total_value",
        y=country_label_col,
        orientation="h",
        title={"en": f"Top {top_n} Import Sources", "hy": f"Թոփ {top_n} ներմուծման աղբյուրներ"}[lang],
        labels={"total_value": t("imports_value"), country_label_col: {"en": "Country", "hy": "Երկիր"}[lang]},
        color_discrete_sequence=[IMPORT_COLOR],
    )
    imp_chart.update_layout(yaxis=dict(automargin=True), margin=dict(l=LEFT_MARGIN, r=20, t=60, b=20))

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(exp_chart, use_container_width=True)
    with c2:
        st.plotly_chart(imp_chart, use_container_width=True)

# --- Tab 2: Country Detail
with tab2:
    st.markdown({"en": "Select a country to explore products.", "hy": "Ընտրեք երկիր՝ ապրանքները դիտելու համար։"}[lang])

    all_countries_am = sorted(
        set(exports_f["country_name"].dropna().unique()) | set(imports_f["country_name"].dropna().unique())
    )
    dropdown_df = country_tr[country_tr["country_name_am"].isin(all_countries_am)].copy()

    missing = [c for c in all_countries_am if c not in set(dropdown_df["country_name_am"])]
    if missing:
        dropdown_df = pd.concat(
            [dropdown_df, pd.DataFrame({"country_name_am": missing, "country_name_en": missing, "iso3": ["" for _ in missing]})],
            ignore_index=True,
        )

    dropdown_df = dropdown_df.sort_values(country_label_col)
    options = dropdown_df[country_label_col].tolist()
    label_to_am = dict(zip(dropdown_df[country_label_col], dropdown_df["country_name_am"]))

    # Default to Russian Federation (or Armenian equivalent)
    if lang == "en":
        default_label = "Russian Federation"
    else:
        rf_rows = dropdown_df[dropdown_df["country_name_en"] == "Russian Federation"]
        default_label = rf_rows["country_name_am"].iloc[0] if not rf_rows.empty else (options[0] if options else "")

    default_index = options.index(default_label) if default_label in options else 0

    selected_country_label = st.selectbox(t("select_country"), options=options, index=default_index if options else 0)
    selected_country_am = label_to_am.get(selected_country_label)

    if selected_country_am:
        exp_val = exports_f.loc[exports_f["country_name"] == selected_country_am, "value_to"].sum()
        imp_val = imports_f.loc[imports_f["country_name"] == selected_country_am, "value_to"].sum()
        total_trade = exp_val + imp_val

        a, b, c = st.columns(3)
        a.metric(t("exports"), format_value(exp_val))
        b.metric(t("imports"), format_value(imp_val))
        c.metric(t("total_trade"), format_value(total_trade))

        exp_prod = aggregate_country_products_value(exports_f, selected_country_am, prod_tr, lang).head(top_n)
        imp_prod = aggregate_country_products_value(imports_f, selected_country_am, prod_tr, lang).head(top_n)

        cc1, cc2 = st.columns(2)

        exp_prod_chart = px.bar(
            exp_prod.sort_values("total_value", ascending=True),
            x="total_value",
            y="display_label_short",
            orientation="h",
            title={"en": f"Top {top_n} Export Products", "hy": f"Թոփ {top_n} արտահանվող ապրանքներ"}[lang],
            labels={"total_value": t("exports_value"), "display_label_short": {"en": "Product", "hy": "Ապրանք"}[lang]},
            color_discrete_sequence=[EXPORT_COLOR],
        )
        exp_prod_chart.update_layout(yaxis=dict(automargin=True), margin=dict(l=LEFT_MARGIN, r=20, t=60, b=20))
        exp_prod_chart.update_traces(
            customdata=exp_prod[["product_code", "display_label"]].values,
            hovertemplate="<b>%{customdata[1]}</b><br>"
            "Code: %{customdata[0]}<br>"
            + f"{t('exports_value')}: %{{x:,.1f}}<extra></extra>",
        )

        imp_prod_chart = px.bar(
            imp_prod.sort_values("total_value", ascending=True),
            x="total_value",
            y="display_label_short",
            orientation="h",
            title={"en": f"Top {top_n} Import Products", "hy": f"Թոփ {top_n} ներմուծվող ապրանքներ"}[lang],
            labels={"total_value": t("imports_value"), "display_label_short": {"en": "Product", "hy": "Ապրանք"}[lang]},
            color_discrete_sequence=[IMPORT_COLOR],
        )
        imp_prod_chart.update_layout(yaxis=dict(automargin=True), margin=dict(l=LEFT_MARGIN, r=20, t=60, b=20))
        imp_prod_chart.update_traces(
            customdata=imp_prod[["product_code", "display_label"]].values,
            hovertemplate="<b>%{customdata[1]}</b><br>"
            "Code: %{customdata[0]}<br>"
            + f"{t('imports_value')}: %{{x:,.1f}}<extra></extra>",
        )

        with cc1:
            st.plotly_chart(exp_prod_chart, use_container_width=True)
        with cc2:
            st.plotly_chart(imp_prod_chart, use_container_width=True)

# --- Tab 3: Map
with tab3:
    flow = st.radio(t("flow"), options=[t("exports"), t("imports")], horizontal=True)

    if flow == t("exports"):
        map_df = exports_c.copy()
        value_label = t("exports_value")
        color_scale = "Blues"
    else:
        map_df = imports_c.copy()
        value_label = t("imports_value")
        color_scale = "Reds"

    mappable = map_df[map_df["iso3"].fillna("").astype(str).str.strip() != ""].copy()

    if mappable.empty:
        st.warning({"en": "No mappable countries found.", "hy": "Քարտեզի համար տվյալներ չեն գտնվել։"}[lang])
    else:
        choropleth = px.choropleth(
            mappable,
            locations="iso3",
            color="total_value",
            hover_name=country_label_col,
            color_continuous_scale=color_scale,
            labels={"total_value": value_label},
        )
        choropleth.update_traces(
            hovertemplate="<b>%{hovertext}</b><br>" + f"{value_label}: %{{z:,.1f}}<extra></extra>"
        )
        choropleth.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(choropleth, use_container_width=True)