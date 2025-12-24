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
        paths = src_page.get_drawings()

        # --- BIÇAK İZİ ARAMA STRATEJİSİ (GÜNCELLENMİŞ) ---

        # 1. Aşama: Orijinal kural (Üst Yarı + 2.83)
        bicak_izleri = [
            p for p in paths
            if p.get("width") is not None
            and abs(p["width"] - hedef_kalinlik) <= 0.1
            and p["rect"].y1 < (page_height / 2)
        ]

        # 2. Aşama: Kısıtlamasız 2.83 (Tüm Sayfa)
        if not bicak_izleri:
            bicak_izleri = [
                p for p in paths
                if p.get("width") is not None
                and abs(p["width"] - hedef_kalinlik) <= 0.1
            ]

        # 3. Aşama: Sayfadaki en kalın çizgiler (Sayıları elemek için alan kontrolü eklendi)
        if not bicak_izleri:
            # Sadece belirli bir genişlikten büyük olanları al (Sayılar genelde küçüktür)
            yollar = [p for p in paths if p.get("width") is not None and p["width"] > 0.3]
            if yollar:
                # Sayıları elemek için: Çizimin kapladığı alan çok küçükse (örn 50px'den az) sayı olabilir.
                yollar = [p for p in yollar if p["rect"].width > 50 or p["rect"].height > 50]
                if yollar:
                    max_w = max(p["width"] for p in yollar)
                    bicak_izleri = [p for p in yollar if abs(p["width"] - max_w) < 0.1]

        # 4. Aşama: DERİN ARAMA (Sayıları eleyerek en uzun yolu seçer)
        if not bicak_izleri:
            if paths:
                # Sayı olabilecek küçük objeleri filtrele, en çok parça içeren büyük objeyi seç
                adaylar = [p for p in paths if p["rect"].width > 40 and p["rect"].height > 40]
                if adaylar:
                    bicak_izleri = [max(adaylar, key=lambda p: len(p.get("items", [])))]
                else:
                    bicak_izleri = [max(paths, key=lambda p: len(p.get("items", [])))]

        if not bicak_izleri:
            raise ValueError(f"Bıçak izi bulunamadı: {dosya_adi.name}")

        # Bounding Box Güvenliği
        try:
            union_rect = fitz.Rect(bicak_izleri[0]["rect"])
            for p in bicak_izleri[1:]:
                union_rect |= p["rect"]
            final_rect = union_rect if not union_rect.is_empty else src_page.rect
        except:
            final_rect = src_page.rect

        new_doc = fitz.open()
        try:
            new_page = new_doc.new_page(width=final_rect.width, height=final_rect.height)
            offset = final_rect.tl

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

            # Geometri Birleştirme
            merged = unary_union(all_lines)
            polys = list(polygonize(merged))

            if not polys:
                refined = merged.buffer(0.5).buffer(-0.4)
                if refined.geom_type == 'Polygon':
                    polys = [refined]
                elif hasattr(refined, 'geoms'):
                    polys = [g for g in refined.geoms if g.geom_type == 'Polygon']

            if not polys:
                raise ValueError(f"Geometri taranabilir değil: {dosya_adi.name}")

            outer = max(polys, key=lambda p: p.area)
            holes = [p for p in polys if p is not outer and p.within(outer)]
            poly = outer.difference(unary_union(holes)) if holes else outer
            poly = poly.buffer(float(buffer_eps))

            # Tarama
            shape_hatch = new_page.new_shape()
            w, h = new_page.rect.width, new_page.rect.height
            diag = math.sqrt(w * w + h * h)
            angle_rad = math.radians(angle_deg)
            dx, dy = math.cos(angle_rad), math.sin(angle_rad)
            L = diag * 2
            nx, ny = -dy, dx

            step = int(tarama_araligi)
            for i in range(-int(diag), int(diag), step):
                cx, cy = nx * i + w / 2, ny * i + h / 2
                line = LineString([(cx - dx * L, cy - dy * L), (cx + dx * L, cy + dy * L)])
                inter = poly.intersection(line)
                if inter.is_empty: continue

                def draw_ls(ls):
                    coords = list(ls.coords)
                    if len(coords) >= 2:
                        shape_hatch.draw_line(fitz.Point(*coords[0]), fitz.Point(*coords[-1]))

                if inter.geom_type == "LineString":
                    draw_ls(inter)
                elif inter.geom_type == "MultiLineString":
                    for ls in inter.geoms: draw_ls(ls)
                elif inter.geom_type == "GeometryCollection":
                    for g in inter.geoms:
                        if g.geom_type == "LineString": draw_ls(g)
                        elif g.geom_type == "MultiLineString":
                            for ls in g.geoms: draw_ls(ls)

            shape_hatch.finish(color=(0, 0, 0), width=0.7)
            shape_hatch.commit()
            new_doc.save(str(cikti_adi))
        finally:
            new_doc.close()
    finally:
        doc.close()

    return cikti_adi
