import streamlit as st
import fitz
import pandas as pd
import requests
import json
import numpy as np
import cv2
import io
from gcs import upload_pdf_to_gcs

# ==========================================
# 1. SABİT FİLTRELER VE FONKSİYON
# ==========================================
# İhtiyacına göre bu sabitleri buradan güncelleyebilirsin
MIN_AREA = 8000
MIN_W = 200
MIN_H = 200
MIN_SOLIDITY = 0.6
DPI_PREVIEW = 120

def get_filtered_bboxes(page, dpi=150):
    pix = page.get_pixmap(dpi=dpi, alpha=True)
    img_data = np.frombuffer(pix.tobytes("png"), np.uint8)
    img = cv2.imdecode(img_data, cv2.IMREAD_UNCHANGED)
    if img is None: return []

    alpha = img[:, :, 3]
    kernel = np.ones((5,5), np.uint8)
    thresh = cv2.threshold(alpha, 1, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bboxes = []
    scale = 72 / dpi
    page_rect = page.rect

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        rect = fitz.Rect(x * scale, y * scale, (x + w) * scale, (y + h) * scale)

        # Hayalet Kutu Engelleme
        if rect.width > page_rect.width * 0.9 or rect.height > page_rect.height * 0.9:
            continue

        # Solidity Hesabı
        area_pixel = cv2.contourArea(cnt)
        solidity = float(area_pixel) / (w * h) if (w * h) > 0 else 0

        pt_w, pt_h = w * scale, h * scale
        pt_area = (pt_w * pt_h)

        if pt_area > MIN_AREA and pt_w > MIN_W and pt_h > MIN_H:
            if solidity > MIN_SOLIDITY:
                bboxes.append(rect)

    bboxes.sort(key=lambda r: (r.y0, r.x0))
    return bboxes

# ==========================================
# 2. UI BAŞLANGIÇ
# ==========================================
st.set_page_config(page_title="DieLine Tool v2", layout="wide")
st.title("🛡️ Çok Sayfalı Ambalaj Seçici")

uploaded = st.file_uploader("PDF yükle", type=["pdf"])

if uploaded:
    pdf_bytes = uploaded.getvalue()
    pdf_key = f"{uploaded.name}_{uploaded.size}"
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # State yönetimi: Seçilen kutuları saklamak için
    if "selected_boxes_map" not in st.session_state:
        st.session_state["selected_boxes_map"] = {}

    st.info(f"PDF yüklendi: {len(doc)} sayfa tarandı. Lütfen parçaları seçin.")

    # ==========================================
    # 3. TÜM SAYFALARI GÖSTER VE SEÇTİR
    # ==========================================
    for pg_idx in range(len(doc)):
        page = doc[pg_idx]
        boxes = get_filtered_bboxes(page)

        if boxes:
            st.markdown(f"### 📄 Sayfa {pg_idx + 1}")
            cols = st.columns(2)

            for i, box in enumerate(boxes):
                with cols[i % 2]:
                    # 0.3 zoom ile önizleme
                    pix_crop = page.get_pixmap(matrix=fitz.Matrix(0.3, 0.3), clip=box)
                    st.image(pix_crop.tobytes("png"), caption=f"Sayfa {pg_idx+1} - Parça {i}")

                    # Seçim Checkbox'ı
                    cb_key = f"cb_{pg_idx}_{i}"
                    if st.checkbox(f"Seç (P:{pg_idx+1}, ID:{i})", key=cb_key):
                        st.session_state["selected_boxes_map"][cb_key] = (pg_idx, box)
                    else:
                        st.session_state["selected_boxes_map"].pop(cb_key, None)
            st.divider()

    # ==========================================
    # 4. İŞLEME VE GCS TRANSFER
    # ==========================================
    if st.button("🚀 Seçili Parçaları İşle, GCS'ye Yükle ve PDF İndir", use_container_width=True):
        if not st.session_state["selected_boxes_map"]:
            st.error("Lütfen en az bir parça seçin!")
        else:
            with st.spinner("Vektörel PDF oluşturuluyor ve GCS'ye aktarılıyor..."):
                try:
                    # Yeni bir PDF oluşturmak yerine mevcut PDF üzerine vektörel çizim yapıyoruz
                    output_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

                    # Seçilen kutuları ilgili sayfalara çiz
                    for key, (pg_idx, box) in st.session_state["selected_boxes_map"].items():
                        out_page = output_doc[pg_idx]
                        # Vektörel kırmızı çerçeve çizimi
                        out_page.draw_rect(box, color=(1, 0, 0), width=2)

                    final_pdf_bytes = output_doc.write()

                    # 1. GCS'ye Yükle
                    gcs_uri = upload_pdf_to_gcs(io.BytesIO(final_pdf_bytes), "sesa-grafik-bucket")
                    st.session_state["final_gcs_uri"] = gcs_uri
                    st.session_state["final_pdf_bytes"] = final_pdf_bytes

                    st.success(f"✅ İşlem Tamamlandı! GCS Adresi: {gcs_uri}")
                    st.balloons()

                except Exception as e:
                    st.error(f"Bir hata oluştu: {e}")

    # İndirme Butonu
    if "final_pdf_bytes" in st.session_state:
        st.download_button(
            label="📥 İşaretlenmiş Vektörel PDF'i İndir",
            data=st.session_state["final_pdf_bytes"],
            file_name=f"isaretli_{uploaded.name}",
            mime="application/pdf",
            use_container_width=True
        )

    doc.close()
