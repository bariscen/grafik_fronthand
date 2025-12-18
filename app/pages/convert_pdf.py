from __future__ import annotations

import os
import math
from pathlib import Path
from typing import Union, Optional

import fitz  # PyMuPDF
from shapely.geometry import LineString
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
    """
    yon: 1 veya -1 (tarama yönünü terslemek için)
    output_dir: çıktıların kaydedileceği klasör (None ise input ile aynı klasör)
    """
    dosya_adi = Path(dosya_adi)
    if not dosya_adi.exists():
        raise FileNotFoundError(f"PDF bulunamadı: {dosya_adi}")
    if dosya_adi.suffix.lower() != ".pdf":
        raise ValueError(f"PDF değil: {dosya_adi}")

    angle_deg = float(tarama_acisi_derece)  # yon sadece isimlendirme için


    base = dosya_adi.stem
    out_dir = Path(output_dir) if output_dir else dosya_adi.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    cikti_adi = out_dir / f"{base}-{yon}.pdf"

    doc = fitz.open(str(dosya_adi))
    try:
        if doc.page_count < 1:
            raise ValueError(f"Boş PDF: {dosya_adi}")

        src_page = doc[0]
        page_height = src_page.rect.height

        # 1) Bıçak izlerini bul
        paths = src_page.get_drawings()
        bicak_izleri = [
            p for p in paths
            if p.get("width") is not None
            and abs(p["width"] - hedef_kalinlik) <= 0.1
            and p["rect"].y1 < (page_height / 2)
        ]

        if not bicak_izleri:
            raise ValueError(f"Bıçak izi bulunamadı: {dosya_adi}")

        # union rect (MARGIN=0)
        union_rect = bicak_izleri[0]["rect"]
        for p in bicak_izleri[1:]:
            union_rect |= p["rect"]
        final_rect = union_rect

        # 2) Yeni PDF sayfası
        new_doc = fitz.open()
        try:
            new_page = new_doc.new_page(width=final_rect.width, height=final_rect.height)
            offset = final_rect.tl

            # 3) Konturu çiz (siyah kalın)
            shape_outline = new_page.new_shape()
            for p in bicak_izleri:
                for item in p["items"]:
                    if item[0] == "l":
                        a = item[1] - offset
                        b = item[2] - offset
                        shape_outline.draw_line(a, b)
                    elif item[0] == "c":
                        a = item[1] - offset
                        b = item[2] - offset
                        c = item[3] - offset
                        d = item[4] - offset
                        shape_outline.draw_bezier(a, b, c, d)
            shape_outline.finish(color=(0, 0, 0), width=hedef_kalinlik)
            shape_outline.commit()

            # 4) Konturu poligonlara çevir
            all_lines = []
            for p in bicak_izleri:
                for item in p["items"]:
                    if item[0] == "l":
                        a = item[1] - offset
                        b = item[2] - offset
                        all_lines.append(LineString([(a.x, a.y), (b.x, b.y)]))
                    elif item[0] == "c":
                        p0 = item[1] - offset
                        p1 = item[2] - offset
                        p2 = item[3] - offset
                        p3 = item[4] - offset
                        pts = bezier_points(p0, p1, p2, p3, n=int(bezier_adim))
                        all_lines.append(LineString(pts))

            merged = unary_union(all_lines)
            polys = list(polygonize(merged))
            if not polys:
                raise ValueError(f"Polygonize başarısız: {dosya_adi}")

            # DELİKLERİ çıkar
            outer = max(polys, key=lambda p: p.area)
            holes = [p for p in polys if p is not outer and p.within(outer)]
            poly = outer.difference(unary_union(holes)) if holes else outer
            poly = poly.buffer(float(buffer_eps))

            # 5) Tarama çizgileri
            shape_hatch = new_page.new_shape()
            w = new_page.rect.width
            h = new_page.rect.height
            diag = math.sqrt(w * w + h * h)

            angle_rad = math.radians(angle_deg)
            dx = math.cos(angle_rad)
            dy = math.sin(angle_rad)

            L = diag * 2
            nx = -dy
            ny = dx

            step = int(tarama_araligi)
            for i in range(-int(diag), int(diag), step):
                cx = nx * i + w / 2
                cy = ny * i + h / 2

                p1 = (cx - dx * L, cy - dy * L)
                p2 = (cx + dx * L, cy + dy * L)
                line = LineString([p1, p2])

                inter = poly.intersection(line)
                if inter.is_empty:
                    continue

                def draw_linestring(ls: LineString):
                    coords = list(ls.coords)
                    if len(coords) >= 2:
                        a = fitz.Point(*coords[0])
                        b = fitz.Point(*coords[-1])
                        shape_hatch.draw_line(a, b)

                gt = inter.geom_type
                if gt == "LineString":
                    draw_linestring(inter)
                elif gt == "MultiLineString":
                    for ls in inter.geoms:
                        draw_linestring(ls)
                elif gt == "GeometryCollection":
                    for g in inter.geoms:
                        if g.geom_type == "LineString":
                            draw_linestring(g)
                        elif g.geom_type == "MultiLineString":
                            for ls in g.geoms:
                                draw_linestring(ls)

            shape_hatch.finish(color=(0, 0, 0), width=0.7)
            shape_hatch.commit()

            new_doc.save(str(cikti_adi))
        finally:
            new_doc.close()

    finally:
        doc.close()

    print(f"OK: {dosya_adi} -> {cikti_adi}")
    return cikti_adi
