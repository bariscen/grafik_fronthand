import streamlit as st
import fitz
import pandas as pd
import requests
import json
from gcs import upload_pdf_to_gcs

# =========================
# CONFIG
# =========================
BACKEND_URL = "https://sesa-grafik-api-1003931228830.europe-southwest1.run.app"   # Streamlit Cloud -> secrets önerilir

st.set_page_config(page_title="DieLine Tool", layout="wide")
st.title("Ön Repro Analizi")
st.info("⚠️ Lütfen gerçek kişilere ait kişisel veri (isim, telefon, adres, imza vb.) içeren dosyalar yüklemeyiniz. Dosyalar yalnızca teknik analiz amacıyla geçici olarak işlenir ve saklanmaz.")

# =========================
# Upload
# =========================
uploaded = st.file_uploader("PDF yükle", type=["pdf"], key="pdf_uploader_dieline")
if not uploaded:
    st.stop()

pdf_key = f"{uploaded.name}_{uploaded.size}"

# 1) PDF bytes'ı bir kere al
if st.session_state.get("pdf_key") != pdf_key:
    st.session_state["pdf_key"] = pdf_key
    st.session_state["pdf_bytes"] = uploaded.read()

    # yeni PDF geldi -> eski analiz çıktıları temizlenir
    for k in ["analysis_payload", "df", "meta", "report", "pdf_labeled"]:
        st.session_state.pop(k, None)

pdf_bytes = st.session_state["pdf_bytes"]

# 2) GCS'ye sadece PDF değişince upload et
if st.session_state.get("last_uploaded_to_gcs") != pdf_key:
    try:
        import io
        gcs_uri = upload_pdf_to_gcs(io.BytesIO(pdf_bytes), "sesa-grafik-bucket")
        st.session_state["last_uploaded_to_gcs"] = pdf_key
        st.session_state["gcs_uri"] = gcs_uri
        st.success("PDF güncellendi (overwrite edildi) ✅")
        st.write(gcs_uri)
    except Exception as e:
        st.error(f"GCS yükleme hatası: {e}")
        st.stop()  # istersen kaldır
else:
    st.caption("GCS: bu dosya zaten yüklü.")

# =========================
# State init
# =========================
if "analysis_ready" not in st.session_state:
    st.session_state["analysis_ready"] = False
if "analysis_running" not in st.session_state:
    st.session_state["analysis_running"] = False

left, right = st.columns([1, 2])

with left:
    st.subheader("Ayarlar")
    page_index = st.number_input("Sayfa index (0 tabanlı)", min_value=0, value=0, step=1, key="page_index")

    st.markdown("**Beklenen bıçak ölçüsü (mm)**")
    exp_w = st.number_input("Genişlik (mm)", min_value=1.0, value=255.0, step=1.0, key="exp_w")
    exp_h = st.number_input("Yükseklik (mm)", min_value=1.0, value=325.0, step=1.0, key="exp_h")

    # Sabit filtreler (senin kodundaki gibi)
    only_no_fill = True
    min_w = 80
    min_h = 80
    width_max = 2.0
    quant = 3

    if st.button("Analiz et", key="btn_analyze"):
        st.session_state["analysis_ready"] = True
        st.session_state["analysis_running"] = True

        # önceki sonuçları temizle
        for k in ["analysis_payload", "df", "meta", "report", "pdf_labeled"]:
            st.session_state.pop(k, None)

# =========================
# API helpers
# =========================
def api_analyze(
    gcs_uri: str,
    page_index: int,
    exp_w: float,
    exp_h: float,
    min_w: float,
    min_h: float,
    only_no_fill: bool,
    width_max: float,
    quant: int,
):
    if not gcs_uri:
        raise RuntimeError("api_analyze çağrıldı ama gcs_uri boş")

    data = {
        "mode": "analyze",
        "gcs_uri": gcs_uri,           # 👈 EVET, TAM BURASI
        "page_index": str(int(page_index)),
        "exp_w": str(float(exp_w)),
        "exp_h": str(float(exp_h)),
        "min_w": str(float(min_w)),
        "min_h": str(float(min_h)),
        "only_no_fill": "1" if only_no_fill else "0",
        "width_max": str(float(width_max)),
        "quant": str(int(quant)),
    }

    r = requests.post(
        f"{BACKEND_URL.rstrip('/')}/on_repro",
        data=data,
        timeout=300,
    )
    r.raise_for_status()
    return r.json()



