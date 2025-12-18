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



import io
import zipfile
import tempfile
from pathlib import Path

import streamlit as st

# ⚠️ code.py adını kullanma (stdlib ile çakışır)
# process_pdf senin fonksiyonun burada olmalı:
from pages.convert_pdf import process_pdf


st.set_page_config(page_title="PDF Hatch", layout="centered")
st.title("PDF Tarama (Tek PDF + Batch)")

# Ortak sabit parametreler
HEDEF_KALINLIK = 2.83
TARAMA_ARALIGI = 6
BEZIER_ADIM = 20
BUFFER_EPS = 0.01

# 2 çıktı ayarı
JOB_CONFIGS = [
    {"TARAMA_ACISI_DERECE": 45,  "yon": 2},
    {"TARAMA_ACISI_DERECE": 135, "yon": 1},
]

tab_single, tab_batch = st.tabs(["Tek PDF", "Batch (çoklu PDF)"])


## =========================
# TEK PDF TAB (ZIP indir)
# =========================
with tab_single:
    st.subheader("Tek PDF Tarama (2 çıktı → tek indirme)")
    uploaded = st.file_uploader(
        "PDF yükle",
        type=["pdf"],
        accept_multiple_files=False,
        key="single_uploader"
    )

    run_single = st.button(
        "İşlemi Başlat (Tek PDF)",
        type="primary",
        disabled=not uploaded,
        key="run_single"
    )

    if run_single:
        if not uploaded:
            st.error("PDF seçilmedi.")
            st.stop()

        zip_buffer = io.BytesIO()

        with st.spinner("İşleniyor..."):
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)

                safe_name = Path(uploaded.name).name
                tmp_input = td / safe_name
                tmp_input.write_bytes(uploaded.getbuffer())

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for cfg in JOB_CONFIGS:
                        out_path = process_pdf(
                            dosya_adi=str(tmp_input),
                            hedef_kalinlik=HEDEF_KALINLIK,
                            tarama_araligi=TARAMA_ARALIGI,
                            bezier_adim=BEZIER_ADIM,
                            buffer_eps=BUFFER_EPS,
                            tarama_acisi_derece=cfg["TARAMA_ACISI_DERECE"],
                            yon=cfg["yon"],
                        )

                        out_path = Path(out_path)
                        zf.write(out_path, arcname=out_path.name)

        zip_buffer.seek(0)

        st.success("Tamamlandı. 2 çıktı birlikte indirilebilir.")

        st.download_button(
            label="Çıktıları indir (ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"{Path(uploaded.name).stem}_outputs.zip",
            mime="application/zip",
            key="single_zip_download",
        )



# =========================
# BATCH TAB
# =========================
with tab_batch:
    st.subheader("Batch (çoklu PDF) → ZIP indir")
    st.write("Klasördeki PDF’leri topluca seçip yükle → hepsi işlenir → ZIP olarak indirirsin.")

    uploaded_files = st.file_uploader(
        "PDF dosyalarını seç",
        type=["pdf"],
        accept_multiple_files=True,
        key="batch_uploader",
    )

    run_batch = st.button("İşlemi Başlat (Batch)", type="primary", disabled=not uploaded_files, key="run_batch")

    if run_batch:
        if not uploaded_files:
            st.error("PDF seçilmedi.")
            st.stop()

        progress = st.progress(0)
        status = st.empty()

        zip_buffer = io.BytesIO()
        ok_count = 0
        fail_count = 0
        failures = []

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)

            # input’ları temp’e yaz
            input_paths = []
            for uf in uploaded_files:
                safe_name = Path(uf.name).name
                p = td / safe_name
                p.write_bytes(uf.getbuffer())
                input_paths.append(p)

            total_jobs = len(input_paths) * len(JOB_CONFIGS)
            done = 0

            with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for pdf_path in input_paths:
                    for cfg in JOB_CONFIGS:
                        try:
                            status.write(f"İşleniyor: {pdf_path.name} | açı={cfg['TARAMA_ACISI_DERECE']} | yon={cfg['yon']}")

                            out_path = process_pdf(
                                dosya_adi=str(pdf_path),
                                hedef_kalinlik=HEDEF_KALINLIK,
                                tarama_araligi=TARAMA_ARALIGI,
                                bezier_adim=BEZIER_ADIM,
                                buffer_eps=BUFFER_EPS,
                                tarama_acisi_derece=cfg["TARAMA_ACISI_DERECE"],
                                yon=cfg["yon"],
                            )

                            out_path = Path(out_path)
                            zf.write(out_path, arcname=out_path.name)
                            ok_count += 1

                        except Exception as e:
                            fail_count += 1
                            failures.append((pdf_path.name, cfg, str(e)))

                        done += 1
                        progress.progress(min(1.0, done / total_jobs))

        zip_buffer.seek(0)

        st.success(f"Tamamlandı. Başarılı: {ok_count} | Hatalı: {fail_count}")

        if failures:
            with st.expander("Hatalar"):
                for name, cfg, err in failures:
                    st.write(f"- {name} | açı={cfg['TARAMA_ACISI_DERECE']} | yon={cfg['yon']} -> {err}")

        st.download_button(
            "Çıktıları ZIP olarak indir",
            data=zip_buffer.getvalue(),
            file_name="pdf_outputs.zip",
            mime="application/zip",
            key="dl_zip",
        )
