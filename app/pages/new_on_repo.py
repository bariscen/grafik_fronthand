import streamlit as st
import fitz
import numpy as np
import cv2
import io
import requests  # <--- YÜKLENMESİ GEREKEN KÜTÜPHANE
from gcs import upload_pdf_to_gcs

# Backend URL'iniz (Cloud Run adresi)
BACKEND_URL = "https://sesa-grafik-api-1003931228830.europe-southwest1.run.app/on_repro"

# ==========================================
# 1. ANALİZİ HAFIZAYA AL (Donmayı Önleyen Kısım)
# ==========================================
@st.cache_resource(show_spinner="Sayfalar taranıyor, lütfen bekleyin...")
def get_all_pdf_boxes(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_boxes = {}
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
st.set_page_config(page_title="Pro Repro Seçici", layout="wide")
st.title("🛡️ Ambalaj Seçici & Backend Analizi")

uploaded = st.file_uploader("PDF yükle", type=["pdf"])

if uploaded:
    pdf_bytes = uploaded.getvalue()

    # 1. Adım: Orijinal PDF'i GCS'ye yükle (Backend'in okuyabilmesi için)
    if "gcs_uri" not in st.session_state or st.session_state.get("last_pdf") != uploaded.name:
        with st.spinner("Dosya GCS'ye aktarılıyor..."):
            gcs_uri = upload_pdf_to_gcs(io.BytesIO(pdf_bytes), "sesa-grafik-bucket")
            st.session_state["gcs_uri"] = gcs_uri
            st.session_state["last_pdf"] = uploaded.name

    all_boxes_map = get_all_pdf_boxes(pdf_bytes)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    with st.form("selection_form"):
        st.info("Analiz edilecek parçaları seçin.")

        # Seçilenlerin koordinatlarını tutacak liste
        selected_boxes_data = []

        for pg_idx, boxes in all_boxes_map.items():
            if not boxes: continue
            st.markdown(f"### 📄 Sayfa {pg_idx + 1}")
            cols = st.columns(2)
            for i, box in enumerate(boxes):
                with cols[i % 2]:
                    pix_crop = doc[pg_idx].get_pixmap(matrix=fitz.Matrix(0.3, 0.3), clip=box)
                    st.image(pix_crop.tobytes("png"))

                    cb_key = f"{pg_idx}_{i}"
                    if st.checkbox(f"Seç: Sayfa {pg_idx+1}-ID {i}", key=f"check_{cb_key}"):
                        # Koordinatları ve sayfa bilgisini listeye ekle
                        selected_boxes_data.append({"pg": pg_idx, "box": box})
            st.divider()

        submit_button = st.form_submit_button("🚀 Seçimleri Backend'de Analiz Et", use_container_width=True)

    # ==========================================
    # 3. BACKEND HABERLEŞMESİ (DÜZELTİLMİŞ & TEK SEFERLİK)
    # ==========================================
    if submit_button:
        # 1. Sadece o an checkbox'ı işaretli olanları topla
        temiz_secim = []
        target_page = 0
        for pg_idx, boxes in all_boxes_map.items():
            for i, box in enumerate(boxes):
                if st.session_state.get(f"check_{pg_idx}_{i}"):
                    temiz_secim.append(box)
                    target_page = pg_idx

        if not temiz_secim:
            st.warning("Lütfen en az bir parça seçin.")
        else:
            with st.spinner(f"Backend {len(temiz_secim)} parçayı işliyor..."):

                # 2. Koordinatları paketle (Backend'de split("|") yapılacak format)
                bbox_payload = " | ".join([f"{b.x0},{b.y0},{b.x1},{b.y1}" for b in temiz_secim])

                payload = {
                    "gcs_uri": st.session_state["gcs_uri"],
                    "page_index": str(target_page),
                    "bbox_pt": bbox_payload,
                    "quant": "3",
                    "exp_w": "255.0",
                    "exp_h": "325.0"
                }

                try:
                    # 3. Backend'e TEK BİR istek gönder (Tekrar eden bloklar silindi)
                    response = requests.post(BACKEND_URL, data=payload, timeout=300)

                    if response.status_code == 200:
                        final_pdf_content = response.content
                        st.success(f"✅ {len(temiz_secim)} bölge başarıyla analiz edildi!")

                        # 4. GCS Yedeği (Hata olsa bile indirmeye engel olmasın)
                        try:
                            final_uri = upload_pdf_to_gcs(io.BytesIO(final_pdf_content), "sesa-grafik-bucket")
                            st.caption(f"Bulut Yedeği: {final_uri}")
                        except:
                            pass

                        # 5. İNDİRME BUTONU
                        st.download_button(
                            label="📥 Analizli PDF'i İndir",
                            data=final_pdf_content,
                            file_name=f"analizli_{uploaded.name}",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        # Backend'den gelen hata detayını göster
                        st.error(f"Backend hatası: {response.text}")

                except Exception as e:
                    st.error(f"Bağlantı hatası: {e}")

    # Belgeyi kapat (Hatanın dışına aldık)
    if 'doc' in locals():
        doc.close()
