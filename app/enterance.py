import streamlit as st
import numpy as np
import pandas as pd
from pathlib import Path

st.set_page_config(initial_sidebar_state="collapsed")

# --- HEADER / SIDEBAR / MENÜ GİZLEME ---
st.markdown(
    """
<style>
    [data-testid="collapsedControl"] {
        display: none;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("""
    <style>
    /* Menü (sidebar navigation) gizle */
    section[data-testid="stSidebarNav"] {
        display: none;
    }
    /* Sağ üstteki hamburger menü gizle */
    button[title="Toggle sidebar"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Bu dosyanın bulunduğu dizin
current_dir = Path(__file__).parent

# row-data yolunu oluştur
image_path = current_dir.parent / "row-data" / "sesa-logo-80-new.png"
st.image(str(image_path), width=300)

# Arka plan rengi
st.markdown("""
    <style>
    .stApp {
        background-color: #d3d3d3; /* 1 ton açık gri */
    }
    </style>
    """, unsafe_allow_html=True)

# Başlık
st.markdown(
    """
    <h2 style="color: #FFBF00;">
        <span style="background-color:#666666; padding: 5px 10px; border-radius: 5px;">
            SESA Ambalaj Yapay Zekaya Hoşgeldin
        </span>
    </h2>
    """,
    unsafe_allow_html=True
)

st.markdown("<div style='margin-bottom: 50px;'></div>", unsafe_allow_html=True)

# --- Özel Buton Stilleri ---
st.markdown("""
<style>
div.stButton > button:first-child {
    background-color:#FFBF00;
    color: #555555;
    border-radius: 8px;
    border: 1px solid #555555;
    padding: 10px 20px;
    font-size: 16px;
    transition: background-color 0.3s, color 0.3s;
}

div.stButton > button:first-child:hover {
    background-color: #777777;
    color: white;
    border-color: #AAAAAA;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.custom-info-box {
    background-color: #444444;
    color: #FFBF00;
    border-left: 5px solid #FFBF00;
    padding: 10px 15px;
    border-radius: 5px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# Butonları büyüt
st.markdown("""
<style>
div.stButton > button {
    font-size: 24px !important;
    padding: 20px 40px !important;
    height: auto !important;
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# =======================
#   ŞİFRE & SAYFA AYARI
# =======================

# Tek sayfa: mainpage
TARGET_PAGE = "pages/mainpage.py"

# Eğer secrets.toml'da hala "page1" kullanıyorsan:
PAGE_PASSWORD = st.secrets.page1

# Eğer değiştirmek istersen:
# PAGE_PASSWORD = st.secrets.mainpage

# --- Session state init ---
if 'show_password_input' not in st.session_state:
    st.session_state.show_password_input = False
if 'password_error' not in st.session_state:
    st.session_state.password_error = False


def check_password_and_navigate():
    entered_password = st.session_state.password_input

    if entered_password == PAGE_PASSWORD:
        st.session_state.show_password_input = False
        st.session_state.password_error = False
        st.switch_page(TARGET_PAGE)  # "pages/mainpage.py"
    else:
        st.session_state.password_error = True


# --- Navigasyon Butonu (TEK SAYFA: SATIŞ / MAINPAGE) ---
col1 = st.columns(1)[0]
with col1:
    if st.button('GRAFİK'):
        st.session_state.show_password_input = True
        st.session_state.password_error = False

st.markdown("<div style='margin-bottom: 70px;'></div>", unsafe_allow_html=True)

# --- Şifre Giriş Formu ---
if st.session_state.show_password_input:
    page_display_name = "GRAFİK"

    st.markdown(f"""
    <div class="custom-info-box">
        <b>'{page_display_name}'</b> sayfasına erişmek için şifrenizi girin.
    </div>
    """, unsafe_allow_html=True)

    with st.form(key="password_form"):
        password_input = st.text_input("Şifre", type="password", key="password_input")
        col_buttons_1, col_buttons_2 = st.columns(2)

        with col_buttons_1:
            submit_button = st.form_submit_button("Onayla")

        with col_buttons_2:
            cancel_button = st.form_submit_button("İptal")

        if submit_button:
            check_password_and_navigate()
        elif cancel_button:
            st.session_state.show_password_input = False
            st.session_state.password_error = False

    if st.session_state.password_error:
        st.error("Yanlış şifre! Lütfen tekrar deneyin.")
