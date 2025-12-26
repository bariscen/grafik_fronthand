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
    "70 x 20 D001" : "D001",
    "85 x 20 D002" : "D002",
    "100 x 30 D003" : "D003",
    "110 x 30 D004" : "D004",
    "112 x 35 D005" : "D005",
    "112 x 45 D006" : "D006",
    "120 x 38 D007" : "D007",
    "125,33 x 25 D008" : "D008",
    "125,33 x 47 D009" : "D009",
    "131,19 x 45 D010" : "D010",
    "140 x 40 D011" : "D011",
    "150 x 45 D012" : "D012",
    "150 x 45 D013" : "D013",
    "152 x 35 D014" : "D014",
    "157 x 39 D015" : "D015",
    "159 x 50 D016" : "D016",
    "159 x 42 D017" : "D017",
    "165 x 45 D018" : "D018",
    "170 x 50 D019" : "D019",
    "175 x 48 D020" : "D020",
    "190 x 50 D021" : "D021",
    "190 x 50 D022" : "D022",
    "200 x 32,5 D023" : "D023",
    "200 x 60 D024" : "D024",
    "200 x 40 D025" : "D025",
    "195,6 x 45 D026" : "D026",
    "210 x 55 D027" : "D027",
    "220 x 45 D028" : "D028",
    "224,5 x 24 D029" : "D029",
    "240 x 57 D031" : "D031",
    "435 x 75 D032" : "D032",
    "0 x 55 D033" : "D033",
    "0 x 80 D034" : "D034",
    "0 x 35 D035" : "D035",
    "89,7 x 30 D038" : "D038",
    "100 x 35 D039" : "D039",
    "110 x 30 D040" : "D040",
    "120 x 32 D041" : "D041",
    "130 x 40 D042" : "D042",
    "140 x 40 D043" : "D043",
    "150 x 40 D044" : "D044",
    "150 x 22,5 D045" : "D045",
    "160 x 44 D047" : "D047",
    "165 x 45 D048" : "D048",
    "170 x 57 D049" : "D049",
    "175 x 50 D050" : "D050",
    "190 x 55 D051" : "D051",
    "200 x 45 D052" : "D052",
    "200 x 50 D053" : "D053",
    "217 x 55 D054" : "D054",
    "220 x 52 D055" : "D055",
    "230 x 50 D056" : "D056",
    "250 x 55 D058" : "D058",
    "267 x 50 D059" : "D059",
    "329 x 60 D060" : "D060",
    "110 x 35 D062" : "D062",
    "160 x 45 D063" : "D063",
    "175 x 24 D064" : "D064",
    "180 x 50 D065" : "D065",
    "180 x 45 D066" : "D066",
    "192 x 40 D068" : "D068",
    "170 x 48 D069" : "D069",
    "159,66 x 44 D070" : "D070",
    "264,5 x 45 D071" : "D071",
    "190 x 25 D073" : "D073",
    "130 x 35 D074" : "D074",
    "274,5 x 50 D075" : "D075",
    "311 x 50 D076" : "D076",
    "238 x 38 D077" : "D077",
    "85 x 25 D079" : "D079",
    "180 x 55 D080" : "D080",
    "100 x 26 D081" : "D081",
    "140 x 36 D082" : "D082",
    "235 x 38 D083" : "D083",
    "250 x 65 D086" : "D086",
    "210 x 55 D089" : "D089",
    "215 x 45 D090" : "D090",
    "150 x 30 D091" : "D091",
    "93 x 21 D093" : "D093",
    "165 x 20 D094" : "D094",
    "185 x 40 D095" : "D095",
    "220 x 60 D097" : "D097",
    "220 x 70 D099" : "D099",
    "140 x 40 D100" : "D100",
    "220 x 30 D101" : "D101",
    "320 x 30 D102" : "D102",
    "200 x 40 D104" : "D104",
    "130 x 30 D105" : "D105",
    "140 x 30 D106" : "D106",
    "150 x 50 D107" : "D107",
    "100 x 32 D108" : "D108",
    "120 x 25 D109" : "D109",
    "135 x 30 D110" : "D110",
    "145 x 40 D111" : "D111",
    "157 x 40 D112" : "D112",
    "160 x 30 D113" : "D113",
    "320 x 50 D115" : "D115",
    "300 x 70 D116" : "D116",
    "320 x 65 D117" : "D117",
    "1 x 1 D120" : "D120",
    "140 x 43 D121" : "D121",
    "204 x 76,5 D122" : "D122",
    "204 x 55 D123" : "D123",
    "140 x 55 D124" : "D124",
    "319 x 30 D127" : "D127",
    "374 x 55 D128" : "D128",
    "319 x 60 D129" : "D129",
    "152 x 42 D130" : "D130",
    "140 x 25,5 D131" : "D131",
    "204 x 38 D132" : "D132",
    "120 x 30 D133" : "D133",
    "400 x 60 D134" : "D134",
    "95 x 15 D135" : "D135",
    "162 x 42 D136" : "D136",
    "171,5 x 42 D137" : "D137",
    "200 x 30 D138" : "D138",
    "163 x 45 D139" : "D139",
    "152 x 42 D140" : "D140",
    "145 x 30 D141" : "D141",
    "140 x 40 D142" : "D142",
    "150 x 22,5 D143" : "D143",
    "380 x 90 D144" : "D144",
    "245 x 55 D145" : "D145",
    "240 x 60 D146" : "D146",
    "238 x 45 D147" : "D147",
    "110 x 25 D148" : "D148",
    "460 x 80 D149" : "D149",
    "150 x 42 D152" : "D152",
    "180 x 50 D153" : "D153",
    "95 x 30 D154" : "D154",
    "440 x 75 D155" : "D155",
    "420 x 70 D156" : "D156",
    "310 x 62,5 D157" : "D157",
    "205 x 60 D158" : "D158",
    "190 x 50 D159" : "D159",
    "200 x 60 D160" : "D160",
    "240 x 70 D161" : "D161",
    "160 x 26 D162" : "D162",
    "220 x 26 D163" : "D163",
    "130 x 32 D164" : "D164",
    "95 x 25 D165" : "D165",
    "150 x 42 D166" : "D166",
    "159 x 38 D167" : "D167",
    "80 x 26 D168" : "D168",
    "235 x 50 D169" : "D169",
    "255 x 50 D170" : "D170",
    "127 x 25 D171" : "D171",
    "300 x 75 D172" : "D172",
    "0 x 0 D173" : "D173",
    "0 x 0 D174" : "D174",
    "150 x 35 D175" : "D175",
    "195 x 50 D176" : "D176",
    "235 x 60 D177" : "D177",
    "165 x 30 D178" : "D178",
    "171 x 39 D179" : "D179",
    "150 x 25 D180" : "D180",
    "240 x 70 D181" : "D181",
    "152 x 35 D182" : "D182",
    "186 x 45 D183" : "D183",
    "247 x 46 D184" : "D184",
    "165 x 50 D185" : "D185",
    "174 x 45 D186" : "D186",
    "175 x 45 D187" : "D187",
    "231 x 45 D188" : "D188",
    "205 x 50 D189" : "D189",
    "171 x 43 D191" : "D191",
    "140 x 44 D192" : "D192",
    "154 x 35 D193" : "D193",
    "170 x 38 D194" : "D194",
    "133 x 40 D195" : "D195",
    "155 x 35 D196" : "D196",
    "240 x 65 D197" : "D197",
    "248 x 67 D198" : "D198",
    "130 x 45 D199" : "D199",
    "110 x 35 D200" : "D200",
    "150 x 40 D201" : "D201",
    "170 x 45 D202" : "D202",
    "85 x 25 D203" : "D203",
    "178 x 45 D204" : "D204",
    "93 x 27,5 D205" : "D205",
    "152 x 44,5 D206" : "D206",
    "120 x 32 D207" : "D207",
    "180 x 30 D208" : "D208",
    "102 x 32 D209" : "D209",
    "95 x 20 D212" : "D212",
    "160 x 45 D213" : "D213",
    "371 x 80 D214" : "D214",
    "153 x 30 D215" : "D215",
    "86 x 30 D216" : "D216",
    "140 x 40 D217" : "D217",
    "150 x 45 D218" : "D218",
    "128,5 x 30 D219" : "D219",
    "152 x 35 D220" : "D220",
    "120 x 35 D221" : "D221",
    "250 x 65 D222" : "D222",
    "224 x 52 D223" : "D223",
    "216 x 38 D224" : "D224",
    "140 x 40 D225" : "D225",
    "140 x 40 D226" : "D226",
    "79 x 35 D227" : "D227",
    "95 x 25 D228" : "D228",
    "195,6 x 60 D229" : "D229",
    "160 x 44 D230" : "D230",
    "125 x 48 D231" : "D231",
    "235 x 57 D232" : "D232",
    "171 x 51 D233" : "D233",
    "178 x 38 D234" : "D234",
    "127 x 42 D235" : "D235",
    "235 x 51 D236" : "D236",
    "153 x 50 D237" : "D237",
    "140 x 40 D238" : "D238",
    "184 x 38 D239" : "D239",
    "125 x 48 D240" : "D240",
    "143 x 40 D241" : "D241",
    "178 x 47,5 D242" : "D242",
    "155 x 40 D243" : "D243",
    "175 x 40 D244" : "D244",
    "170 x 38 D245" : "D245",
    "250 x 44,5 D246" : "D246",
    "200 x 45 D247" : "D247",
    "185 x 42,5 D248" : "D248",
    "260 x 50 D249" : "D249",
    "170 x 25 D250" : "D250",
    "200 x 50 D251" : "D251",
    "210 x 60 D253" : "D253",
    "216 x 41 D254" : "D254",
    "135 x 40 D255" : "D255",
    "127 x 25 D256" : "D256",
    "203 x 45 D257" : "D257",
    "235 x 65 D258" : "D258",
    "320 x 80 D259" : "D259",
    "240 x 50 D260" : "D260",
    "113 x 32 D261" : "D261",
    "140 x 43 D262" : "D262",
    "165 x 45 D263" : "D263",
    "85 x 20 D264" : "D264",
    "424 x 80 D265" : "D265",
    "160 x 50 D266" : "D266",
    "180 x 35 D267" : "D267",
    "150 x 48 D268" : "D268",
    "400 x 80 D269" : "D269",
    "119 x 35 D270" : "D270",
    "230 x 60 D271" : "D271",
    "300 x 50 D272" : "D272",
    "125 x 40 D273" : "D273",
    "145 x 30 D274" : "D274",
    "178 x 32 D275" : "D275",
    "140 x 25 D276" : "D276",
    "95 x 27,5 D277" : "D277",
    "95 x 30 D278" : "D278",
    "145 x 40 D279" : "D279",
    "100 x 30 D280" : "D280",
    "220 x 45 D281" : "D281",
    "183 x 50 D282" : "D282",
    "210 x 50 D283" : "D283",
    "285 x 60 D285" : "D285",
    "142 x 25 D286" : "D286",
    "115 x 30 D287" : "D287",
    "181 x 32 D288" : "D288",
    "160 x 40 D289" : "D289",
    "154 x 35 D290" : "D290",
    "300 x 80 D291" : "D291",
    "164 x 38 D292" : "D292",
    "127 x 38 D293" : "D293",
    "180 x 38 D294" : "D294",
    "250 x 40 D295" : "D295",
    "240 x 33 D296" : "D296",
    "120 x 30 D297" : "D297",
    "84 x 25 D298" : "D298",
    "133 x 35 D299" : "D299",
    "300 x 60 D300" : "D300",
    "132 x 40 D301" : "D301",
    "110 x 32 D302" : "D302",
    "300 x 80 D303" : "D303",
    "140 x 30 D304" : "D304",
    "190 x 60 D305" : "D305",
    "220 x 50 D306" : "D306",
    "160 x 55 D307" : "D307",
    "180 x 23 D308" : "D308",
    "160 x 30 D309" : "D309",
    "210 x 60 D310" : "D310",
    "125 x 35 D311" : "D311",
    "250 x 45 D312" : "D312",
    "180 x 23 D313" : "D313",
    "143 x 0 D314" : "D314",
    "85 x 27,5 D315" : "D315",
    "425 x 84 D316" : "D316",
    "190 x 40 D317" : "D317",
    "280 x 51 D318" : "D318",
    "143 x 0 D319" : "D319",
    "200 x 0 D320" : "D320",
    "180 x 50 D321" : "D321",
    "195 x 50 D322" : "D322",
    "159 x 32,5 D323" : "D323",
    "195 x 32,5 D324" : "D324",
    "110 x 32 D325" : "D325",
    "117 x 38 D326" : "D326",
    "115 x 35 D327" : "D327",
    "116 x 35 D328" : "D328",
    "183 x 30 D329" : "D329",
    "240 x 65 D330" : "D330",
    "260 x 70 D331" : "D331",
    "150 x 37 D332" : "D332",
    "143 x 25 D333" : "D333",
    "143 x 25 D334" : "D334",
    "154 x 37,5 D335" : "D335",
    "173 x 50 D336" : "D336",
    "170 x 50 D337" : "D337",
    "200 x 0 D338" : "D338",
    "170 x 30 D339" : "D339",
    "165 x 41 D340" : "D340",
    "130 x 35 D341" : "D341",
    "165 x 40 D342" : "D342",
    "250 x 50 D343" : "D343",
    "215 x 27,5 D344" : "D344",
    "215 x 27,5 D345" : "D345",
    "190 x 37,5 D346" : "D346",
    "140 x 26 D347" : "D347",
    "95 x 31 D348" : "D348",
    "160 x 35 D349" : "D349",
    "140 x 35 D350" : "D350",
    "98 x 31 D351" : "D351",
    "210 x 45 D352" : "D352",
    "125 x 20 D353" : "D353",
    "235 x 44,5 D354" : "D354",
    "170 x 44 D355" : "D355",
    "122 x 32 D356" : "D356",
    "100 x 30 D357" : "D357",
    "241 x 51 D358" : "D358",
    "110 x 28 D359" : "D359",
    "205 x 60 D360" : "D360",
    "205 x 60 D361" : "D361",
    "225 x 60 D362" : "D362",
    "150 x 55 D363" : "D363",
    "170 x 45 D364" : "D364",
    "120 x 40 D365" : "D365",
    "240 x 40 D366" : "D366",
    "195 x 40 D367" : "D367",
    "130 x 28 D368" : "D368",
    "154 x 42 D369" : "D369",
    "85 x 30 D370" : "D370",
    "155 x 45 D372" : "D372",
    "137 x 26 D373" : "D373",
    "130 x 40 D374" : "D374",
    "95 x 24 D375" : "D375",
    "145 x 45 D376" : "D376",
    "390 x 70 D377" : "D377",
    "180 x 40 D378" : "D378",
    "156 x 38 D379" : "D379",
    "164 x 40 D380" : "D380",
    "128 x 30 D381" : "D381",
    "127 x 32 D382" : "D382",
    "220 x 45 D383" : "D383",
    "165 x 55 D384" : "D384",
    "93 x 30 D385" : "D385",
    "203 x 38 D386" : "D386",
    "210 x 40 D388" : "D388",
    "170 x 55 D389" : "D389",
    "230 x 50 D390" : "D390",
    "225 x 40 D391" : "D391",
    "230 x 40 D392" : "D392",
    "203 x 38 D393" : "D393",
    "160 x 40 D394" : "D394",
    "175 x 45 D395" : "D395",
    "190 x 45 D396" : "D396",
    "206 x 38 D397" : "D397",
    "200 x 42,5 D398" : "D398",
    "300 x 51 D399" : "D399",
    "0 x 0 D400" : "D400",
    "107 x 32 D401" : "D401",
    "95 x 31 D402" : "D402",
    "116 x 40 D403" : "D403",
    "164 x 50 D404" : "D404",
    "210 x 55 D405" : "D405",
    "229 x 64 D406" : "D406",
    "180 x 45 D407" : "D407",
    "100 x 30 D408" : "D408",
    "300 x 45 D409" : "D409",
    "128 x 35 D410" : "D410",
    "220 x 55 D411" : "D411",
    "272 x 47 D412" : "D412",
    "260 x 50 D413" : "D413",
    "350 x 50 D414" : "D414",
    "143 x 30 D415" : "D415",
    "217 x 45 D416" : "D416",

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
dikis_kalinlik = st.number_input("Dikiş Kalınlığı (mm)", min_value=0.0, value=7.5, step=1.0)

st.markdown("---")
st.subheader("Gelişmiş Ayarlar (opsiyonel)")

with st.expander("Gelişmiş ayarları aç"):

    margin = 25
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
    lazer = False
    if ac_kapa == "Var":
        ac_kapa_yer = st.number_input(
            "Çentik Yeri (mm)",
            min_value=0.0,
            value=20.0,
            step=1.0,
        )
        lazer = st.selectbox("Lazer Var mı", ["Yok", "Var"])

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
        "lazer": lazer == "Var",

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
