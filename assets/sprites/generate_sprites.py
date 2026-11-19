#!/usr/bin/env python3
"""
Generador de sprites pixel art industrial / sci-fi (top-down) estilo Mindustry.

Uso:   python generate_sprites.py
Salida: carpeta ./sprites/ junto al script, con 11 PNG (RGBA).

Convenciones:
  * Naves y cañón apuntan a la DERECHA (0° / Este).
  * Coordenadas continuas: el centro de un sprite de NxN es (N/2, N/2),
    es decir, exactamente el centro de la imagen (pivote de rotación).
  * Luz desde arriba-izquierda; contorno oscuro de 1px en todo sprite.
"""
import math
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites")
SS = 8  # supersampling usado solo para generar máscaras geométricas precisas

BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


# --------------------------------------------------------------------------
# Utilidades de color
# --------------------------------------------------------------------------
def hx(s, a=255):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(4))


def lighten(c, t):
    return mix(c, (255, 255, 255, c[3]), t)


def darken(c, t):
    return mix(c, (0, 0, 0, c[3]), t)


# --------------------------------------------------------------------------
# Máscaras (L, 0/255) con coordenadas continuas
# --------------------------------------------------------------------------
def _finish(m, size):
    m = m.resize(size, Image.BOX)
    return m.point(lambda v: 255 if v >= 128 else 0)


def poly_mask(size, pts):
    w, h = size
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).polygon([(x * SS, y * SS) for x, y in pts], fill=255)
    return _finish(m, size)


def ellipse_mask(size, cx, cy, rx, ry=None):
    ry = rx if ry is None else ry
    w, h = size
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).ellipse(
        [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS - 1, (cy + ry) * SS - 1], fill=255
    )
    return _finish(m, size)


