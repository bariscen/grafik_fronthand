from __future__ import annotations

import os
import math
from pathlib import Path
from typing import Union, Optional

import fitz  # PyMuPDF
from shapely.geometry import LineString, box, MultiPolygon
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
        paths = src_page.get_drawings()

        # --- ARAMA HİYERARŞİSİ ---
        # 1. Orijinal Kural
        bicak_izleri = [p for p in paths if p.get("width") is not None and abs(p["width"] - hedef_kalinlik) <= 0.1 and p["rect"].y1 < (page_height / 2)]

        # 2. Tüm Sayfa 2.83
        if not bicak_izleri:
            bicak_izleri = [p for p in paths if p.get("width") is not None and abs(p["width"] - hedef_kalinlik) <= 0.1]

        # 3. SENİN İSTEDİĞİN MANTIK: 0.50mm - 0.60mm arası çizgiler
        if not bicak_izleri:
            # 0.50mm yaklaşık 1.41 point, 0.60mm yaklaşık 1.70 pointtir.
            bicak_izleri = [p for p in paths if p.get("width") is not None and 1.3 <= p["width"] <= 1.8]

        # 4. Derin Arama (Son Çare)
        if not bicak_izleri:
            bicak_izleri = [p for p in paths if p["rect"].width > 50 or p["rect"].height > 50]

        if not bicak_izleri:
            raise ValueError(f"Bıçak izi bulunamadı.")

        # Bounding Box
        try:
            union_rect = fitz.Rect(bicak_izleri[0]["rect"])
            for p in bicak_izleri[1:]: union_rect |= p["rect"]
            final_rect = union_rect
        except:
            final_rect = src_page.rect

        new_doc = fitz.open()
        try:
            new_page = new_doc.new_page(width=final_rect.width + 2, height=final_rect.height + 2)
            offset = final_rect.tl - fitz.Point(1, 1)

            all_lines = []
            for p in bicak_izleri:
                for item in p["items"]:
                    if item[0] == "l":
                        a, b = item[1] - offset, item[2] - offset
                        all_lines.append(LineString([(a.x, a.y), (b.x, b.y)]))
                    elif item[0] == "c":
                        p0, p1, p2, p3 = [v - offset for v in item[1:5]]
                        all_lines.append(LineString(bezier_points(p0, p1, p2, p3, n=int(bezier_adim))))

            merged = unary_union(all_lines)

            # --- YENİ GEOMETRİ MANTIĞI: TÜM POLİGONLARI TARAMA ---
            # Sadece en büyüğü değil, tüm kapalı alanları (üçgenler dahil) buluyoruz.
            # Uçları açık çizgileri birleştirmek için buffer uyguluyoruz.
            refined_geom = merged.buffer(1.5).buffer(-1.4)

            polys = []
            if refined_geom.geom_type == 'Polygon':
                polys = [refined_geom]
            elif refined_geom.geom_type == 'MultiPolygon':
                polys = list(refined_geom.geoms)
            elif hasattr(refined_geom, 'geoms'): # GeometryCollection durumu
                polys = [g for g in refined_geom.geoms if g.geom_type == 'Polygon']

            if not polys:
                # Poligon oluşmadıysa polygonize dene
                polys = list(polygonize(merged))

            if not polys:
                # Hala yoksa mecbur bounding box
                polys = [box(*merged.bounds)]

            # Tarama Alanı: Tüm poligonların birleşimi (Dış hat + İç üçgenler)
            final_poly = unary_union(polys).buffer(float(buffer_eps))

            # Çizim (Dış Hatlar)
            shape_outline = new_page.new_shape()
            def draw_poly_outline(geom):
                if geom.geom_type == 'Polygon':
                    coords = list(geom.exterior.coords)
                    for i in range(len(coords)-1):
                        shape_outline.draw_line(fitz.Point(*coords[i]), fitz.Point(*coords[i+1]))
                    for interior in geom.interiors:
                        coords = list(interior.coords)
                        for i in range(len(coords)-1):
                            shape_outline.draw_line(fitz.Point(*coords[i]), fitz.Point(*coords[i+1]))
                elif hasattr(geom, 'geoms'):
                    for g in geom.geoms: draw_poly_outline(g)

            draw_poly_outline(final_poly)
            shape_outline.finish(color=(0, 0, 0), width=hedef_kalinlik)
            shape_outline.commit()

            # Tarama (Hatching)
            shape_hatch = new_page.new_shape()
            diag = math.sqrt(new_page.rect.width**2 + new_page.rect.height**2)
            angle_rad = math.radians(angle_deg)
            dx, dy = math.cos(angle_rad), math.sin(angle_rad)
            nx, ny = -dy, dx

            step = int(tarama_araligi)
            for i in range(-int(diag), int(diag), step):
                cx, cy = nx * i + new_page.rect.width/2, ny * i + new_page.rect.height/2
                line = LineString([(cx - dx * diag, cy - dy * diag), (cx + dx * diag, cy + dy * diag)])

                try:
                    inter = final_poly.intersection(line)
                    if inter.is_empty: continue

                    def draw_it(geom):
                        if geom.geom_type == "LineString":
                            pts = list(geom.coords)
                            shape_hatch.draw_line(fitz.Point(*pts[0]), fitz.Point(*pts[-1]))
                        elif hasattr(geom, 'geoms'):
                            for g in geom.geoms: draw_it(g)

                    draw_it(inter)
                except:
                    continue

            shape_hatch.finish(color=(0, 0, 0), width=0.7)
            shape_hatch.commit()
            new_doc.save(str(cikti_adi))
        finally:
            new_doc.close()
    finally:
        doc.close()

    return cikti_adi
