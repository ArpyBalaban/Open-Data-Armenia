import streamlit as st

from utils.i18n import LANG_EN, LANG_HY, get_lang, set_lang, t

st.set_page_config(page_title=t("app_title"), layout="wide")

# Sidebar global controls
with st.sidebar:
    st.markdown(f"### {t('app_title')}")
    # Display labels
    lang_display = st.radio(
        t("language"),
        options=[t("english"), t("armenian")],
        index=0 if get_lang() == LANG_EN else 1,
    )
    set_lang(LANG_EN if lang_display == t("english") else LANG_HY)

st.title(t("app_title"))
st.write(t("use_sidebar"))