import streamlit as st
import fitz
import pandas as pd
import requests
import json
import numpy as np
import cv2
import io
from gcs import upload_pdf_to_gcs # Mevcut GCS yükleme fonksiyonun

# ==========================================
# 1. HAYALET KUTU ENGELLEYİCİ FONKSİYON
# ==========================================
def get_filtered_bboxes(page, dpi=150, min_area=1500, min_w=50, min_h=50, min_solidity=0.5):
    # Sayfayı OpenCV ile analiz için piksellere döküyoruz
    pix = page.get_pixmap(dpi=dpi, alpha=True)
    img_data = np.frombuffer(pix.tobytes("png"), np.uint8)
    img = cv2.imdecode(img_data, cv2.IMREAD_UNCHANGED)
    if img is None: return []

    alpha = img[:, :, 3]
    kernel = np.ones((5,5), np.uint8)
    thresh = cv2.threshold(alpha, 1, 255, cv2.THRESH_BINARY)[1]
    # Parçaları birleştirip gürültüyü temizliyoruz
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bboxes = []
    scale = 72 / dpi
    page_rect = page.rect # Sayfa sınırları

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        rect = fitz.Rect(x * scale, y * scale, (x + w) * scale, (y + h) * scale)

        # FİLTRE 1: Sayfa Çerçevesi (Hayalet Kutu) Engelleme
        if rect.width > page_rect.width * 0.9 or rect.height > page_rect.height * 0.9:
            continue

        # FİLTRE 2: Solidity (Doluluk Oranı) - Yazıları ve okları eler
        area_pixel = cv2.contourArea(cnt)
        solidity = float(area_pixel) / (w * h) if (w * h) > 0 else 0

        pt_w, pt_h = w * scale, h * scale
        pt_area = (pt_w * pt_h)

        if pt_area > min_area and pt_w > min_w and pt_h > min_h:
            if solidity > min_solidity:
                bboxes.append(rect)

    bboxes.sort(key=lambda r: (r.y0, r.x0))
    return bboxes

# ==========================================
# 2. CONFIG & API HELPERS
# ==========================================
BACKEND_URL = "https://sesa-grafik-api-1003931228830.europe-southwest1.run.app"

def api_build_pdf(gcs_uri, page_index, bbox_pt, quant=3):
    data = {
        "mode": "build_pdf",
        "gcs_uri": gcs_uri,
        "page_index": str(int(page_index)),
        "bbox_pt": ",".join([str(float(x)) for x in bbox_pt]),
        "quant": str(int(quant)),
        "target_stroke": "1.0,0.0,0.0", # Kırmızı
        "target_width": "2.0"
    }
    url = f"{BACKEND_URL.rstrip('/')}/on_repro"
    r = requests.post(url, data=data, timeout=300)
    r.raise_for_status()
    return r.content

# ==========================================
# 3. STREAMLIT UI & LOGIC
# ==========================================
st.set_page_config(page_title="DieLine Tool v2", layout="wide")
st.title("🛡️ Akıllı Ambalaj Seçici & Repro Analizi")

uploaded = st.file_uploader("PDF yükle", type=["pdf"])

if uploaded:
    pdf_bytes = uploaded.getvalue()
    pdf_key = f"{uploaded.name}_{uploaded.size}"

    # GCS Upload Mantığı (Senin orijinal kodun)
    if st.session_state.get("last_uploaded_to_gcs") != pdf_key:
        try:
            gcs_uri = upload_pdf_to_gcs(io.BytesIO(pdf_bytes), "sesa-grafik-bucket")
            st.session_state["gcs_uri"] = gcs_uri
            st.session_state["last_uploaded_to_gcs"] = pdf_key
            st.success("Dosya GCS'ye yüklendi ✅")
        except Exception as e:
            st.error(f"GCS Hatası: {e}")
            st.stop()

    left, right = st.columns([1, 2])

    with left:
        st.subheader("⚙️ Ayarlar")
        page_idx = st.number_input("Sayfa Index", min_value=0, value=0)

        st.markdown("---")
        st.markdown("### 🎯 Kutu Filtreleri")
        m_area = st.slider("Min. Alan (pt²)", 500, 50000, 8000, help="Küçük parçaları eler.")
        m_solidity = st.slider("Min. Doluluk (Solidity)", 0.0, 1.0, 0.6, help="Yazıları ve okları eler.")

        if st.button("Sayfayı Analiz Et", use_container_width=True):
            st.session_state["run_analysis"] = True

    with right:
        if st.session_state.get("run_analysis"):
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc[page_idx]

            # Hayalet kutulardan arındırılmış parçaları buluyoruz
            boxes = get_filtered_bboxes(page, min_area=m_area, min_solidity=m_solidity)

            if not boxes:
                st.warning("Bu ayarlarla parça bulunamadı. Filtreleri gevşetin.")
            else:
                st.subheader(f"📄 Sayfa {page_idx} - Bulunan Parçalar")

                # Sayfa önizlemesi
                st.image(page.get_pixmap(dpi=100).tobytes("png"), caption="Tam Sayfa Görünümü")

                st.write("### 🔎 İşlenecek Parçayı Onayla")
                cols = st.columns(2)
                selected_box = None

                for i, box in enumerate(boxes):
                    with cols[i % 2]:
                        # Özel 0.3 zoom ayarın
                        pix_crop = page.get_pixmap(matrix=fitz.Matrix(0.3, 0.3), clip=box)
                        st.image(pix_crop.tobytes("png"), caption=f"Parça {i}")

                        if st.checkbox(f"Bu parçayı seç (ID: {i})", key=f"cb_{i}"):
                            selected_box = box

                if selected_box:
                    st.divider()
                    st.success(f"Seçim Yapıldı: {selected_box.width*0.3527:.1f} x {selected_box.height*0.3527:.1f} mm")

                    if st.button("🚀 Seçili Parçayı Backend'de İşle", use_container_width=True):
                        with st.spinner("Backend PDF oluşturuyor..."):
                            try:
                                bbox_list = [selected_box.x0, selected_box.y0, selected_box.x1, selected_box.y1]
                                final_pdf = api_build_pdf(
                                    gcs_uri=st.session_state["gcs_uri"],
                                    page_index=page_idx,
                                    bbox_pt=bbox_list
                                )
                                st.session_state["pdf_labeled"] = final_pdf
                                st.balloons()
                            except Exception as e:
                                st.error(f"Backend Hatası: {e}")

                if "pdf_labeled" in st.session_state:
                    st.download_button(
                        "📥 İşaretlenmiş PDF'i İndir",
                        data=st.session_state["pdf_labeled"],
                        file_name="repro_analiz_sonuc.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            doc.close()
