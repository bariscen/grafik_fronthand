import streamlit as st
import numpy as np
import pandas as pd
import os
from pathlib import Path
import sys
import requests

# ------------------------------------------------
#  GENEL AYARLAR & SIDEBAR / MENÜ GİZLEME
# ------------------------------------------------
st.set_page_config(initial_sidebar_state="collapsed")

# Sol sidebar collapse okunu gizle
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

# Sol menü (sayfa navigation) ve hamburger menü gizle
st.markdown("""
    <style>
    section[data-testid="stSidebarNav"] {
        display: none;
    }
    button[title="Toggle sidebar"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Üst menü, header, footer gizle
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Arka plan rengi
st.markdown("""
    <style>
    .stApp {
        background-color: #d3d3d3;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------
#  LOGO
# ------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

current_dir = Path(__file__).parent.parent
image_path_for_logo = current_dir.parent / "row-data" / "sesa-logo-80-new.png"

if 'logo_image_path' not in st.session_state:
    st.session_state.logo_image_path = str(image_path_for_logo)

st.image(st.session_state.logo_image_path, width=200)

# ------------------------------------------------
#  ÜSTTE "Bıçak Çizimi Menüsüne Dön" BUTONU
# ------------------------------------------------
st.markdown("""
    <style>
    div[data-testid="satis_button"] button {
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
    div[data-testid="satis_button"] button:hover {
        background-color: #555555 !important;
        color: #FFBF00 !important;
    }
    </style>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<div data-testid="satis_button">', unsafe_allow_html=True)
    if st.button("Bıçak Çizimi Menüsüne Dön", key="satis"):
        st.switch_page("pages/die-line.py")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------
#  DOYPACK FORMU
# ------------------------------------------------
BACKEND_URL = "https://sesa-grafik-api-1003931228830.europe-southwest1.run.app"

st.title("Doypack için Bıçak Çizimi Bilgileri")

dosya_adi_input = st.text_input(
    "Dosya adı (uzantısız)",
    value="bicak_plani"
)

# Temel alanlar
boy_mm = st.number_input("Boy (mm)", min_value=0.0, value=170.0, step=1.0)

gusset_options = {
    "D404 164 x 50": "D404",
    "D403 116 x 40": "D403",
    "D407 180 x 45": "D407",
    "D405 210 x 55" : "D405",
    "D413 260 x 50" : "D413",
    "Deneme": "Deneme"
    }
gusset_label = st.selectbox(
    "Kalıp Bıçağı",
    list(gusset_options.keys())
    )
gusset_base_name = gusset_options[gusset_label]

kb = gusset_label.split()
birlesim = float(kb[-1])
en_mm =  float(kb[-3])

# kb = st.number_input("Kalıp Birleşimi", min_value=0.0, value=5.0, step=1.0)
# middle_mm = (2 * kb) * -1
dikis_kalinlik = st.number_input("Dikiş Kalınlığı (mm)", min_value=0.0, value=5.0, step=1.0)

st.markdown("---")
st.subheader("Gelişmiş Ayarlar (opsiyonel)")

with st.expander("Gelişmiş ayarları aç"):

    margin = st.number_input("Margin (mm)", min_value=0.0, value=25.0, step=1.0)
    yuvarlama = st.selectbox("Radious Var mı", ["Yok", "Var"])

    # -----------------------------------------
    # ⭐ VALF AYARLARI
    # -----------------------------------------

    valf = st.selectbox("Valf Var mı", ["Yok", "Var"])

    valf_mesafe = 0
    valf_panel = "sag"
    if valf == "Var":
        valf_mesafe = st.number_input(
            "Valf Yeri (mm)",
            min_value=0.0,
            value=55.0,
            step=1.0,
        )
        valf_p = st.selectbox("Valf Önde mi Arkada mı", ["Ön Taraf", "Arka Taraf"])

        if valf_p == "Ön Taraf":
            valf_panel = "sol"
        else:
            valf_panel = "sag"



    # -----------------------------------------
    # ⭐ AÇ-KAPA AYARLARI
    # -----------------------------------------
    ac_kapa = st.selectbox("Çentik Var mı", ["Yok", "Var"])

    ac_kapa_yer = 0.0
    if ac_kapa == "Var":
        ac_kapa_yer = st.number_input(
            "Çentik Yeri (mm)",
            min_value=0.0,
            value=20.0,
            step=1.0,
        )

    # -----------------------------------------
    # ⭐ ZIPPER AYARLARI
    # -----------------------------------------
    zipper = st.selectbox("Zipper Var mı", ["Yok", "Var"])

    zipper_name = None
    zip_mesafe = 0.0
    sag_zip = "Yok"

    if zipper == "Var":

        zipper_options = ["PE (6 mm) ZIP", "PE (10 mm) ZIP", "PP (11 mm) ZIP", "Standart ZIP", "VELCRO (16 mm) ZIP", "Flexico (Senso Grip) ZIP", "VELCRO (22 mm) ZIP", "Aplix (16 mm) ZIP", "Front ZIP", "Child Resistant ZIP"]

        zipper_name = st.selectbox(
            "Zipper Tipi Seç (PDF adı, uzantısız)",
            zipper_options,
            index=0,
        )

        zip_mesafe = st.number_input(
            "Zipper Mesafesi (mm)",
            min_value=0.0,
            value=30.0,
            step=1.0,
        )

        sag_zip = "Var"


    # -----------------------------------------
    # ⭐ EUROHOLE AYARLARI
    # -----------------------------------------
    eurohole = st.selectbox("Eurohole Var mı", ["Yok", "Var"])

    eurohole_name = None
    eurohole_mesafe = 0.0

    if eurohole == "Var":
        eurohole_options = [
            "Eurohole 1_21cm",
            "Eurohole 2_33cm",
            "Eurohole 3_cift_21cm",
            "Eurohole 4_cift_31cm",
            "Eurohole 5_45cm",
            "Eurohole 6_27cm",
            "Eurohole 7_30cm",
            "Eurohole 8_yuv_22cm",
            "Eurohole Bıyık_38cm",
            "Delik Tip 1_cap5",
            "Delik Tip 2_cap8",
            "Delik Tip 3_cap6",
            "Delik Tipi 4_cap10cm"
        ]

        eurohole_name = st.selectbox(
            "Eurohole Seç (PDF adı, uzantısız)",
            eurohole_options,
            index=0,
        )

        eurohole_mesafe = st.number_input(
            "Eurohole Mesafesi (mm)",
            min_value=0.0,
            value=10.0,
            step=1.0,
        )

# ------------------------------------------------
#  BUTON & BACKEND CALL
# ------------------------------------------------
if st.button("Bıçağı Oluştur"):

    # Zorunluluk kontrolleri
    if zipper == "Var" and (not zipper_name or zipper_name.strip() == ""):
        st.error("❌ Zipper aktif fakat 'Zipper Dosya Adı' girilmemiş!")
        st.stop()

    # selectbox kullandığımız için normalde boş olmaz ama yine de güvenlik:
    if eurohole == "Var" and not eurohole_name:
        st.error("❌ Eurohole aktif fakat 'Eurohole Dosyası' seçilmemiş!")
        st.stop()

    payload = {
        "boy_mm": boy_mm,
        "en_mm": en_mm,
        "birlesim": birlesim,
        "margin": margin,
        "sag_yapisma": dikis_kalinlik,
        "sol_yapisma": dikis_kalinlik,
        "yuvarlama": yuvarlama == "Var",

        "valf": valf == "Var",
        "valf_panel": valf_panel,
        "valf_ic_mesafe_mm": valf_mesafe,

        "gusset_base_name": gusset_base_name,
        "dosya_adi": dosya_adi_input,

        # Aç-kapa
        "ac_kapa": ac_kapa == "Var",
        "ac_kapa_yer": ac_kapa_yer,

        # Zipper
        "zipper": zipper == "Var",
        "zipper_name": zipper_name,
        "zip_mesafe": zip_mesafe,
        "sag_zip": sag_zip == "Var",

        # Eurohole
        "eurohole": eurohole == "Var",
        "eurohole_name": eurohole_name,
        "eurohole_mesafe": eurohole_mesafe,
    }

    try:
        res = requests.post(f"{BACKEND_URL}/gusset-die-line", json=payload)

        if res.status_code == 200:
            pdf_bytes = res.content

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
