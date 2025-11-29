import streamlit as st
import numpy as np
import pandas as pd
import os
from pathlib import Path
import sys
import requests


### SIDE BAR KAPAMA BASLIYOR

st.set_page_config(initial_sidebar_state="collapsed")

st.markdown(
    """
<style>
    [data-testid="collapsedControl"] {
        display: none
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


### SIDE BAR KAPAMA BİTTİ

# Projenin kök dizinini (sesa_front) Python'ın arama yoluna ekle.
# gelecek.py dosyası 'app/pages' klasörünün içinde olduğu için,
# Path(__file__).resolve().parent -> app/pages
# .parent.parent -> app
# .parent.parent.parent -> sesa_front (projenin kökü)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Şimdi 'function.py' dosyasını doğrudan projenin kökünden import edebiliriz.



# Bu dosyanın bulunduğu dizin (app.py'nin dizini)
current_dir = Path(__file__).parent.parent

# row-data yolunu oluştur
image_path_for_logo = current_dir.parent / "row-data" / "sesa-logo-80-new.png"


# Logonun her sayfada gösterilmesi için session_state'e kaydet
if 'logo_image_path' not in st.session_state:
    st.session_state.logo_image_path = str(image_path_for_logo)

# Ana sayfada logoyu göster (isteğe bağlı, sayfalarda da gösterebilirsin)
st.image(st.session_state.logo_image_path, width=200)

st.markdown("""
    <style>
    .stApp {
        background-color: #d3d3d3; /* 1 ton açık gri */
    }
    </style>
    """, unsafe_allow_html=True)


st.markdown("""
    <style>
    div[data-testid="pazarlama_button"] button {
        position: fixed !important;
        top: 10px !important;
        right: 10px !important;
        background-color: #444444 !important;
        color: #FFBF00 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 12px 24px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        cursor: pointer !important;
        z-index: 9999 !important;
        transition: background-color 0.3s ease !important;
    }
    div[data-testid="pazarlama_button"] button:hover {
        background-color: #555555 !important;
        color: #FFBF00 !important;
    }
    </style>
""", unsafe_allow_html=True)

# SADECE bu button'a özel container (testid kullanılıyor)
with st.container():
    st.markdown('<div data-testid="satis_button">', unsafe_allow_html=True)
    if st.button("Bıçak Çizimi Menüsüne Dön", key="satis"):
        st.switch_page("pages/die-line.py")
    st.markdown("</div>", unsafe_allow_html=True)

import streamlit as st
import requests

BACKEND_URL = "https://sesa-grafik-api-1003931228830.europe-southwest1.run.app"  # backend burada çalışıyor varsayalım

st.title("Bobin için Bıçak Çizimi Bilgileri")

dosya_adi_input = st.text_input(
    "Dosya adı (uzantısız)",
    value="bicak_plani"
)

# Temel alanlar
toplam_en = st.number_input("Toplam En (mm)", min_value=0.0, value=350.0, step=1.0)
toplam_boy = st.number_input("Toplam Boy (mm)", min_value=0.0, value=210.0, step=1.0)
yapistirma = st.selectbox("Yapıştırma tipi", ["AA", "AB"])

st.markdown("---")
st.subheader("Gelişmiş Ayarlar (opsiyonel)")

with st.expander("Gelişmiş ayarları aç"):
    bleed = st.number_input("Bleed (mm)", min_value=0.0, value=3.0, step=0.5)
    margin = st.number_input("Margin (mm)", min_value=0.0, value=27.0, step=1.0)

    sol_yapisma = st.number_input("Sol Yapışma (mm)", min_value=0.0, value=0.0, step=0.5)
    sag_yapisma = st.number_input("Sağ Yapışma (mm)", min_value=0.0, value=0.0, step=0.5)

    sol_panel = st.number_input("Sol Panel (mm)", min_value=0.0, value=0.0, step=0.5)
    orta_panel = st.number_input("Orta Panel (mm)", min_value=0.0, value=0.0, step=0.5)
    sag_panel = st.number_input("Sağ Panel (mm)", min_value=0.0, value=0.0, step=0.5)

    ust_yapisma = st.number_input("Üst Yapışma (mm)", min_value=0.0, value=0.0, step=0.5)
    alt_yapisma = st.number_input("Alt Yapışma (mm)", min_value=0.0, value=0.0, step=0.5)
    fotosel_h_mm = st.number_input("Fotosel Yükseklik (mm)", min_value=0.0, value=7.0, step=0.5)
    fotosel_h_mm = st.number_input("Fotosel Genişlik (mm)", min_value=0.0, value=15.0, step=0.5)

def to_none_if_zero(v: float):
    # 0 girilmişse backend için None gönder (demek ki “auto hesapla”)
    return None if v == 0 else v


if st.button("Bıçağı Oluştur"):
    payload = {
        "toplam_en_mm": toplam_en,
        "toplam_boy_mm": toplam_boy,
        "yapistima": yapistirma,
        "bleed_mm": bleed,
        "margin_mm": margin,
        "sol_yapisma_mm": to_none_if_zero(sol_yapisma),
        "sag_yapisma_mm": to_none_if_zero(sag_yapisma),
        "sol_panel_mm": to_none_if_zero(sol_panel),
        "orta_panel_mm": to_none_if_zero(orta_panel),
        "sag_panel_mm": to_none_if_zero(sag_panel),
        "ust_yapisma_mm": to_none_if_zero(ust_yapisma),
        "alt_yapisma_mm": to_none_if_zero(alt_yapisma),
        "dosya_adi": dosya_adi_input,
        "fotosel_h_mm": to_none_if_zero(fotosel_h_mm),
        "fotosel_w_mm": to_none_if_zero(fotosel_w_mm)
    }

    try:
        res = requests.post(f"{BACKEND_URL}/roll-die-line", json=payload)

        if res.status_code == 200:
            pdf_bytes = res.content

            # Header'dan gerçek dosya adını çekelim
            content_disposition = res.headers.get("content-disposition", "")
            filename = f"{dosya_adi_input}.pdf"

            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[1].strip('"')

            st.success("PDF başarıyla oluşturuldu ✅")

            st.download_button(
                label=f"📥 {filename} dosyasını indir",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
            )

        else:
            st.error(f"Sunucudan hata dönüyor: {res.status_code}")
            st.text(res.text)

    except Exception as e:
        st.error("PDF oluştururken bir hata oluştu.")
        st.exception(e)
