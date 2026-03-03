import streamlit as st

st.set_page_config(page_title="Armenia Trade Atlas", layout="wide")

st.title("Armenia Trade Atlas")
st.write(
    "An interactive dashboard for exploring Armenia’s trade data, "
    "including long-term trends, products, partner countries, and essential goods."
)

st.markdown(
    """
    Use the sidebar to navigate between pages:

    - **Trade Overview**
    - **Products**
    - **Partner Countries**
    - **Essential Goods**
    """
)