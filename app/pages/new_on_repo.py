import streamlit as st
import fitz
import numpy as np
import cv2
import io
import requests
from gcs import upload_pdf_to_gcs
from urllib.parse import urlencode

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
        if img is None:
            continue

        alpha = img[:, :, 3]
        kernel = np.ones((5, 5), np.uint8)
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

    doc.close()
    return all_boxes


# ==========================================
# Yardımcılar: checkbox state temizleme + bbox sayma
# ==========================================
def clear_all_checkbox_states():
    for k in list(st.session_state.keys()):
        if k.startswith("check_"):
            del st.session_state[k]


def bbox_lines_from_payload(payload: dict) -> list[str]:
    if not payload or "bbox_pt" not in payload or not payload["bbox_pt"]:
        return []
    return [p.strip() for p in payload["bbox_pt"].split("|") if p.strip()]


# ==========================================
# 2. UI & SEÇİM ALANI
# ==========================================
st.set_page_config(page_title="Pro Repro Seçici", layout="wide")
st.title("🛡️ Ambalaj Seçici & Backend Analizi")

uploaded = st.file_uploader("PDF yükle", type=["pdf"])

if uploaded:
    pdf_bytes = uploaded.getvalue()

    # ✅ PDF değişince eski seçimleri temizle
    if st.session_state.get("last_pdf") != uploaded.name:
        clear_all_checkbox_states()

    # Manuel temizleme butonu
    if st.button("🧹 Seçimleri temizle"):
        clear_all_checkbox_states()
        st.rerun()

    # 1) Orijinal PDF'i GCS'ye yükle (Backend'in okuyabilmesi için)
    if "gcs_uri" not in st.session_state or st.session_state.get("last_pdf") != uploaded.name:
        with st.spinner("Dosya GCS'ye aktarılıyor..."):
            gcs_uri = upload_pdf_to_gcs(io.BytesIO(pdf_bytes), "sesa-grafik-bucket")
            st.session_state["gcs_uri"] = gcs_uri
            st.session_state["last_pdf"] = uploaded.name
    else:
        gcs_uri = st.session_state["gcs_uri"]

    all_boxes_map = get_all_pdf_boxes(pdf_bytes)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # ==========================================
    # FORM: seçim + 2 buton
    # ==========================================
    with st.form("selection_form"):
        st.info("Analiz edilecek parçaları seçin.")

        selected_boxes_data = []

        for pg_idx, boxes in all_boxes_map.items():
            if not boxes:
                continue

            st.markdown(f"### 📄 Sayfa {pg_idx + 1}")
            cols = st.columns(2)

            for i, box in enumerate(boxes):
                with cols[i % 2]:
                    pix_crop = doc[pg_idx].get_pixmap(matrix=fitz.Matrix(0.3, 0.3), clip=box)
                    st.image(pix_crop.tobytes("png"))

                    cb_key = f"{pg_idx}_{i}"
                    if st.checkbox(f"Seç: Sayfa {pg_idx + 1}-ID {i}", key=f"check_{cb_key}"):
                        selected_boxes_data.append({"pg": pg_idx, "box": box})

            st.divider()

        # ✅ Backend'e gidecek payload'ı üret (BOŞLUKSUZ '|' delimiter)
        backend_payload = None
        if selected_boxes_data:
            bbox_payload = "|".join([
                f"{item['box'].x0},{item['box'].y0},{item['box'].x1},{item['box'].y1}"
                for item in selected_boxes_data
            ])

            backend_payload = {
                "gcs_uri": st.session_state["gcs_uri"],
                "page_index": str(selected_boxes_data[0]["pg"]),  # backend böyle istiyorsa kalsın
                "bbox_pt": bbox_payload,
            }

        see_payload_btn = st.form_submit_button("👁️ Backend'e gidecek verileri gör")
        submit_button = st.form_submit_button("🚀 Seçimleri Backend'de Analiz Et", use_container_width=True)

    # ==========================================
    # FORM DIŞI: her durumda seçili kutu sayısını göster
    # ==========================================
    bbox_lines = bbox_lines_from_payload(backend_payload)
    if backend_payload:
        st.success(f"✅ Şu an backend'e gidecek kutu sayısı: {len(bbox_lines)}")

    # ==========================================
    # 3A. BACKEND'E GİDECEK VERİLERİ GÖSTER (backend'e istek atmaz)
    # ==========================================
    if see_payload_btn:
        if not backend_payload:
            st.warning("Lütfen en az bir parça seçin.")
        else:
            st.subheader("📨 Backend'e GİDECEK PAYLOAD (dict)")
            st.json({**backend_payload, "bbox_sayisi": len(bbox_lines)})

            st.subheader("📦 bbox_pt satırları (her satır = 1 kutu)")
            st.code("\n".join(bbox_lines), language="text")

            st.subheader("🧾 RAW request body (requests form-data olarak bunu yollar)")
            raw_body = urlencode(backend_payload)
            st.code(raw_body, language="text")

    # ==========================================
    # 3B. BACKEND HABERLEŞMESİ
    # ==========================================
    if submit_button:
        if not backend_payload:
            st.warning("Lütfen en az bir parça seçin.")
        else:
            # ✅ Göndermeden hemen önce: gerçekten ne gidecek göster ve sakla
            raw_body = urlencode(backend_payload)
            st.session_state["last_payload"] = backend_payload
            st.session_state["last_raw_body"] = raw_body

            st.info(f"Gönderiliyor... (Kutu sayısı: {len(bbox_lines)})")
            st.json({**backend_payload, "bbox_sayisi": len(bbox_lines)})
            st.code(raw_body, language="text")

            try:
                response = requests.post(BACKEND_URL, data=backend_payload, timeout=300)

                if response.status_code == 200:
                    final_pdf_content = response.content
                    st.success(f"✅ {len(bbox_lines)} bölge başarıyla analiz edildi!")

                    st.download_button(
                        label="📥 Tüm Analizleri İçeren PDF'i İndir",
                        data=final_pdf_content,
                        file_name=f"analizli_{uploaded.name}",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.error(f"Backend hatası: {response.text}")

            except Exception as e:
                st.error(f"Backend erişilemiyor / hata: {e}")

    # ==========================================
    # 4. EN SON GÖNDERİLEN İSTEĞİ GÖSTER (backend çökmüş olsa bile kanıt)
    # ==========================================
    if "last_payload" in st.session_state:
        st.subheader("🧾 Son gönderilen payload (session_state)")
        st.json(st.session_state["last_payload"])

    if "last_raw_body" in st.session_state:
        st.subheader("🧾 Son gönderilen RAW body (session_state)")
        st.code(st.session_state["last_raw_body"], language="text")

    doc.close()
