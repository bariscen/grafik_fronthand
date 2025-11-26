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

st.title("Doypack için Bıçak Çizimi Bilgileri")

dosya_adi_input = st.text_input(
    "Dosya adı (uzantısız)",
    value="bicak_plani"
)

# Temel alanlar
boy_mm = st.number_input("Boy (mm)", min_value=0.0, value=170.0, step=1.0)
gusset_base_name = st.selectbox("Kalıp Bıçağı", ["D404"])
kb = st.number_input("Kalıp Birleşimi", min_value=0.0, value=5.0, step=1.0)
middle_mm = (2*kb)*-1
dikis_kalinlik = st.number_input("Dikiş Kalınlığı", min_value=0.0, value=5.0, step=1.0)

st.markdown("---")
st.subheader("Gelişmiş Ayarlar (opsiyonel)")

with st.expander("Gelişmiş ayarları aç"):
    margin = st.number_input("Margin (mm)", min_value=0.0, value=25.0, step=1.0)
    yuvarlama = st.selectbox("Yuvarlama Var mı", ["False", "True"])
    valf = st.selectbox("Valf Var mı", ["False", "True"])


def to_none_if_zero(v: float):
    # 0 girilmişse backend için None gönder (demek ki “auto hesapla”)
    return None if v == 0 else v


if st.button("Bıçağı Oluştur"):
    payload = {
    "boy_mm": boy_mm,                        # doypack boyu
    "middle_mm": middle_mm,                  # iki gusset arası mesafe
    "margin": margin,                        # üst-alt boşluk (default 25)
    "sag_yapisma": dikis_kalinlik,              # sağ yapışma
    "sol_yapisma": dikis_kalinlik,              # sol yapışma
    "yuvarlama": yuvarlama,                  # rounded corner yes/no
    "valf": valf,                            # valf var mı
    "gusset_base_name": gusset_base_name,    # storage içindeki base isim: "D404"
    "dosya_adi": dosya_adi_input             # çıktı dosya adı (opsiyonel)
}


    try:
        res = requests.post(f"{BACKEND_URL}/gusset-die-line", json=payload)

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