def rect_mask(size, x0, y0, x1, y1):
    return poly_mask(size, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def regular_poly(cx, cy, r, n, rot=0.0):
    return [
        (cx + r * math.cos(math.radians(rot + 360.0 * k / n)),
         cy + r * math.sin(math.radians(rot + 360.0 * k / n)))
        for k in range(n)
    ]


def sym(upper, h):
    """Cierra un polígono simétrico respecto al eje horizontal y = h/2."""
    return list(upper) + [(x, h - y) for x, y in reversed(upper)]


def mirror(poly, h):
    return [(x, h - y) for x, y in poly]


def m_sub(a, b):
    return ImageChops.subtract(a, b)


def m_add(a, b):
    return ImageChops.lighter(a, b)


def m_and(a, b):
    return ImageChops.multiply(a, b)


# --------------------------------------------------------------------------
# Pintado
# --------------------------------------------------------------------------
def blank(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def fill(img, mask, color):
    img.paste(Image.new("RGBA", img.size, color), (0, 0), mask)


def shade(img, mask, ramp, direction=(0.25, 1.0), dither=0.22):
    """Rellena la máscara con un degradado ditherizado (ramp: de luz a sombra)."""
    w, h = img.size
    px, mp = img.load(), mask.load()
    pts = [(x, y) for y in range(h) for x in range(w) if mp[x, y]]
    if not pts:
        return
    dx, dy = direction
    proj = [x * dx + y * dy for x, y in pts]
    lo, hi = min(proj), max(proj)
    n = len(ramp)
    for (x, y), p in zip(pts, proj):
        t = (p - lo) / (hi - lo + 1e-9)
        t += (BAYER4[y % 4][x % 4] / 16.0 - 0.5) * dither / max(1, n - 1) * 2
        px[x, y] = ramp[min(n - 1, max(0, int(t * n)))]


def shade_radial(img, mask, cx, cy, radius, ramp, dither=0.2):
    """Degradado radial: ramp[0] en el centro, ramp[-1] en el borde."""
    w, h = img.size
    px, mp = img.load(), mask.load()
    n = len(ramp)
    for y in range(h):
        for x in range(w):
            if mp[x, y]:
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / radius
                d += (BAYER4[y % 4][x % 4] / 16.0 - 0.5) * dither / max(1, n - 1) * 2
                px[x, y] = ramp[min(n - 1, max(0, int(d * n)))]


def paint(img, mask, fn):
    """Dibuja con ImageDraw (fn recibe el draw) recortado por la máscara."""
    tmp = blank(img.size)
    fn(ImageDraw.Draw(tmp))
    tmp.putalpha(ImageChops.multiply(tmp.split()[3], mask))
    img.alpha_composite(tmp)


def bevel(img, mask, amount_light=0.35, amount_dark=0.35):
    """Resalta bordes superior/izquierdo y sombrea inferior/derecho dentro de la máscara."""
    w, h = img.size
    px, mp = img.load(), mask.load()

    def inside(x, y):
        return 0 <= x < w and 0 <= y < h and mp[x, y]

    for y in range(h):
        for x in range(w):
            if not mp[x, y]:
                continue
            c = px[x, y]
            if not inside(x, y - 1) or not inside(x - 1, y):
                px[x, y] = lighten(c, amount_light)
            elif not inside(x, y + 1) or not inside(x + 1, y):
                px[x, y] = darken(c, amount_dark)


def outline(img, color):
    """Contorno exterior de 1px (vecindad 8) alrededor de todo lo opaco."""
    a = img.split()[3].point(lambda v: 255 if v > 0 else 0)
    border = ImageChops.subtract(a.filter(ImageFilter.MaxFilter(3)), a)
    img.paste(Image.new("RGBA", img.size, color), (0, 0), border)


def px_set(img, pts, color):
    d = ImageDraw.Draw(img)
    for p in pts:
        d.point(p, fill=color)


def save(img, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    img.save(os.path.join(OUT_DIR, name))
    print("  ->", name, img.size)


# --------------------------------------------------------------------------
# 1. commander.png  (32x32)
# --------------------------------------------------------------------------
def make_commander():
    S, H = (32, 32), 32
    img = blank(S)
    hull = sym([(30, 16), (23, 12.5), (18, 11), (12, 3), (7, 2.5), (7, 4.5),
                (9, 10.5), (6, 12.5), (5, 16)], H)
    hull_m = poly_mask(S, hull)

    # alas (azul cobalto más oscuro)
    wing_up = [(18, 11), (12, 3), (7, 2.5), (7, 4.5), (9, 10.5), (13, 12)]
    for wing in (wing_up, mirror(wing_up, H)):
        shade(img, poly_mask(S, wing),
              [hx("#3B82F6"), hx("#2563EB"), hx("#1D4ED8"), hx("#1E3A8A")], (0.3, 1))

    # fuselaje (azul acero claro)
    fus = poly_mask(S, sym([(29.5, 16), (23, 13), (17, 12.2), (8, 12), (6.5, 14), (6.5, 16)], H))
    shade(img, fus, [hx("#BFDBFE"), hx("#93C5FD"), hx("#60A5FA"), hx("#2563EB"), hx("#1E40AF")], (0.15, 1))

    # propulsor trasero: carcasa gris + llama
    fill(img, rect_mask(S, 4, 13, 7.5, 19), hx("#6B7280"))
    fill(img, rect_mask(S, 4, 17, 7.5, 19), hx("#374151"))
    fill(img, rect_mask(S, 4, 13, 7.5, 14), hx("#D1D5DB"))
    flame = poly_mask(S, [(4.5, 14.2), (1.5, 15.2), (0.5, 16), (1.5, 16.8), (4.5, 17.8)])
    shade(img, flame, [hx("#0EA5E9"), hx("#7DD3FC"), hx("#E0F2FE"), hx("#FFFFFF")], (1, 0), 0.1)

    # cabina oscura con reflejo
    cab = poly_mask(S, sym([(24.5, 16), (20.5, 14.2), (16.5, 14.4), (14.8, 16)], H))
    shade(img, cab, [hx("#38608F"), hx("#16294A"), hx("#0A1428")], (0.2, 1), 0.1)
    px_set(img, [(19, 14), (20, 14), (21, 15), (18, 14)], hx("#BAE6FD"))
    px_set(img, [(19, 15)], hx("#7DD3FC"))

    # paneles, remaches y detalles metálicos grises
    def details(d):
        d.line([(13, 12), (13, 20)], fill=hx("#1E3A8A"))
        d.line([(10, 12), (10, 19)], fill=hx("#1E3A8A"))
        d.line([(17, 12), (12, 4)], fill=hx("#9CA3AF"))          # borde ala sup.
        d.line([(17, 19), (12, 27)], fill=hx("#9CA3AF"))         # borde ala inf.
        d.line([(10, 5), (14, 9)], fill=hx("#1E3A8A"))
        d.line([(10, 26), (14, 22)], fill=hx("#1E3A8A"))
        for p in [(11, 13), (11, 18), (15, 13), (15, 18), (9, 6), (9, 25)]:
            d.point(p, fill=hx("#E5E7EB"))
        d.point((8, 3), fill=hx("#9CA3AF"))
        d.point((8, 28), fill=hx("#9CA3AF"))
        d.point((27, 16), fill=hx("#E5E7EB"))
    paint(img, poly_mask(S, hull), details)

    # luces de punta de ala
    px_set(img, [(7, 3), (7, 28)], hx("#67E8F9"))

    bevel(img, hull_m, 0.22, 0.25)
    outline(img, hx("#0A1020"))
    return img


# --------------------------------------------------------------------------
# 2. collector.png  (32x32)
# --------------------------------------------------------------------------
def make_collector():
    S, H = (32, 32), 32
    img = blank(S)

    # pinzas frontales (chasis gris oscuro, punta lima)
    claw_up = [(15, 11), (15, 9), (27, 6.5), (30, 8), (30, 12.5), (28, 12.5),
               (28.3, 9.6), (26.5, 8.8), (16, 11.5)]
    for claw in (claw_up, mirror(claw_up, H)):
        m = poly_mask(S, claw)
        shade(img, m, [hx("#6B7280"), hx("#4B5563"), hx("#374151"), hx("#1F2937")], (0.2, 1))
        tip = m_and(m, rect_mask(S, 27.5, 0, 32, 32))
        shade(img, tip, [hx("#BBF7D0"), hx("#4ADE80"), hx("#16A34A")], (0.2, 1), 0.1)
        bevel(img, m, 0.2, 0.25)

    # cuerpo verde esmeralda
    body = poly_mask(S, sym([(26.5, 16), (20, 12), (10, 10), (6.5, 12.5), (6, 16)], H))
    shade(img, body, [hx("#86EFAC"), hx("#4ADE80"), hx("#22C55E"), hx("#16A34A"), hx("#14532D")], (0.2, 1))
    bevel(img, body, 0.22, 0.25)

    # compartimento de carga (gris oscuro con núcleo lima)
    cargo = rect_mask(S, 8.5, 12.5, 16.5, 19.5)
    shade(img, cargo, [hx("#4B5563"), hx("#374151"), hx("#1F2937")], (0.2, 1), 0.1)
    bevel(img, cargo, 0.3, 0.2)
    fill(img, rect_mask(S, 10.5, 14, 14.5, 18), hx("#14532D"))
    shade(img, rect_mask(S, 11, 14.5, 14, 17.5),
          [hx("#ECFCCB"), hx("#BEF264"), hx("#4ADE80")], (0.3, 1), 0.1)

    # sensor frontal + paneles + remaches
    def details(d):
        d.line([(19, 13), (19, 19)], fill=hx("#14532D"))
        d.line([(8, 11), (17, 11)], fill=hx("#14532D"))
        d.line([(8, 21), (17, 21)], fill=hx("#14532D"))
        for p in [(18, 12), (18, 20), (7, 14), (7, 18), (22, 14), (22, 18)]:
            d.point(p, fill=hx("#D1FAE5"))
        d.rectangle([22, 15, 24, 16], fill=hx("#0F172A"))
        d.point((24, 15), fill=hx("#BEF264"))
        d.point((24, 16), fill=hx("#4ADE80"))
    paint(img, body, details)

    # propulsores traseros duales
    for y0 in (12.0, 18.2):
        fill(img, rect_mask(S, 4, y0, 7, y0 + 1.8), hx("#4B5563"))
        shade(img, poly_mask(S, [(4.2, y0 + 0.2), (1.5, y0 + 0.6), (1.5, y0 + 1.2), (4.2, y0 + 1.6)]),
              [hx("#84CC16"), hx("#BEF264"), hx("#ECFCCB")], (1, 0), 0.1)
    outline(img, hx("#07140C"))
    return img


# --------------------------------------------------------------------------
# 3. builder.png  (32x32)
# --------------------------------------------------------------------------
def make_builder():
    S, H = (32, 32), 32
    img = blank(S)

    # brazos soldadores (detrás del casco)
    arm_up = [(17, 11.5), (24, 8), (26, 8.2), (26.6, 9.6), (19.5, 13.5)]
    for arm in (arm_up, mirror(arm_up, H)):
        m = poly_mask(S, arm)
        shade(img, m, [hx("#9CA3AF"), hx("#6B7280"), hx("#374151")], (0.2, 1), 0.1)
        bevel(img, m, 0.25, 0.25)
    # antorchas
    for y in (7.8, 24.2):
        fill(img, rect_mask(S, 25.5, y - 0.9, 28.5, y + 0.9), hx("#1F2937"))
        fill(img, rect_mask(S, 28.5, y - 0.6, 29.5, y + 0.6), hx("#F97316"))
    # chispas de soldadura
    px_set(img, [(29, 7), (29, 8), (30, 7)], hx("#FDE68A"))
    px_set(img, [(30, 8)], hx("#FFFFFF"))
    px_set(img, [(29, 24), (29, 23), (30, 24)], hx("#FDE68A"))
    px_set(img, [(30, 23)], hx("#FFFFFF"))

    # cuerpo ámbar
    hull = sym([(27, 16), (20.5, 12.8), (14, 11), (8, 10.8), (6, 12.5), (5.5, 16)], H)
    body = poly_mask(S, hull)
    shade(img, body, [hx("#FEF9C3"), hx("#FEF08A"), hx("#FACC15"), hx("#EAB308"), hx("#A16207")], (0.2, 1))

    # franjas de precaución (diagonales oscuras) en la zona trasera
    def stripes(d):
        for k in range(-6, 12, 4):
            d.line([(7 + k, 10), (13 + k, 22)], fill=hx("#1C1917"), width=2)
    paint(img, m_and(body, rect_mask(S, 6, 0, 14.5, 32)), stripes)

    # sensor/cabina
    sens = rect_mask(S, 17, 14.2, 21.5, 17.8)
    fill(img, sens, hx("#292524"))
    px_set(img, [(18, 15), (19, 15), (20, 15)], hx("#FDBA74"))
    px_set(img, [(18, 16)], hx("#FEF08A"))
    # remaches y líneas de panel
    def details(d):
        d.line([(15, 11), (15, 21)], fill=hx("#854D0E"))
        for p in [(16, 12), (16, 19), (23, 14), (23, 17), (13, 11), (13, 20)]:
            d.point(p, fill=hx("#FFFBEB"))
    paint(img, body, details)

    # propulsores
    for y0 in (12.5, 17.5):
        fill(img, rect_mask(S, 3.5, y0, 6.5, y0 + 2), hx("#44403C"))
        shade(img, poly_mask(S, [(3.8, y0 + 0.2), (1.2, y0 + 0.7), (1.2, y0 + 1.3), (3.8, y0 + 1.8)]),
              [hx("#EA580C"), hx("#FB923C"), hx("#FEF08A")], (1, 0), 0.1)
    bevel(img, body, 0.25, 0.25)
    outline(img, hx("#1C1005"))
    return img


# --------------------------------------------------------------------------
# 4. enemy.png  (32x32)
# --------------------------------------------------------------------------
def make_enemy():
    S, H = (32, 32), 32
    img = blank(S)
    hull = sym([(31, 16), (23, 13.5), (18.5, 11), (25.5, 2.5), (13, 5.5),
                (10, 11), (4, 13), (4, 16)], H)
    hull_m = poly_mask(S, hull)
    shade(img, hull_m, [hx("#FCA5A5"), hx("#F87171"), hx("#EF4444"), hx("#DC2626"),
                        hx("#991B1B"), hx("#7F1D1D")], (0.15, 1))

    # cuchillas de ala en naranja oscuro
    blade_up = [(18.5, 11), (25.5, 2.5), (13, 5.5), (10, 11), (14, 11.6)]
    for b in (blade_up, mirror(blade_up, H)):
        shade(img, poly_mask(S, b), [hx("#EA580C"), hx("#C2410C"), hx("#9A3412"), hx("#7C2D12")], (0.3, 1))

    # espina dorsal oscura
    spine = poly_mask(S, sym([(28, 16), (22, 14.8), (8, 14.2), (5, 16)], H))
    shade(img, spine, [hx("#7F1D1D"), hx("#450A0A"), hx("#2A0606")], (0.2, 1), 0.1)

    # núcleo brillante amenazante (zócalo + glow radial)
    fill(img, ellipse_mask(S, 15, 16, 4.6), hx("#3B0A0A"))
    core = ellipse_mask(S, 15, 16, 3.4)
    shade_radial(img, core, 15, 16, 3.6,
                 [hx("#FFFFFF"), hx("#FEF08A"), hx("#FB923C"), hx("#EF4444")], 0.25)

    # propulsor trasero
    flame = poly_mask(S, [(4.5, 14.3), (1.5, 15.2), (0.5, 16), (1.5, 16.8), (4.5, 17.7)])
    shade(img, flame, [hx("#EA580C"), hx("#F97316"), hx("#FDE047"), hx("#FFFFFF")], (1, 0), 0.1)

    def details(d):
        d.line([(20, 13), (22, 15)], fill=hx("#450A0A"))
        d.line([(20, 19), (22, 17)], fill=hx("#450A0A"))
        d.line([(12, 7), (16, 11)], fill=hx("#450A0A"))
        d.line([(12, 25), (16, 21)], fill=hx("#450A0A"))
        d.line([(8, 14), (8, 18)], fill=hx("#450A0A"))
        for p in [(11, 12), (11, 20), (6, 15), (6, 17), (19, 14), (19, 18)]:
            d.point(p, fill=hx("#FECACA"))
        d.point((24, 4), fill=hx("#FFEDD5"))
        d.point((24, 27), fill=hx("#FFEDD5"))
    paint(img, hull_m, details)
    px_set(img, [(30, 16), (29, 16)], hx("#FEF08A"))   # punta de nariz incandescente

    bevel(img, hull_m, 0.2, 0.3)
    outline(img, hx("#1A0505"))
    return img


# --------------------------------------------------------------------------
# 5. turret_base.png  (32x32)
# --------------------------------------------------------------------------
def make_turret_base():
    S = (32, 32)
    img = blank(S)
    steel = [hx("#D1D5DB"), hx("#9CA3AF"), hx("#6B7280"), hx("#4B5563"), hx("#374151")]

    outer = poly_mask(S, regular_poly(16, 16, 15, 8, 22.5))
    shade(img, outer, steel, (0.5, 1))
    bevel(img, outer, 0.3, 0.3)

    plate = poly_mask(S, regular_poly(16, 16, 12.2, 8, 22.5))
    shade(img, plate, [hx("#9CA3AF"), hx("#8A929E"), hx("#6B7280"), hx("#59616D")], (0.4, 1), 0.3)
    bevel(img, plate, 0.25, 0.3)

    # anclajes al suelo en las esquinas
    for (x0, y0) in [(2, 2), (24, 2), (2, 24), (24, 24)]:
        pl = rect_mask(S, x0, y0, x0 + 6, y0 + 6)
        shade(img, pl, [hx("#6B7280"), hx("#4B5563"), hx("#374151")], (0.5, 1), 0.2)
        bevel(img, pl, 0.35, 0.3)
        fill(img, rect_mask(S, x0 + 2, y0 + 2, x0 + 4, y0 + 4), hx("#1F2937"))
        px_set(img, [(x0 + 2, y0 + 2)], hx("#E5E7EB"))

    # anillo de rotación
    ring_out = ellipse_mask(S, 16, 16, 9.5)
    ring_in = ellipse_mask(S, 16, 16, 8)
    ring = m_sub(ring_out, ring_in)
    shade(img, ring, [hx("#E5E7EB"), hx("#9CA3AF"), hx("#4B5563")], (0.5, 1), 0.2)
    groove = m_sub(ellipse_mask(S, 16, 16, 8), ellipse_mask(S, 16, 16, 7))
    fill(img, groove, hx("#1F2937"))
    track = ellipse_mask(S, 16, 16, 7)
    shade(img, track, [hx("#4B5563"), hx("#6B7280"), hx("#9CA3AF")], (0.5, 1), 0.2)

    # muescas de la corona dentada
    def teeth(d):
        for k in range(16):
            a = math.radians(k * 22.5)
            x, y = 16 + 8.6 * math.cos(a), 16 + 8.6 * math.sin(a)
            d.point((int(x), int(y)), fill=hx("#374151"))
    paint(img, ring, teeth)

    # buje central
    hub = ellipse_mask(S, 16, 16, 4)
    shade_radial(img, hub, 14.5, 14.5, 5.5, [hx("#9CA3AF"), hx("#6B7280"), hx("#374151")], 0.2)
    bevel(img, hub, 0.2, 0.3)

    # remaches en la placa
    for p in [(16, 3), (16, 28), (3, 16), (28, 16)]:
        px_set(img, [p], hx("#E5E7EB"))
    outline(img, hx("#111827"))
    return img


# --------------------------------------------------------------------------
# 6. turret_gun.png  (32x32) — apunta a la derecha, pivote en (16,16)
# --------------------------------------------------------------------------
def make_turret_gun():
    S, H = (32, 32), 32
    img = blank(S)
    gr = [hx("#6B7280"), hx("#4B5563"), hx("#374151"), hx("#1F2937"), hx("#111827")]

    # camisa/refrigeración del cañón
    jacket = rect_mask(S, 19, 12.5, 26.5, 19.5)
    shade(img, jacket, gr, (0, 1), 0.2)
    bevel(img, jacket, 0.3, 0.3)

    # tubo del cañón
    barrel = rect_mask(S, 19, 14, 29, 18)
    shade(img, barrel, [hx("#9CA3AF"), hx("#4B5563"), hx("#374151"), hx("#1F2937")], (0, 1), 0.15)

    # boca reforzada
    muzzle = poly_mask(S, [(26.5, 12), (30.2, 12.6), (30.8, 13.2), (30.8, 18.8), (30.2, 19.4),
                           (26.5, 20)])
    shade(img, muzzle, [hx("#9CA3AF"), hx("#6B7280"), hx("#374151"), hx("#1F2937")], (0, 1), 0.15)
    bevel(img, muzzle, 0.25, 0.25)
    fill(img, rect_mask(S, 30, 14.3, 31, 17.7), hx("#030712"))  # ánima

    # recámara / culata
    breech = poly_mask(S, [(7, 12), (9, 10), (20, 10), (20, 22), (9, 22), (7, 20)])
    shade(img, breech, gr, (0.1, 1), 0.2)
    bevel(img, breech, 0.28, 0.3)

    def details(d):
        # ventilaciones de la recámara
        for x in (10, 12, 14):
            d.line([(x, 12), (x, 14)], fill=hx("#111827"))
            d.line([(x, 18), (x, 20)], fill=hx("#111827"))
        # refrigeración
        for x in (21, 23, 25):
            d.line([(x, 13), (x, 14)], fill=hx("#111827"))
            d.line([(x, 18), (x, 19)], fill=hx("#111827"))
        # brillo metálico del tubo
        d.line([(20, 14), (29, 14)], fill=hx("#D1D5DB"))
        d.line([(20, 17), (26, 17)], fill=hx("#1F2937"))
        # remaches
        for p in [(8, 13), (8, 18), (18, 11), (18, 20), (27, 13), (27, 18)]:
            d.point(p, fill=hx("#D1D5DB"))
    paint(img, m_add(m_add(breech, jacket), barrel), details)

    # tapa del pivote (centro exacto)
    cap = ellipse_mask(S, 16, 16, 4.6)
    shade_radial(img, cap, 14.8, 14.8, 6.5, [hx("#E5E7EB"), hx("#9CA3AF"), hx("#6B7280"), hx("#4B5563")], 0.2)
    bevel(img, cap, 0.2, 0.3)
    fill(img, ellipse_mask(S, 16, 16, 1.6), hx("#1F2937"))
    px_set(img, [(15, 15)], hx("#9CA3AF"))

    outline(img, hx("#030712"))
    return img


# --------------------------------------------------------------------------
# 7. command_center.png  (64x64)
# --------------------------------------------------------------------------
def make_command_center():
    S = (64, 64)
    img = blank(S)
    C = 32

    outer = poly_mask(S, regular_poly(C, C, 30.5, 6, 0))
    shade(img, outer, [hx("#F9FAFB"), hx("#F3F4F6"), hx("#E5E7EB"), hx("#D1D5DB"),
                       hx("#9CA3AF"), hx("#6B7280")], (0.45, 1))
    bevel(img, outer, 0.35, 0.3)

    # anillo de placas blindadas
    ring_o = poly_mask(S, regular_poly(C, C, 27.5, 6, 0))
    ring_i = poly_mask(S, regular_poly(C, C, 18.5, 6, 0))
    plates = m_sub(ring_o, ring_i)
    shade(img, plates, [hx("#F3F4F6"), hx("#E5E7EB"), hx("#D1D5DB"), hx("#B7BDC8"), hx("#9CA3AF")],
          (0.45, 1), 0.3)

    def seams(d):
        for k in range(6):
            a = math.radians(60 * k)
            p0 = (C + 18 * math.cos(a), C + 18 * math.sin(a))
            p1 = (C + 28 * math.cos(a), C + 28 * math.sin(a))
            d.line([p0, p1], fill=hx("#6B7280"), width=2)
            # luz junto a la costura (lado superior-izquierdo)
            q0 = (p0[0] - 1.2, p0[1] - 1.2)
            q1 = (p1[0] - 1.2, p1[1] - 1.2)
            d.line([q0, q1], fill=hx("#FFFFFF"), width=1)
        # ventilaciones en el centro de cada lado
        for k in range(6):
            a = math.radians(30 + 60 * k)
            ca, sa = math.cos(a), math.sin(a)
            for off in (-4, -2, 0, 2, 4):
                tx, ty = -sa * off, ca * off
                p0 = (C + 21.5 * ca + tx, C + 21.5 * sa + ty)
                p1 = (C + 25.5 * ca + tx, C + 25.5 * sa + ty)
                d.line([p0, p1], fill=hx("#4B5563"), width=1)
    paint(img, plates, seams)

    # torretas/remaches en los vértices
    for k in range(6):
        a = math.radians(60 * k)
        x, y = C + 27.5 * math.cos(a), C + 27.5 * math.sin(a)
        node = ellipse_mask(S, x, y, 2.4)
        shade(img, node, [hx("#6B7280"), hx("#374151"), hx("#1F2937")], (0.4, 1), 0.2)
        px_set(img, [(int(x - 1), int(y - 1))], hx("#E5E7EB"))

    # suelo interior hundido
    inner = poly_mask(S, regular_poly(C, C, 17, 6, 0))
    shade(img, inner, [hx("#6B7280"), hx("#8B93A1"), hx("#B8BEC9"), hx("#D1D5DB")], (0.45, 1), 0.3)
    # (bisel invertido: sombra arriba-izq, luz abajo-der)
    inner_edge = m_sub(inner, poly_mask(S, regular_poly(C, C, 15.8, 6, 0)))
    def edge(d):
        d.rectangle([0, 0, 63, 31], fill=hx("#4B5563"))
        d.rectangle([0, 32, 63, 63], fill=hx("#FFFFFF"))
    paint(img, inner_edge, edge)

    # líneas de energía hacia el núcleo
    def energy(d):
        for k in range(6):
            a = math.radians(30 + 60 * k)
            ca, sa = math.cos(a), math.sin(a)
            p0 = (C + 9 * ca, C + 9 * sa)
            p1 = (C + 16 * ca, C + 16 * sa)
            d.line([p0, p1], fill=hx("#67E8F9"), width=1)
            d.point((int(C + 12.5 * ca), int(C + 12.5 * sa)), fill=hx("#FFFFFF"))
    paint(img, inner, energy)

    # zócalo y núcleo energético
    fill(img, ellipse_mask(S, C, C, 10.5), hx("#374151"))
    fill(img, ellipse_mask(S, C, C, 9.5), hx("#9CA3AF"))
    fill(img, ellipse_mask(S, C, C, 8.7), hx("#1F2937"))
    glow = ellipse_mask(S, C, C, 8)
    shade_radial(img, glow, C, C, 8.2,
                 [hx("#FFFFFF"), hx("#CFFAFE"), hx("#A5F3FC"), hx("#67E8F9"),
                  hx("#22D3EE"), hx("#0891B2"), hx("#155E75")], 0.3)
    px_set(img, [(28, 28), (29, 28), (28, 29)], hx("#FFFFFF"))  # brillo especular

    outline(img, hx("#1F2937"))
    return img


# --------------------------------------------------------------------------
# 8. resource_crystal.png  (32x32)
# --------------------------------------------------------------------------
def make_crystal():
    S = (32, 32)
    img = blank(S)
    edge = hx("#083344")

    def facet(poly, c0, c1=None, d=(0.3, 1)):
        m = poly_mask(S, poly)
        shade(img, m, [c0, c1 or c0], d, 0.2)
        return m

    # cristales secundarios (detrás)
    left = [(5, 20), (8.5, 13.5), (12, 19), (11, 26), (5.5, 26)]
    right = [(20.5, 20), (25, 12.5), (28.5, 19.5), (27, 26), (21.5, 26)]
    facet([(5, 20), (8.5, 13.5), (8.5, 26), (5.5, 26)], hx("#22D3EE"), hx("#06B6D4"))
    facet([(8.5, 13.5), (12, 19), (11, 26), (8.5, 26)], hx("#0E7490"), hx("#0891B2"))
    facet([(20.5, 20), (25, 12.5), (25, 26), (21.5, 26)], hx("#67E8F9"), hx("#22D3EE"))
    facet([(25, 12.5), (28.5, 19.5), (27, 26), (25, 26)], hx("#0E7490"), hx("#155E75"))

    # cristal principal
    T, UL, UR = (16, 2.5), (9.5, 10), (22.5, 10)
    G2, G3 = (13.5, 10), (18.5, 10)
    LL, LR, B = (11.5, 22), (20.5, 22), (16, 27)
    facet([T, UL, G2], hx("#67E8F9"), hx("#22D3EE"))
    facet([T, G2, G3], hx("#CFFAFE"), hx("#A5F3FC"))
    facet([T, G3, UR], hx("#22D3EE"), hx("#06B6D4"))
    facet([UL, G2, B, LL], hx("#06B6D4"), hx("#0891B2"))
    facet([G2, G3, B], hx("#67E8F9"), hx("#22D3EE"))
    facet([G3, UR, LR, B], hx("#0E7490"), hx("#0891B2"))

    # aristas brillantes entre facetas y especulares
    d = ImageDraw.Draw(img)
    lite = hx("#ECFEFF")
    for a, b in [(T, G2), (T, G3), (G2, B), (G3, B)]:
        d.line([a, b], fill=lite)
    d.line([UL, G2], fill=hx("#A5F3FC"))
    d.line([G3, UR], fill=hx("#0891B2"))
    d.line([UR, LR], fill=hx("#155E75"))
    d.line([LL, B], fill=hx("#0E7490"))
    px_set(img, [(15, 5), (14, 6), (15, 6), (14, 7)], hx("#FFFFFF"))
    px_set(img, [(21, 11), (21, 12)], hx("#CFFAFE"))
    px_set(img, [(7, 17), (7, 18)], hx("#CFFAFE"))
    px_set(img, [(23, 16), (23, 17)], hx("#CFFAFE"))

    outline(img, edge)

    # sombra en la base (se compone por debajo del cristal)
    sh = blank(S)
    shadow_m = ellipse_mask(S, 16, 26.8, 12.5, 3.2)
    fill(sh, shadow_m, (0, 0, 0, 95))
    sh.alpha_composite(img)
    return sh


# --------------------------------------------------------------------------
# 9. bullet.png  (16x16)
# --------------------------------------------------------------------------
def make_bullet():
    img = blank((16, 16))
    px = img.load()
    rings = [
        (2.7, hx("#FFFFFF")),
        (3.9, hx("#FFFBD0")),
        (5.0, hx("#FDE047", 190)),
        (6.3, hx("#FACC15", 80)),
        (7.5, hx("#FDE68A", 34)),
    ]
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
            for r, c in rings:
                if d < r:
                    px[x, y] = c
                    break
    return img


# --------------------------------------------------------------------------
# Texturas tileables
# --------------------------------------------------------------------------
def tile_noise(n, cell, seed):
    rnd = random.Random(seed)
    g = n // cell
    grid = [[rnd.random() for _ in range(g)] for _ in range(g)]
    sm = lambda t: t * t * (3 - 2 * t)
    out = [[0.0] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            gx, gy = x / cell, y / cell
            x0, y0 = int(gx) % g, int(gy) % g
            x1, y1 = (x0 + 1) % g, (y0 + 1) % g
            fx, fy = sm(gx - int(gx)), sm(gy - int(gy))
            a = grid[y0][x0] * (1 - fx) + grid[y0][x1] * fx
            b = grid[y1][x0] * (1 - fx) + grid[y1][x1] * fx
            out[y][x] = a * (1 - fy) + b * fy
    return out


# --------------------------------------------------------------------------
# 10. tile_ground.png  (64x64, tileable)
# --------------------------------------------------------------------------
def make_tile_ground():
    N = 64
    img = Image.new("RGBA", (N, N), hx("#5C4033"))
    px = img.load()
    rnd = random.Random(7)
    n1, n2, n3 = tile_noise(N, 16, 1), tile_noise(N, 8, 2), tile_noise(N, 4, 3)
    ramp = [hx("#4A332A"), hx("#54392E"), hx("#5C4033"), hx("#664839"), hx("#6E4E3E")]
    for y in range(N):
        for x in range(N):
            v = 0.5 * n1[y][x] + 0.32 * n2[y][x] + 0.18 * n3[y][x]
            v = (v - 0.5) * 1.5 + 0.5
            v += (BAYER4[y % 4][x % 4] / 16.0 - 0.5) * 0.16
            px[x, y] = ramp[min(4, max(0, int(v * 5)))]

    def put(x, y, c):
        px[x % N, y % N] = c

    # motas sutiles
    for _ in range(170):
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(x, y, rnd.choice([hx("#47302A"), hx("#3F2B23"), hx("#725241"), hx("#6A4B3B")]))

    # grietas tenues (caminatas aleatorias con wrap)
    for _ in range(5):
        x, y = rnd.randrange(N), rnd.randrange(N)
        ang = rnd.uniform(0, math.tau)
        for _ in range(rnd.randint(9, 20)):
            ang += rnd.uniform(-0.6, 0.6)
            x += math.cos(ang)
            y += math.sin(ang)
            put(int(x), int(y), hx("#3B2820"))
            put(int(x) - 1, int(y) - 1, hx("#74543F"))

    # piedras pequeñas con luz/sombra
    for _ in range(14):
        cx, cy = rnd.uniform(0, N), rnd.uniform(0, N)
        rx, ry = rnd.uniform(1.4, 3.0), rnd.uniform(1.2, 2.4)
        # sombra proyectada
        for yy in range(int(cy - 5), int(cy + 6)):
            for xx in range(int(cx - 6), int(cx + 7)):
                if ((xx + 0.5 - cx - 1) / rx) ** 2 + ((yy + 0.5 - cy - 1) / ry) ** 2 < 1:
                    put(xx, yy, hx("#3A2820"))
        # cuerpo
        for yy in range(int(cy - 5), int(cy + 6)):
            for xx in range(int(cx - 6), int(cx + 7)):
                ex = (xx + 0.5 - cx) / rx
                ey = (yy + 0.5 - cy) / ry
                if ex * ex + ey * ey < 1:
                    t = (ex + ey + 2) / 4 + (BAYER4[yy % 4][xx % 4] / 16 - 0.5) * 0.25
                    put(xx, yy, [hx("#8A6A57"), hx("#7B5B49"), hx("#6E4E3E"), hx("#5A3F33")]
                        [min(3, max(0, int(t * 4)))])
    return img


# --------------------------------------------------------------------------
# 11. tile_wall.png  (64x64)
# --------------------------------------------------------------------------
def make_tile_wall():
    N = 64
    img = Image.new("RGBA", (N, N), hx("#27272A"))
    px = img.load()
    rnd = random.Random(11)

    # celdas tipo Voronoi (toroidal) = bloques de roca facetados
    seeds = [(rnd.uniform(0, N), rnd.uniform(0, N)) for _ in range(11)]
    base_tone = [rnd.choice([0.38, 0.5, 0.62]) for _ in seeds]
    ramp = [hx("#18181B"), hx("#202023"), hx("#27272A"), hx("#323237"), hx("#3F3F46"), hx("#4A4A52")]

    def tdist(a, b):
        d = abs(a - b)
        return min(d, N - d)

    for y in range(N):
        for x in range(N):
            best = []
            for i, (sx, sy) in enumerate(seeds):
                dx, dy = tdist(x + 0.5, sx), tdist(y + 0.5, sy)
                best.append((dx * dx + dy * dy, i))
            best.sort()
            d1, i1 = math.sqrt(best[0][0]), best[0][1]
            d2 = math.sqrt(best[1][0])
            sx, sy = seeds[i1]
            # vector firmado (con wrap) desde la semilla hasta el pixel
            vx = (x + 0.5 - sx + N / 2) % N - N / 2
            vy = (y + 0.5 - sy + N / 2) % N - N / 2
            light = -(vx + vy) / 28.0        # luz desde arriba-izquierda
            t = base_tone[i1] + light * 0.35 + (BAYER4[y % 4][x % 4] / 16 - 0.5) * 0.12
            c = ramp[min(5, max(0, int(t * 6)))]
            gap = d2 - d1
            if gap < 1.1:
                c = hx("#18181B")
            elif gap < 2.0:
                c = darken(c, 0.25)
            px[x, y] = c

    # grietas rocosas adicionales
    def put(x, y, c):
        px[x % N, y % N] = c
    for _ in range(4):
        x, y = rnd.randrange(N), rnd.randrange(N)
        ang = rnd.uniform(0, math.tau)
        for _ in range(rnd.randint(10, 22)):
            ang += rnd.uniform(-0.7, 0.7)
            x += math.cos(ang)
            y += math.sin(ang)
            put(int(x), int(y), hx("#18181B"))
            put(int(x) - 1, int(y) - 1, hx("#4A4A52"))

    # motas de mineral/polvo
    for _ in range(60):
        put(rnd.randrange(N), rnd.randrange(N), rnd.choice([hx("#3F3F46"), hx("#18181B"), hx("#2F2F34")]))

    # relieve: borde superior/izquierdo iluminado, inferior/derecho sombreado
    for i in range(N):
        for k, (a, t) in enumerate([(0.0, 0.55), (0.0, 0.30)]):
            px[i, k] = lighten(px[i, k], t)
        px[0, i] = lighten(px[0, i], 0.35)
        for k, t in enumerate([0.6, 0.45, 0.28]):
            px[i, N - 1 - k] = darken(px[i, N - 1 - k], t)
        for k, t in enumerate([0.5, 0.3]):
            px[N - 1 - k, i] = darken(px[N - 1 - k, i], t)
    # esquinas
    px[0, 0] = lighten(px[0, 0], 0.5)
    px[N - 1, N - 1] = darken(px[N - 1, N - 1], 0.7)
    return img


# --------------------------------------------------------------------------
def main():
    print("Generando sprites en:", OUT_DIR)
    jobs = [
        ("commander.png", make_commander),
        ("collector.png", make_collector),
        ("builder.png", make_builder),
        ("enemy.png", make_enemy),
        ("turret_base.png", make_turret_base),
        ("turret_gun.png", make_turret_gun),
        ("command_center.png", make_command_center),
        ("resource_crystal.png", make_crystal),
        ("bullet.png", make_bullet),
        ("tile_ground.png", make_tile_ground),
        ("tile_wall.png", make_tile_wall),
    ]
    for name, fn in jobs:
        save(fn(), name)
    print("Listo: %d sprites generados." % len(jobs))


if __name__ == "__main__":
    main()
