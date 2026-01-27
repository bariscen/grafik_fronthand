import streamlit as st
from pathlib import Path

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

# Bu dosyanın bulunduğu dizin (örneğin: pages/page1.py)
current_dir = Path(__file__).parent.parent

# row-data yolunu oluştur
image_path_for_logo = current_dir.parent / "row-data" / "sesa-logo-80-new.png"

# Logonun her sayfada gösterilmesi için session_state'e kaydet
if 'logo_image_path' not in st.session_state:
    if image_path_for_logo.exists():
        st.session_state.logo_image_path = str(image_path_for_logo)
    else:
        st.session_state.logo_image_path = None

# Logoyu göster
if st.session_state.logo_image_path:
    try:
        st.image(st.session_state.logo_image_path, width=200)
    except:
        st.warning("Logo yüklenemedi.")
else:
    st.warning("Logo dosyası bulunamadı.")

# Sayfa arka planını ayarla
st.markdown("""
    <style>
    .stApp {
        background-color: #d3d3d3;
    }
    </style>
    """, unsafe_allow_html=True)

# Buton stilini ayarla
st.markdown("""
<style>
div.stButton > button {
    font-size: 24px;
    padding: 20px 0; /* Butonların içine dikey boşluk ekler */
    border-radius: 10px;
    background-color: #FFBF00;
    color: black;
    border: 2px solid #444;
    margin: 5px;

    /* Butonların sabit genişliği ve yüksekliği */
    width: 250px; /* İstediğiniz genişliği buraya yazabilirsiniz */
    height: 80px; /* Buton yüksekliğini sabitleyebiliriz */

    /* Metnin ortalanması */
    display: flex;
    justify-content: center;
    align-items: center;
}
</style>
""", unsafe_allow_html=True)

# --- 2 Buton Üstte ---
# --- 3 Buton Üstte ---
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🎚️ Ön Kontrol"):
        st.switch_page("pages/on_repro.py")

with col2:
    if st.button("✒️ Bıçak Çizimi"):
        st.switch_page("pages/die-line.py")

with col3:
    if st.button("💫"):
        st.switch_page("pages/new_on_repo.py")



# # --- 3 Buton Altta ---
# col4, col5, col6 = st.columns(3)

# with col4:
#     if st.button("📊 İstatistikler"):
#         st.switch_page("pages/stats.py")

# with col5:
#     if st.button("✍🏼 Geçen Sene Sipariş Vermeyenler"):
#         st.switch_page("pages/gecen_sene.py")

# with col6:
#     if st.button("🏭 Sektörel Değişimler"):
#         st.switch_page("pages/sektor.py")

# # Son butonu ortalamak için
# col_sol, col_orta, col_sag = st.columns([1, 1, 1])

# with col_sol:
#     if st.button("🧭 Müşteri Temsilcisi"):
#         st.switch_page("pages/temsilci.py")


# with col_orta:
#     if st.button("🏅 Müşteri Başarı Durumu"):
#         st.switch_page("pages/basari.py")



st.markdown("""
<style>
div.stButton > button {
    font-size: 24px;
    padding: 20px 0; /* Butonun içindeki dikey boşluk */
    border-radius: 10px;
    background-color: #FFBF00;
    color: black;
    border: 2px solid #444;

    /* Butonlar arasındaki boşluğu artırın */
    margin: 15px;

    width: 220px;
    height: 80px;

    display: flex;
    justify-content: center;
    align-items: center;
}
</style>
""", unsafe_allow_html=True)

# Özel stil için butonu container içine al ve sınıfı ver
button_placeholder = st.empty()
with button_placeholder.container():
    # Butonun key parametresi önemli, her butonun unique olmalı
    clicked = st.button("Ana Sayfaya Dön", key="back_to_sales", help="Satış sayfasına dön",
                        args=None, kwargs=None)
    # Yukarıdaki button normal görünüyor, şimdi butona CSS sınıfını JavaScript ile ekleyelim
    # Çünkü Streamlit doğrudan class parametre almıyor

    st.markdown("""
    <script>
    const btn = window.parent.document.querySelector('button[kind="primary"][data-testid^="stButton"][aria-label="Satış Menüsüne Dön"]');
    if(btn){
        btn.classList.add("fixed-button");
    }
    </script>
    """, unsafe_allow_html=True)

if clicked:
    st.switch_page("enterance.py")