def api_build_pdf(
    pdf_bytes: bytes,
    page_index: int,
    bbox_pt: list[float],
    quant: int,
    target_stroke: tuple[float, float, float] | None,
    target_width: float | None,
):
    files = {"file": ("upload.pdf", pdf_bytes, "application/pdf")}
    data = {
        "mode": "build_pdf",  # ✅ KRİTİK
        "page_index": str(int(page_index)),
        "bbox_pt": ",".join([str(float(x)) for x in bbox_pt]),
        "quant": str(int(quant)),
    }
    if target_stroke is not None:
        data["target_stroke"] = ",".join([str(float(x)) for x in target_stroke])
    if target_width is not None:
        data["target_width"] = str(float(target_width))

    r = requests.post(
        f"{BACKEND_URL.rstrip('/')}/on_repro",
        files=files,
        data=data,
        timeout=300,
    )

    # ✅ Eğer backend JSON hata döndürürse (bazı durumlarda), burada yakalayalım
    ct = (r.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        try:
            j = r.json()
        except Exception:
            j = {"detail": r.text}
        raise RuntimeError(f"Backend build_pdf JSON döndü: {j}")

    r.raise_for_status()
    return r.content

# =========================
# RIGHT PANEL
# =========================
with right:
    if not st.session_state["analysis_ready"]:
        st.info("Soldan ayarları yapıp **Analiz et**'e bas.")
        st.stop()

    if "analysis_payload" not in st.session_state:
        if st.session_state.get("analysis_running", False):
            st.info("Analiz ediliyor... Lütfen bekleyiniz.")

        with st.spinner("PDF analiz ediliyor..."):
            try:
                payload = api_analyze(
                    gcs_uri=st.session_state.get("gcs_uri", ""),
                    page_index=int(page_index),
                    exp_w=float(exp_w),
                    exp_h=float(exp_h),
                    min_w=float(min_w),
                    min_h=float(min_h),
                    only_no_fill=bool(only_no_fill),
                    width_max=float(width_max),
                    quant=int(quant),
                )


            except Exception as e:
                st.session_state["analysis_running"] = False
                st.error(f"API analiz hatası: {e}")
                st.stop()

        st.session_state["analysis_payload"] = payload
        st.session_state["analysis_running"] = False

        # parse
        st.session_state["df"] = payload.get("df", [])
        st.session_state["meta"] = payload.get("meta", {})
        st.session_state["report"] = payload.get("report", {})

    payload = st.session_state["analysis_payload"]
    df_list = st.session_state.get("df", []) or []
    meta = st.session_state.get("meta", {}) or {}
    report = st.session_state.get("report", {}) or {}

    if not df_list:
        st.warning("Hiç aday bulunamadı.")
        st.stop()

    # df -> ilk satır
    row = df_list[0]
    bbox = fitz.Rect(row["bbox_x0_pt"], row["bbox_y0_pt"], row["bbox_x1_pt"], row["bbox_y1_pt"])
    st.write(f"Seçilen ölçü: **{row['w_mm']:.2f} x {row['h_mm']:.2f} mm**, score={row['score']:.2f}")

    # Backend rapor objeleri
    color_report = (report.get("color_report") or {})
    text_mode = (report.get("text_mode") or {})
    q = (report.get("outline_text_quality") or {})
    dpi_check = (report.get("dpi_check") or {})
    barcode_info = (report.get("barcode_qr") or {})
    photosel = (report.get("photosel") or {})
    artwork_raster_ratio = report.get("artwork_raster_ratio")  # 0..1

    # ----------------------------------
    # DOSYA DURUMU
    # ----------------------------------
    with st.expander("DOSYA DURUMU", expanded=False):
        vec = (report.get("vector_check") or {})
        is_vec = bool(vec.get("is_vector", True))
        vec_count = int(vec.get("paths", 0) or 0)
        st.write(f"**Vektörel Durumu:** {'Vektörel' if is_vec else 'Vektörel Değil'} ({vec_count} vektör)")

        sel_w = float(row["w_mm"])
        sel_h = float(row["h_mm"])
        tol_mm = 0.2
        same_size = (abs(sel_w - float(exp_w)) <= tol_mm) and (abs(sel_h - float(exp_h)) <= tol_mm)
        if same_size:
            st.write(f"**Çizim Durumu:** Çizim bulundu, bıçak boyu (Beklenen: {float(exp_w):.1f} x {float(exp_h):.1f} mm | Seçilen: {sel_w:.1f} x {sel_h:.1f} mm)")
        else:
            st.write(f"**Çizim Durumu:** Çizim bulundu (Beklenen: {float(exp_w):.1f} x {float(exp_h):.1f} mm | Seçilen: {sel_w:.1f} x {sel_h:.1f} mm)")

        if artwork_raster_ratio is None:
            st.write("**Çizimdeki Raster Oranı:** Bilinmiyor")
        else:
            st.write(f"**Çizimdeki Raster Oranı:** %{float(artwork_raster_ratio)*100.0:.1f}")

        has_rgb = bool(color_report.get("has_rgb_in_bbox"))
        has_cmyk = bool(color_report.get("has_cmyk_in_bbox"))
        has_spot = bool(color_report.get("has_spot_in_bbox"))
        if has_rgb:
            renk_durumu = "RGB"
        else:
            if has_cmyk and has_spot:
                renk_durumu = "CMYK + SPOT"
            elif has_cmyk:
                renk_durumu = "CMYK"
            elif has_spot:
                renk_durumu = "SPOT"
            else:
                renk_durumu = "Bilinmiyor"
        st.write(f"**Renk Durumu:** {renk_durumu}")

    # ----------------------------------
    # RENK DETAYI
    # ----------------------------------
    with st.expander("RENK DETAYI", expanded=False):
        cmyk_palette = (color_report.get("cmyk_spot_palette") or {})
        top_cmyk = cmyk_palette.get("top_cmyk_colors", []) or []

        has_cmyk = bool(color_report.get("has_cmyk_in_bbox"))
        if has_cmyk:
            non_zero_c = [c for c in top_cmyk if (c.get("cmyk", {}).get("c", 0) or 0) > 0]
            cmyk_status = "Sadece MYK" if (top_cmyk and len(non_zero_c) == 0) else "Var"
        else:
            cmyk_status = "Yok"
        st.write(f"**CMYK:** {cmyk_status}")

        spot_colors = color_report.get("spot_colors", []) or []
        st.write("**Spot Renkler:** " + (", ".join(spot_colors) if spot_colors else "Yok"))

        spot_cov = (color_report.get("spot_coverage") or {}).get("spots", {}).get("ANY_SPOT", {}) or {}
        spot_ratio = float(spot_cov.get("ratio_in_bbox", 0.0)) * 100.0
        st.write(f"**Spot Renklerin Çizimdeki Oranı:** %{spot_ratio:.2f}")

        if top_cmyk:
            st.markdown("**En Baskın CMYK Renkleri (Top):**")
            for i, item in enumerate(top_cmyk[:8], start=1):
                cmyk = item.get("cmyk", {})
                ratio = float(item.get("ratio", 0.0)) * 100.0
                st.write(f"{i}. C:{cmyk.get('c',0):.3f}  M:{cmyk.get('m',0):.3f}  Y:{cmyk.get('y',0):.3f}  K:{cmyk.get('k',0):.3f}  → %{ratio:.2f}")
        else:
            st.write("**En Baskın CMYK Renkleri:** Veri yok")

    # ----------------------------------
    # YAZI DETAYI
    # ----------------------------------
    with st.expander("YAZI DETAYI", expanded=False):
        text_mode_val = (text_mode or {}).get("mode")
        yazi_durumu = "Yazı (Seçilebilir)" if text_mode_val == "SELECTABLE_TEXT" else "Outline"
        st.write(f"**Yazı Durumu:** {yazi_durumu}")

        tl = (q or {}).get("luma", {}).get("text_luma", {}) or {}
        is_dark = tl.get("is_dark")

        if not tl or is_dark is None:
            st.write("**Yazı Parlaklığı:** Bilinmiyor")
        else:
            st.write(f"**Yazı Parlaklığı:** {'Koyu' if is_dark else 'Açık'}")

        char_ok = bool((q or {}).get("rules", {}).get("char_height_ok"))
        if char_ok:
            st.write("**Yazı Boyu:** Uygun")
        else:
            reason = "Açık renk yazı 1.12 mm’den kısa" if (is_dark is False) else "1.12 mm’den kısa yazı"
            st.write(f"**Yazı Boyu:** Uygun olmayanlar işaretlendi  \nNedeni: {reason}")

        stroke_ok = bool((q or {}).get("rules", {}).get("stroke_ok"))
        if stroke_ok:
            st.write("**Yazı Kalınlığı:** Uygun")
        else:
            reason = "Açık renk yazı 0.17 mm’den ince" if (is_dark is False) else "0.17 mm’den ince stroke"
            st.write(f"**Yazı Kalınlığı:** Uygun olmayanlar işaretlendi  \nNedeni: {reason}")

        dpi_summary = (dpi_check.get("summary") or {})
        images_low = dpi_summary.get("images_low")
        if images_low is None:
            st.write("**DPI:** Bilinmiyor")
        elif int(images_low) == 0:
            st.write("**DPI:** Uygun (300+)")
        else:
            st.write("**DPI:** Uygun olmayanlar işaretlendi")

    # ----------------------------------
    # AIDC DETAYI
    # ----------------------------------
    with st.expander("AIDC DETAYI", expanded=False):
        bq = (barcode_info or {})

        st.write(f"**Barkod:** {'Var' if bq.get('has_barcode') else 'Yok'}")
        if bq.get("has_barcode"):
            st.write(f"**Barkod Cinsi:** {bq.get('barcode_type')}")
            st.write(f"**Barkod Numarası:** {bq.get('barcode_number')}")
            st.write(f"**Barkod Kontrastı:** {'Var' if (bq.get('barcode_contrast') or {}).get('ok') else 'Yok'}")
            st.write(f"**Barkod Boyu 30mm büyük:** {'Evet' if bq.get('barcode_size_ge_30mm') else 'Hayır'}")
            s = bq.get("barcode_size_mm")
            if s:
                st.caption(f"Boy: {s.get('w_mm',0):.1f} x {s.get('h_mm',0):.1f} mm (max {s.get('max_mm',0):.1f} mm)")

        st.write(f"**QR:** {'Var' if bq.get('has_qr') else 'Yok'}")
        if bq.get("has_qr"):
            st.write(f"**QR:** {'Okunabilir' if bq.get('qr_works') else 'Okunamaz'}")
            qs = bq.get("qr_size_mm")
            QR_MIN_MM = 15.0
            if qs:
                ok = (qs.get("min_mm", 0) >= QR_MIN_MM)
                st.write(f"**QR Boyu:** {'Uygun' if ok else 'Uygun Değil'} ({qs.get('w_mm',0):.1f}x{qs.get('h_mm',0):.1f} mm)")
            else:
                st.write("**QR Boyu:** Bilinmiyor")

        ph = (photosel or {})
        has_photosel = bool(ph.get("has_photosel"))
        st.write(f"**Fotosel:** {'Var' if has_photosel else 'Yok'}")

        if has_photosel:
            st.warning("DİKKAT: FOTOSEL YOLUNU KONTROL ET")

            area_mm2 = ph.get("area_mm2")
            area_ok = ph.get("area_ge_50mm2")
            if area_mm2 is not None:
                st.write(f"**Fotosel Alanı:** {float(area_mm2):.1f} mm²")
            else:
                st.write("**Fotosel Alanı:** Bilinmiyor")

            if area_ok is None:
                st.write("**Fotosel Boyu (>=50mm²):** Bilinmiyor")
            else:
                st.write(f"**Fotosel Boyu (>=50mm²):** {'Uygun' if area_ok else 'Uygun Değil'}")

            uf_ok = ph.get("uniform_fill_ok")
            if uf_ok is None:
                st.write("**Fotosel Kontrastlı:** Bilinmiyor")
            else:
                st.write(f"**Fotosel Kontrastlı:** {'Okunabilir' if uf_ok else 'Okunamaz'}")

    # ----------------------------------
    # PDF oluştur (backend)
    # ----------------------------------
    st.markdown("### İşaretlenmiş PDF")

    if st.button("PDF Oluştur", key="btn_make_highlight_with_labels"):
        with st.spinner("PDF oluşturuluyor..."):
            try:
                target_stroke = None
                if "stroke_rgb" in row and row["stroke_rgb"] is not None:
                    sv = row["stroke_rgb"]
                    if isinstance(sv, str):
                        sv = sv.strip().strip("()")
                        target_stroke = tuple(float(x.strip()) for x in sv.split(","))
                    elif isinstance(sv, (tuple, list)) and len(sv) == 3:
                        target_stroke = tuple(float(x) for x in sv)

                target_width = float(row["width_pt"]) if row.get("width_pt") is not None else None

                pdf_out = api_build_pdf(
                    pdf_bytes=pdf_bytes,
                    page_index=int(page_index),
                    bbox_pt=[bbox.x0, bbox.y0, bbox.x1, bbox.y1],
                    quant=int(quant),
                    target_stroke=target_stroke,
                    target_width=target_width,
                )
                st.session_state["pdf_labeled"] = pdf_out
                st.success("PDF üretildi.")
            except Exception as e:
                st.error(f"PDF oluşturma hatası: {e}")

    if "pdf_labeled" in st.session_state:
        st.download_button(
            "İndir: highlight + ölçülü PDF",
            data=st.session_state["pdf_labeled"],
            file_name="highlight_measure_labels.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="download_highlight_measure_labels"
        )
