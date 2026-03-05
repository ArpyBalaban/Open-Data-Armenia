from pathlib import Path

import streamlit as st

from utils.i18n import LANG_EN, LANG_HY, get_lang, set_lang, t

BASE_DIR = Path(__file__).resolve().parent
HERO_PATH = BASE_DIR / "assets" / "hero.png"

st.set_page_config(page_title=t("app_title"), layout="wide")

# ---- Sidebar: global language switch
with st.sidebar:
    st.markdown(f"### {t('app_title')}")
    lang_display = st.radio(
        t("language"),
        options=[t("english"), t("armenian")],
        index=0 if get_lang() == LANG_EN else 1,
    )
    set_lang(LANG_EN if lang_display == t("english") else LANG_HY)

lang = get_lang()

# ---- Homepage content
st.title(t("app_title"))

one_liner = {
    "en": "Interactive dashboards for exploring Armenia’s trade trends, products, and partner countries.",
    "hy": "Ինտերակտիվ վահանակներ՝ Հայաստանի առևտրի միտումները, ապրանքները և գործընկեր երկրները ուսումնասիրելու համար։",
}[lang]
st.write(one_liner)

# Hero image
if HERO_PATH.exists():
    st.image(str(HERO_PATH), use_container_width=True)
else:
    st.info(
        {
            "en": "Hero image not found. Add it at assets/hero.png",
            "hy": "Գլխավոր պատկերն անհայտ է։ Ավելացրեք այն assets/hero.png հասցեով։",
        }[lang]
    )

# Data coverage + source note (small text)
coverage = {
    "en": (
        "**Data coverage:** Armenia External Trade Database (2002–2022 archive; availability varies by table).  \n"
        "**Source:** Open Data Armenia Contest dataset package."
    ),
    "hy": (
        "**Տվյալների ծածկույթ:** Հայաստանի արտաքին առևտրի տվյալների շտեմարան (2002–2022 արխիվ; "
        "աղյուսակներից կախված՝ ծածկույթը կարող է տարբեր լինել)։  \n"
        "**Աղբյուր:** Open Data Armenia Contest տվյալների փաթեթ։"
    ),
}[lang]

tools = {
    "en": "**Built with:** Python · pandas · Plotly · Streamlit · GitHub",
    "hy": "**Կառուցված է:** Python · pandas · Plotly · Streamlit · GitHub",
}[lang]

st.caption(coverage)
st.caption(tools)

# Gentle navigation hint
st.markdown(
    {
        "en": "Use the sidebar to open **Trade Overview**, **Products**, or **Partner Countries**.",
        "hy": "Օգտագործեք կողային վահանակը՝ բացելու **Առևտրի Ընդհանուր Պատկեր**, **Ապրանքներ**, կամ **Գործընկեր Երկրներ** էջերը։",
    }[lang]
)

# Discreet author line
st.markdown("---")
st.caption(
    {
        "en": "Created by Arpy Balaban.",
        "hy": "Ստեղծել է՝ Arpy Balaban։",
    }[lang]
)