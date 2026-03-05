from __future__ import annotations

import streamlit as st


LANG_EN = "en"
LANG_HY = "hy"


_UI = {
    "app_title": {"en": "Armenia Trade Atlas", "hy": "Հայաստանի Առևտրի Ատլաս"},
    "language": {"en": "Language", "hy": "Լեզու"},
    "english": {"en": "English", "hy": "English"},
    "armenian": {"en": "Armenian", "hy": "Հայերեն"},
    "use_sidebar": {
        "en": "Use the sidebar to navigate between pages.",
        "hy": "Օգտագործեք կողային վահանակը՝ էջերի միջև անցնելու համար։",
    },
    "trade_overview_title": {"en": "Trade Overview", "hy": "Առևտրի Ընդհանուր Պատկեր"},
    "products_title": {"en": "Products", "hy": "Ապրանքներ"},
    "partners_title": {"en": "Partner Countries", "hy": "Գործընկեր Երկրներ"},
    "selected_period": {"en": "Selected Period", "hy": "Ընտրված Ժամանակահատված"},
    "top_n": {"en": "Top N", "hy": "Թոփ N"},
    "comparison_period": {"en": "Comparison period", "hy": "Համեմատության Ժամանակահատված"},
    "select_year": {"en": "Select year for KPI snapshot", "hy": "Ընտրեք տարին՝ KPI ցուցանիշների համար"},
    "year": {"en": "Year", "hy": "Տարի"},
    "exports": {"en": "Exports", "hy": "Արտահանում"},
    "imports": {"en": "Imports", "hy": "Ներմուծում"},
    "balance": {"en": "Balance", "hy": "Հաշվեկշիռ"},
    "turnover": {"en": "Turnover", "hy": "Շրջանառություն"},
    "flow": {"en": "Flow", "hy": "Հոսք"},
    "exports_value": {"en": "Export Value", "hy": "Արտահանման Արժեք"},
    "imports_value": {"en": "Import Value", "hy": "Ներմուծման Արժեք"},
    "total_exports_value": {"en": "Total Exports (value_to)", "hy": "Ընդհանուր Արտահանում (value_to)"},
    "total_imports_value": {"en": "Total Imports (value_to)", "hy": "Ընդհանուր Ներմուծում (value_to)"},
    "distinct_countries": {"en": "Distinct Countries", "hy": "Երկրների Քանակ"},
    "distinct_products": {"en": "Distinct Products", "hy": "Ապրանքների Քանակ"},
    "map": {"en": "Map", "hy": "Քարտեզ"},
    "top_countries": {"en": "Top Countries", "hy": "Թոփ Երկրներ"},
    "country_detail": {"en": "Country Detail", "hy": "Երկրի Մանրամասներ"},
    "select_country": {"en": "Select a country", "hy": "Ընտրեք երկիրը"},
    "total_trade": {"en": "Total Trade", "hy": "Ընդհանուր Առևտուր"},
    "key_takeaways": {"en": "Key Takeaways", "hy": "Հիմնական Եզրակացություններ"},
}


def get_lang() -> str:
    lang = st.session_state.get("lang", LANG_EN)
    return lang if lang in (LANG_EN, LANG_HY) else LANG_EN


def set_lang(lang: str) -> None:
    st.session_state["lang"] = lang if lang in (LANG_EN, LANG_HY) else LANG_EN


def t(key: str) -> str:
    lang = get_lang()
    if key not in _UI:
        return key
    return _UI[key].get(lang, _UI[key].get(LANG_EN, key))