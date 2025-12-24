from __future__ import annotations

import os
import math
from pathlib import Path
from typing import Union, Optional

import fitz  # PyMuPDF
from shapely.geometry import LineString, box
from shapely.ops import unary_union, polygonize


def bezier_points(p0, p1, p2, p3, n: int = 20):
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = (mt**3) * p0.x + 3 * (mt**2) * t * p1.x + 3 * mt * (t**2) * p2.x + (t**3) * p3.x
        y = (mt**3) * p0.y + 3 * (mt**2) * t * p1.y + 3 * mt * (t**2) * p2.y + (t**3) * p3.y
        pts.append((x, y))
    return pts


def process_pdf(
    dosya_adi: Union[str, Path],
    hedef_kalinlik: float = 2.83,
    tarama_araligi: int = 6,
    bezier_adim: int = 20,
    buffer_eps: float = 0.01,
    tarama_acisi_derece: float = 45.0,
    yon: int = 1,
    output_dir: Optional[Union[str, Path]] = None,
) -> Path:
    dosya_adi = Path(dosya_adi)
    angle_deg = float(tarama_acisi_derece)
    base = dosya_adi.stem
    out_dir = Path(output_dir) if output_dir else dosya_adi.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    cikti_adi = out_dir / f"{base}-{yon}.pdf"

    doc = fitz.open(str(dosya_adi))
    try:
        src_page = doc[0]
        page_height = src_page.rect.height
        page_width = src_page.rect.width
        paths = src_page.get_drawings()

        # --- BIÇAK İZİ SEÇİM MANTIĞI ---

        # 1. Aşama: Orijinal senin kuralın (2.83 + Üst Yarı)
        bicak_izleri = [
            p for p in paths
            if p.get("width") is not None
            and abs(p["width"] - hedef_kalinlik) <= 0.1
            and p["rect"].y1 < (page_height / 2)
        ]

        # 2. Aşama: Senin kuralın (Tüm Sayfa)
        if not bicak_izleri:
            bicak_izleri = [
                p for p in paths
                if p.get("width") is not None
                and abs(p["width"] - hedef_kalinlik) <= 0.1
            ]

        # 3. Aşama: GEOMETRİK ANALİZ (Rakamları Eleyip Bıçağı Bulma)
        if not bicak_izleri:
            adaylar = []
            for p in paths:
                r = p["rect"]
                # Sayıları elemek için: Rakamlar genelde dardır veya çok küçüktür.
                # Bıçak izi ise sayfanın en az %30'u kadar genişlik kaplamalıdır.
                if r.width > (page_width * 0.3) or r.height > (page_height * 0.3):
                    # İçinde çizgi veya eğri olanları al
                    if any(item[0] in ("l", "c") for item in p.get("items", [])):
                        adaylar.append(p)

            if adaylar:
                # En geniş alanı kaplayan çizim muhtemelen bıçak izidir
                bicak_izleri = [max(adaylar, key=lambda p: p["rect"].width * p["rect"].height)]

        # 4. Aşama: Son Çare (En çok parçalı büyük obje)
        if not bicak_izleri:
            buyuk_objeler = [p for p in paths if p["rect"].width > 100]
            if buyuk_objeler:
                bicak_izleri = [max(buyuk_objeler, key=lambda p: len(p.get("items", [])))]

        if not bicak_izleri:
            raise ValueError(f"Bıçak izi tespit edilemedi. Lütfen PDF içeriğini kontrol edin.")

        # Margin neredeyse yok dediğin için alanı genişletmiyoruz
        final_rect = fitz.Rect(bicak_izleri[0]["rect"])
        for p in bicak_izleri[1:]:
            final_rect |= p["rect"]

        new_doc = fitz.open()
        try:
            # Margin yoksa çok az (1-2 px) pay bırakmak Shapely'nin hata yapmasını önler
            new_page = new_doc.new_page(width=final_rect.width + 2, height=final_rect.height + 2)
            offset = final_rect.tl - fitz.Point(1, 1)

            all_lines = []
            shape_outline = new_page.new_shape()
            for p in bicak_izleri:
                for item in p["items"]:
                    if item[0] == "l":
                        a, b = item[1] - offset, item[2] - offset
                        shape_outline.draw_line(a, b)
                        all_lines.append(LineString([(a.x, a.y), (b.x, b.y)]))
                    elif item[0] == "c":
                        p0, p1, p2, p3 = [v - offset for v in item[1:5]]
                        shape_outline.draw_bezier(p0, p1, p2, p3)
                        pts = bezier_points(p0, p1, p2, p3, n=int(bezier_adim))
                        all_lines.append(LineString(pts))

            shape_outline.finish(color=(0, 0, 0), width=hedef_kalinlik)
            shape_outline.commit()

            # Poligonlaştırma ve Tarama
            merged = unary_union(all_lines)
            polys = list(polygonize(merged))

            if not polys:
                # Görsellerdeki ince çizgileri birleştirmek için daha agresif buffer
                refined = merged.buffer(1.5).buffer(-1.4)
                if refined.geom_type == 'Polygon':
                    polys = [refined]
                elif hasattr(refined, 'geoms'):
                    polys = [g for g in refined.geoms if g.geom_type == 'Polygon']

            if not polys:
                # Hiç poligon oluşmazsa bounding box'ı kullan (B planı)
                polys = [box(*merged.bounds)]

            outer = max(polys, key=lambda p: p.area)
            poly = outer.buffer(float(buffer_eps))

            # Hatching (Tarama)
            shape_hatch = new_page.new_shape()
            diag = math.sqrt(new_page.rect.width**2 + new_page.rect.height**2)
            angle_rad = math.radians(angle_deg)
            dx, dy = math.cos(angle_rad), math.sin(angle_rad)
            nx, ny = -dy, dx

            step = int(tarama_araligi)
            for i in range(-int(diag), int(diag), step):
                cx, cy = nx * i + new_page.rect.width/2, ny * i + new_page.rect.height/2
                line = LineString([(cx - dx * diag, cy - dy * diag), (cx + dx * diag, cy + dy * diag)])
                inter = poly.intersection(line)

                if inter.is_empty: continue

                def draw_it(geom):
                    if geom.geom_type == "LineString":
                        coords = list(geom.coords)
                        shape_hatch.draw_line(fitz.Point(*coords[0]), fitz.Point(*coords[-1]))
                    elif hasattr(geom, 'geoms'):
                        for g in geom.geoms: draw_it(g)

                draw_it(inter)

            shape_hatch.finish(color=(0, 0, 0), width=0.7)
            shape_hatch.commit()
            new_doc.save(str(cikti_adi))
        finally:
            new_doc.close()
    finally:
        doc.close()

    return cikti_adi
