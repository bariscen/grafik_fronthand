# ... (üst kısımdaki importlar ve bezier_points aynı kalıyor)

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
    if not dosya_adi.exists():
        raise FileNotFoundError(f"PDF bulunamadı: {dosya_adi}")

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

        # --- ADIM 1: SENİN ORİJİNAL KODUN ---
        # Önce tam 2.83 kalınlığını (0.1 tolerans ile) arıyoruz
        bicak_izleri = [
            p for p in paths
            if p.get("width") is not None
            and abs(p["width"] - hedef_kalinlik) <= 0.1
            and p["rect"].y1 < (page_height / 2)
        ]

        # --- ADIM 2: EĞER HATA VERİRSE (BOŞSA) EN KALIN ÇİZGİYE GİT ---
        if not bicak_izleri:
            # Sayfanın üst yarısındaki, genişliği olan tüm yolları al
            upper_paths = [p for p in paths if p["rect"].y1 < (page_height / 2) and p.get("width") is not None]
            if upper_paths:
                # Bulabildiği en büyük kalınlığı tespit et
                max_w = max(p["width"] for p in upper_paths)
                # Sadece bu kalınlıktaki (veya çok yakınındaki) çizgileri seç
                if max_w > 0.5: # Yazı veya çok ince çizgi olmasın diye emniyet
                    bicak_izleri = [p for p in upper_paths if abs(p["width"] - max_w) < 0.1]

        # Eğer hala bulunamadıysa şimdi hata fırlatabiliriz
        if not bicak_izleri:
            raise ValueError(f"Bıçak izi bulunamadı: {dosya_adi.name}")

        # ... (Geri kalan işlemler: union_rect, poligon oluşturma ve tarama aynı kalıyor)

        # Poligon oluştururken de senin orijinal polygonize mantığını koruyup,
        # başarısız olursa buffer'lı kurtarmayı (B Planı) aşağıda tutuyorum:

        union_rect = bicak_izleri[0]["rect"]
        for p in bicak_izleri[1:]:
            union_rect |= p["rect"]

        final_rect = union_rect # Orijinal kodunda margin yoktu, koruyoruz

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

            merged = unary_union(all_lines)
            polys = list(polygonize(merged))

            # Senin kodunda polygonize başarısız olunca sistem çöküyordu.
            # Buraya o %10'luk kısım için buffer kurtarmasını ekledim:
            if not polys:
                refined = merged.buffer(0.2).buffer(-0.2)
                if refined.geom_type == 'Polygon':
                    polys = [refined]
                elif hasattr(refined, 'geoms'):
                    polys = [g for g in refined.geoms if g.geom_type == 'Polygon']

            if not polys:
                raise ValueError(f"Polygonize başarısız: {dosya_adi.name}")

            outer = max(polys, key=lambda p: p.area)
            holes = [p for p in polys if p is not outer and p.within(outer)]
            poly = outer.difference(unary_union(holes)) if holes else outer
            poly = poly.buffer(float(buffer_eps))

            # Tarama kısmı (Senin orijinal tarama kodun)
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

    print(f"OK: {dosya_adi} -> {cikti_adi}")
    return cikti_adi
