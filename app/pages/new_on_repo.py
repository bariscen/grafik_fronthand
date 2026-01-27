import streamlit as st
import fitz
import numpy as np
import cv2
import io
from gcs import upload_pdf_to_gcs

# ==========================================
# 1. ANALİZİ HAFIZAYA AL (Donmayı Önleyen Kısım)
# ==========================================
@st.cache_resource(show_spinner="Sayfalar taranıyor, lütfen bekleyin...")
def get_all_pdf_boxes(pdf_bytes):
    """PDF'i bir kez analiz eder ve tüm kutuları hafızada tutar."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_boxes = {}

    # Sabit Filtreler
    MIN_AREA, MIN_W, MIN_H, MIN_SOLIDITY = 8000, 200, 200, 0.6

    for pg_idx in range(len(doc)):
        page = doc[pg_idx]
        pix = page.get_pixmap(dpi=120, alpha=True)
        img_data = np.frombuffer(pix.tobytes("png"), np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_UNCHANGED)

        if img is None: continue

        alpha = img[:, :, 3]
        kernel = np.ones((5,5), np.uint8)
        thresh = cv2.threshold(alpha, 1, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bboxes = []
        scale = 72 / 120
        page_rect = page.rect

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            rect = fitz.Rect(x * scale, y * scale, (x + w) * scale, (y + h) * scale)
            if rect.width > page_rect.width * 0.9 or rect.height > page_rect.height * 0.9:
                continue
            solidity = float(cv2.contourArea(cnt)) / (w * h) if (w * h) > 0 else 0
            if (rect.width * rect.height) > MIN_AREA and rect.width > MIN_W and rect.height > MIN_H:
                if solidity > MIN_SOLIDITY:
                    bboxes.append(rect)

        bboxes.sort(key=lambda r: (r.y0, r.x0))
        all_boxes[pg_idx] = bboxes
    return all_boxes

# ==========================================
# 2. UI & SEÇİM ALANI
# ==========================================
st.set_page_config(page_title="Hızlı Seçici", layout="wide")
st.title("🛡️ Performans Odaklı Ambalaj Seçici")

uploaded = st.file_uploader("PDF yükle", type=["pdf"])

if uploaded:
    pdf_bytes = uploaded.getvalue()

    # PDF analizini bir kez yap ve cache'le
    with st.spinner("PDF derinlemesine analiz ediliyor..."):
        all_boxes_map = get_all_pdf_boxes(pdf_bytes)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Seçimleri saklamak için session_state
    if "selected_keys" not in st.session_state:
        st.session_state["selected_keys"] = set()

    # --- SEÇİM FORMU (Loading dönmesini engeller) ---
    with st.form("selection_form"):
        st.info("Parçaları seçin ve en alttaki 'Seçimleri Onayla ve İşle' butonuna basın.")

        for pg_idx, boxes in all_boxes_map.items():
            if not boxes: continue

            st.markdown(f"### 📄 Sayfa {pg_idx + 1}")
            cols = st.columns(2)

            for i, box in enumerate(boxes):
                with cols[i % 2]:
                    # Önizleme
                    pix_crop = doc[pg_idx].get_pixmap(matrix=fitz.Matrix(0.3, 0.3), clip=box)
                    st.image(pix_crop.tobytes("png"))

                    cb_key = f"{pg_idx}_{i}"
                    is_selected = st.checkbox(f"Seç: P{pg_idx+1}-I{i}", key=f"check_{cb_key}")
                    if is_selected:
                        st.session_state["selected_keys"].add(cb_key)
                    else:
                        st.session_state["selected_keys"].discard(cb_key)
            st.divider()

        submit_button = st.form_submit_button("🚀 Seçimleri Onayla ve GCS'ye Gönder", use_container_width=True)

    # ==========================================
    # 3. İŞLEME (Sadece Butona Basınca Çalışır)
    # ==========================================
    if submit_button:
        if not st.session_state["selected_keys"]:
            st.warning("Hiç parça seçilmedi.")
        else:
            with st.spinner("Vektörel PDF üretiliyor..."):
                output_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

                for key in st.session_state["selected_keys"]:
                    p_idx, b_idx = map(int, key.split("_"))
                    target_box = all_boxes_map[p_idx][b_idx]
                    output_doc[p_idx].draw_rect(target_box, color=(1, 0, 0), width=2)

                final_bytes = output_doc.write()

                # GCS'ye Yükle
                try:
                    gcs_uri = upload_pdf_to_gcs(io.BytesIO(final_bytes), "sesa-grafik-bucket")
                    st.success(f"GCS Yükleme Başarılı: {gcs_uri}")
                    st.download_button("📥 İşaretli PDF'i İndir", final_bytes, "isaretli.pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"GCS Hatası: {e}")

    doc.close()
