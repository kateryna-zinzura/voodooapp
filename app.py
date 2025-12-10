# app.py
import streamlit as st
from tabs import utm_bitly, bitly_stats

st.set_page_config(
    page_title="Multi-Tool App",
    page_icon="🛠️",
    layout="wide",
)

# ---------------- Header ----------------
st.title("🛠️ Multi-Tool Application")
st.write("")  # small spacing

# ---------------- Sidebar Navigation ----------------
st.sidebar.title("🔧 Tools")

PAGES = {
    "UTM + Bitly Shortener": {
        "icon": "✂️",
        "render": utm_bitly.render,
    },
    "Bitly Stats": {
        "icon": "📊",
        "render": bitly_stats.render,
    },
}

page_names = list(PAGES.keys())

selected_page = st.sidebar.radio(
    "Select tool:",
    page_names,
    format_func=lambda name: f"{PAGES[name]['icon']}  {name}",
)

st.sidebar.markdown("---")
st.sidebar.caption("Multi-Tool dashboard for Voodoo 🧙‍♀️")

# ---------------- Main Content ----------------
PAGES[selected_page]["render"]()
