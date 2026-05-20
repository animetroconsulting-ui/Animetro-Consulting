from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "assets" / "brand"
EXPORT_DIR = BRAND_DIR / "exports"

NAVY = "#081A34"
GOLD = "#B58928"
GOLD_DARK = "#8F6A18"
PAPER = "#FFFDF8"
WHITE = "#FFFFFF"

FONT_SERIF = "/System/Library/Fonts/Supplemental/Baskerville.ttc"
FONT_SERIF_BOLD = "/System/Library/Fonts/Palatino.ttc"
FONT_CHINESE = "/System/Library/Fonts/Supplemental/Songti.ttc"


def ensure_dirs():
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def font(path, size, index=0):
    return ImageFont.truetype(path, size=size, index=index)


def text_center(draw, box, text, fnt, fill, tracking=0):
    x1, y1, x2, y2 = box
    if tracking == 0:
        bbox = draw.textbbox((0, 0), text, font=fnt)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((x1 + (x2 - x1 - w) / 2, y1 + (y2 - y1 - h) / 2 - bbox[1]), text, font=fnt, fill=fill)
        return
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    start = x1 + (x2 - x1 - total) / 2
    bbox = draw.textbbox((0, 0), text, font=fnt)
    y = y1 + (y2 - y1 - (bbox[3] - bbox[1])) / 2 - bbox[1]
    for ch, width in zip(text, widths):
        draw.text((start, y), ch, font=fnt, fill=fill)
        start += width + tracking


def draw_monogram(draw, cx, cy, scale, color=NAVY, accent=GOLD):
    serif = font(FONT_SERIF_BOLD, int(170 * scale), 0)
    inf = font(FONT_SERIF, int(104 * scale), 0)
    a_bbox = draw.textbbox((0, 0), "A", font=serif)
    a_w = a_bbox[2] - a_bbox[0]
    a_h = a_bbox[3] - a_bbox[1]
    draw.text((cx - a_w * 0.74, cy - a_h * 0.58 - a_bbox[1]), "A", font=serif, fill=color)
    i_bbox = draw.textbbox((0, 0), "∞", font=inf)
    i_w = i_bbox[2] - i_bbox[0]
    i_h = i_bbox[3] - i_bbox[1]
    draw.text((cx - i_w * 0.04, cy - i_h * 0.36 - i_bbox[1]), "∞", font=inf, fill=accent)
    y = cy + 88 * scale
    draw.line((cx - 112 * scale, y, cx + 112 * scale, y), fill=accent, width=max(2, int(5 * scale)))
    draw.ellipse((cx - 7 * scale, y - 7 * scale, cx + 7 * scale, y + 7 * scale), fill=accent)


def smooth_leaf_points(cx, cy, length, width, angle):
    points = [
        (0, -length * 0.50),
        (width * 0.34, -length * 0.34),
        (width * 0.50, -length * 0.10),
        (width * 0.42, length * 0.18),
        (width * 0.20, length * 0.42),
        (0, length * 0.50),
        (-width * 0.20, length * 0.42),
        (-width * 0.42, length * 0.18),
        (-width * 0.50, -length * 0.10),
        (-width * 0.34, -length * 0.34),
    ]
    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return [
        (cx + x * cos_a - y * sin_a, cy + x * sin_a + y * cos_a)
        for x, y in points
    ]


def draw_laurel(draw, cx, cy, radius, side, color=GOLD, line_color=NAVY, scale=1):
    start, end = (128, 232) if side == "left" else (-52, 52)
    stem = []
    for i in range(40):
        t = start + (end - start) * i / 39
        rad = math.radians(t)
        stem.append((cx + radius * math.cos(rad), cy + radius * math.sin(rad)))
    draw.line(stem, fill=color, width=max(3, int(8 * scale)), joint="curve")
    for idx, t in enumerate([136, 146, 156, 166, 176, 186, 196, 206, 216]):
        angle = t if side == "left" else 180 - t
        rad = math.radians(t if side == "left" else 180 - t)
        px = cx + radius * math.cos(rad)
        py = cy + radius * math.sin(rad)
        lean = angle - (34 if side == "left" else -34)
        leaf = smooth_leaf_points(px, py, 86 * scale, 34 * scale, lean)
        draw.polygon(leaf, fill=color, outline=GOLD_DARK)
        vein_end = (px + 30 * scale * math.cos(math.radians(lean - 90)), py + 30 * scale * math.sin(math.radians(lean - 90)))
        draw.line((px, py, *vein_end), fill=PAPER, width=max(1, int(2 * scale)))


def draw_book(draw, cx, cy, scale, color=GOLD, outline=NAVY):
    w = 210 * scale
    h = 86 * scale
    gap = 12 * scale
    left = [
        (cx - gap, cy + h * 0.36),
        (cx - w * 0.52, cy + h * 0.18),
        (cx - w * 0.52, cy - h * 0.42),
        (cx - gap, cy - h * 0.22),
    ]
    right = [
        (cx + gap, cy + h * 0.36),
        (cx + w * 0.52, cy + h * 0.18),
        (cx + w * 0.52, cy - h * 0.42),
        (cx + gap, cy - h * 0.22),
    ]
    draw.polygon(left, fill=PAPER, outline=color)
    draw.polygon(right, fill=PAPER, outline=color)
    draw.line((cx, cy + h * 0.38, cx, cy - h * 0.25), fill=color, width=max(2, int(4 * scale)))
    draw.arc((cx - w * 0.58, cy - h * 0.22, cx - gap, cy + h * 0.56), 200, 348, fill=color, width=max(2, int(4 * scale)))
    draw.arc((cx + gap, cy - h * 0.22, cx + w * 0.58, cy + h * 0.56), 192, 340, fill=color, width=max(2, int(4 * scale)))
    draw.line((cx - w * 0.58, cy + h * 0.5, cx, cy + h * 0.68, cx + w * 0.58, cy + h * 0.5), fill=outline, width=max(2, int(3 * scale)))


def draw_seal(draw, cx, cy, radius, text_color=NAVY, bg=None, scale=1):
    if bg:
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=bg)
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=GOLD, width=max(5, int(12 * scale)))
    draw.ellipse((cx - radius * 0.91, cy - radius * 0.91, cx + radius * 0.91, cy + radius * 0.91), outline=text_color, width=max(3, int(8 * scale)))
    draw.ellipse((cx - radius * 0.84, cy - radius * 0.84, cx + radius * 0.84, cy + radius * 0.84), outline=GOLD, width=max(2, int(4 * scale)))


def save_primary_png(path, bg=None, navy_variant=False, size=1800):
    s = size / 1800
    img = Image.new("RGBA", (size, size), bg if bg else (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    color = WHITE if navy_variant else NAVY
    inner_bg = NAVY if navy_variant else WHITE
    draw_laurel(draw, 900 * s, 775 * s, 700 * s, "left", scale=2.0 * s, line_color=color)
    draw_laurel(draw, 900 * s, 775 * s, 700 * s, "right", scale=2.0 * s, line_color=color)
    draw_seal(draw, 900 * s, 720 * s, 505 * s, text_color=color, bg=inner_bg, scale=1.8 * s)
    draw_monogram(draw, 900 * s, 548 * s, 1.9 * s, color=color, accent=GOLD)
    text_center(draw, (315 * s, 825 * s, 1485 * s, 930 * s), "ANIMETRO", font(FONT_SERIF_BOLD, int(98 * s)), color, tracking=int(8 * s))
    draw.line((500 * s, 970 * s, 620 * s, 970 * s), fill=GOLD, width=max(2, int(5 * s)))
    text_center(draw, (645 * s, 928 * s, 1155 * s, 1005 * s), "CONSULTING", font(FONT_SERIF, int(46 * s)), GOLD, tracking=int(9 * s))
    draw.line((1180 * s, 970 * s, 1300 * s, 970 * s), fill=GOLD, width=max(2, int(5 * s)))
    draw_book(draw, 900 * s, 1115 * s, 1.2 * s, outline=color)
    text_center(draw, (330 * s, 1328 * s, 1470 * s, 1408 * s), "EDUCATION CONSULTING", font(FONT_SERIF, int(48 * s)), GOLD, tracking=int(6 * s))
    text_center(draw, (360 * s, 1418 * s, 1440 * s, 1498 * s), "艾美加教育顾问", font(FONT_CHINESE, int(54 * s)), color)
    img.save(path)


def save_daily_logo_png(path, bg=None, navy_variant=False, size=1800):
    img = Image.new("RGBA", (size, size), bg if bg else (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    s = size / 1800
    color = WHITE if navy_variant else NAVY
    draw_monogram(draw, 900 * s, 520 * s, 2.15 * s, color=color, accent=GOLD)
    text_center(draw, (260 * s, 890 * s, 1540 * s, 1015 * s), "ANIMETRO", font(FONT_SERIF_BOLD, int(112 * s)), color, tracking=int(10 * s))
    text_center(draw, (310 * s, 1028 * s, 1490 * s, 1100 * s), "EDUCATION CONSULTING", font(FONT_SERIF, int(48 * s)), GOLD, tracking=int(7 * s))
    draw.line((560 * s, 1162 * s, 1240 * s, 1162 * s), fill=GOLD, width=max(2, int(4 * s)))
    text_center(draw, (350 * s, 1215 * s, 1450 * s, 1295 * s), "艾美加教育顾问", font(FONT_CHINESE, int(54 * s)), color)
    img.save(path)


def save_horizontal_png(path, bg=None, navy_variant=False):
    img = Image.new("RGBA", (2200, 620), bg if bg else (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    color = WHITE if navy_variant else NAVY
    draw_monogram(draw, 335, 280, 1.45, color=color, accent=GOLD)
    draw.line((620, 150, 620, 470), fill=GOLD, width=5)
    draw.text((710, 138), "ANIMETRO", font=font(FONT_SERIF_BOLD, 92), fill=color)
    draw.text((715, 254), "EDUCATION CONSULTING", font=font(FONT_SERIF, 45), fill=GOLD)
    draw.text((716, 338), "艾美加教育顾问", font=font(FONT_CHINESE, 48), fill=color)
    img.save(path)


def save_icon_png(path, size=1024, bg=None, seal=False):
    img = Image.new("RGBA", (size, size), bg if bg else (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    if seal:
        pad = int(size * 0.08)
        draw_laurel(draw, size / 2, size * 0.55, size * 0.43, "left", scale=size / 900, line_color=NAVY)
        draw_laurel(draw, size / 2, size * 0.55, size * 0.43, "right", scale=size / 900, line_color=NAVY)
        draw_seal(draw, size / 2, size * 0.5, size * 0.32, text_color=NAVY, bg=WHITE, scale=size / 900)
        text_center(draw, (size * 0.25, size * 0.48, size * 0.75, size * 0.56), "ANIMETRO", font(FONT_SERIF_BOLD, size // 18), NAVY, tracking=3)
        text_center(draw, (size * 0.28, size * 0.57, size * 0.72, size * 0.63), "CONSULTING", font(FONT_SERIF, size // 32), GOLD, tracking=3)
        draw_book(draw, size / 2, size * 0.70, size / 1400, outline=NAVY)
        draw_monogram(draw, size / 2, size * 0.36, size / 780, color=NAVY, accent=GOLD)
    else:
        draw_monogram(draw, size / 2, size / 2 - (size * 0.03), size / 580, color=NAVY, accent=GOLD)
    img.save(path)


def save_social_png(path):
    img = Image.new("RGBA", (1600, 1600), NAVY)
    draw = ImageDraw.Draw(img)
    draw_laurel(draw, 800, 850, 610, "left", scale=1.7, line_color=WHITE)
    draw_laurel(draw, 800, 850, 610, "right", scale=1.7, line_color=WHITE)
    draw_seal(draw, 800, 735, 430, text_color=WHITE, bg=NAVY, scale=1.5)
    draw_monogram(draw, 800, 585, 1.65, color=WHITE, accent=GOLD)
    text_center(draw, (315, 840, 1285, 930), "ANIMETRO", font(FONT_SERIF_BOLD, 82), WHITE, tracking=7)
    text_center(draw, (470, 935, 1130, 1005), "CONSULTING", font(FONT_SERIF, 40), GOLD, tracking=8)
    draw_book(draw, 800, 1110, 1.0, outline=WHITE)
    text_center(draw, (330, 1300, 1270, 1370), "EDUCATION CONSULTING", font(FONT_SERIF, 38), GOLD, tracking=5)
    img.save(path)


def save_cover_png(path):
    img = Image.new("RGB", (1920, 1080), NAVY)
    draw = ImageDraw.Draw(img)
    draw.rectangle((56, 56, 1864, 1024), outline=GOLD, width=3)
    draw.rectangle((84, 84, 1836, 996), outline=(255, 255, 255), width=1)
    draw_laurel(draw, 960, 520, 330, "left", scale=1.0, line_color=WHITE)
    draw_laurel(draw, 960, 520, 330, "right", scale=1.0, line_color=WHITE)
    draw_seal(draw, 960, 430, 235, text_color=WHITE, bg=NAVY, scale=.85)
    draw_monogram(draw, 960, 342, .92, color=WHITE, accent=GOLD)
    text_center(draw, (720, 482, 1200, 540), "ANIMETRO", font(FONT_SERIF_BOLD, 44), WHITE, tracking=5)
    text_center(draw, (770, 542, 1150, 595), "CONSULTING", font(FONT_SERIF, 25), GOLD, tracking=5)
    draw_book(draw, 960, 640, .55, outline=WHITE)
    text_center(draw, (250, 740, 1670, 840), "ANIMETRO", font(FONT_SERIF_BOLD, 100), WHITE, tracking=10)
    text_center(draw, (300, 860, 1620, 930), "EDUCATION CONSULTING", font(FONT_SERIF, 45), GOLD, tracking=6)
    text_center(draw, (360, 955, 1560, 1020), "艾美加教育顾问", font(FONT_CHINESE, 44), WHITE)
    img.save(path)


def svg_monogram(symbol_only=False):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640" role="img" aria-labelledby="title desc">
  <title id="title">Animetro A infinity monogram</title>
  <desc id="desc">A clean navy and gold A infinity monogram for Animetro Education Consulting.</desc>
  <rect width="640" height="640" fill="none"/>
  <g fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M190 450 L312 165 L434 450" stroke="{NAVY}" stroke-width="34"/>
    <path d="M242 360 H382" stroke="{NAVY}" stroke-width="24"/>
    <path d="M328 314 C376 246 438 246 486 314 C438 382 376 382 328 314 C280 246 218 246 170 314 C218 382 280 382 328 314 Z" stroke="{GOLD}" stroke-width="25"/>
    <path d="M170 492 H470" stroke="{GOLD}" stroke-width="12"/>
    <circle cx="320" cy="492" r="13" fill="{GOLD}" stroke="none"/>
  </g>
</svg>
'''


def svg_laurel(side="left"):
    if side == "left":
        stem = '<path d="M180 890 C70 710 85 475 225 295" stroke="{gold}" stroke-width="10" fill="none"/>'
        leaves = [(180, 820, -48), (145, 745, -36), (124, 666, -24), (120, 585, -12), (135, 505, 2), (165, 430, 16), (205, 365, 30), (255, 310, 42)]
    else:
        stem = '<path d="M1020 890 C1130 710 1115 475 975 295" stroke="{gold}" stroke-width="10" fill="none"/>'
        leaves = [(1020, 820, 48), (1055, 745, 36), (1076, 666, 24), (1080, 585, 12), (1065, 505, -2), (1035, 430, -16), (995, 365, -30), (945, 310, -42)]
    leaf_markup = "\n".join(
        f'    <ellipse cx="{x}" cy="{y}" rx="18" ry="55" transform="rotate({angle} {x} {y})" fill="{GOLD}" stroke="{NAVY}" stroke-width="3"/>'
        for x, y, angle in leaves
    )
    return f'''  <g>
    {stem.format(gold=GOLD)}
{leaf_markup}
  </g>'''


def svg_book(cx=600, cy=805, scale=1, text=NAVY):
    return f'''  <g transform="translate({cx} {cy}) scale({scale})" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M-12 54 C-70 18 -122 22 -174 38 V-50 C-112 -38 -56 -24 -12 18 Z" fill="{PAPER}" stroke="{GOLD}" stroke-width="8"/>
    <path d="M12 54 C70 18 122 22 174 38 V-50 C112 -38 56 -24 12 18 Z" fill="{PAPER}" stroke="{GOLD}" stroke-width="8"/>
    <path d="M0 56 V16" stroke="{GOLD}" stroke-width="7"/>
    <path d="M-178 58 C-118 72 -60 80 0 58 C60 80 118 72 178 58" stroke="{text}" stroke-width="5"/>
  </g>'''


def svg_primary(bg=None, navy_bg=False):
    bg_rect = f'<rect width="1200" height="1200" fill="{bg}"/>' if bg else '<rect width="1200" height="1200" fill="none"/>'
    text = WHITE if navy_bg else NAVY
    mono = svg_monogram().split("<g", 1)[1].rsplit("</g>", 1)[0]
    inner_fill = NAVY if navy_bg else WHITE
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1200" role="img" aria-labelledby="title desc">
  <title id="title">Animetro Education Consulting primary logo</title>
  <desc id="desc">Primary luxury education consulting crest with laurel wreath, double ring, A infinity monogram, English wordmark, open book, and Chinese brand name.</desc>
  {bg_rect}
{svg_laurel("left")}
{svg_laurel("right")}
  <circle cx="600" cy="565" r="350" fill="{inner_fill}" stroke="{GOLD}" stroke-width="12"/>
  <circle cx="600" cy="565" r="318" fill="none" stroke="{text}" stroke-width="10"/>
  <circle cx="600" cy="565" r="296" fill="none" stroke="{GOLD}" stroke-width="4"/>
  <g transform="translate(280 105) scale(1)"{mono}</g>
  <text x="600" y="715" text-anchor="middle" fill="{text}" font-family="Cinzel, Cormorant Garamond, Trajan Pro, Libre Baskerville, Baskerville, Georgia, serif" font-size="74" font-weight="600" letter-spacing="8">ANIMETRO</text>
  <path d="M350 772 H455 M745 772 H850" stroke="{GOLD}" stroke-width="5"/>
  <text x="600" y="790" text-anchor="middle" fill="{GOLD}" font-family="Cormorant Garamond, Libre Baskerville, Baskerville, Georgia, serif" font-size="34" letter-spacing="8">CONSULTING</text>
{svg_book(600, 890, .55, text)}
  <text x="600" y="1060" text-anchor="middle" fill="{GOLD}" font-family="Cormorant Garamond, Libre Baskerville, Baskerville, Georgia, serif" font-size="34" letter-spacing="6">EDUCATION CONSULTING</text>
  <text x="600" y="1122" text-anchor="middle" fill="{text}" font-family="Noto Serif CJK SC, Songti SC, STSong, serif" font-size="38" letter-spacing="3">艾美加教育顾问</text>
</svg>
'''


def svg_daily_logo(bg=None, navy_bg=False):
    bg_rect = f'<rect width="1200" height="1200" fill="{bg}"/>' if bg else '<rect width="1200" height="1200" fill="none"/>'
    text = WHITE if navy_bg else NAVY
    mono = svg_monogram().split("<g", 1)[1].rsplit("</g>", 1)[0]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1200" role="img" aria-labelledby="title desc">
  <title id="title">Animetro Education Consulting daily logo</title>
  <desc id="desc">Clean daily brand logo with A infinity monogram, English wordmark, and Chinese brand name without the laurel wreath.</desc>
  {bg_rect}
  <g transform="translate(280 85) scale(1)"{mono}</g>
  <text x="600" y="755" text-anchor="middle" fill="{text}" font-family="Cinzel, Cormorant Garamond, Trajan Pro, Libre Baskerville, Baskerville, Georgia, serif" font-size="82" font-weight="600" letter-spacing="9">ANIMETRO</text>
  <text x="600" y="835" text-anchor="middle" fill="{GOLD}" font-family="Cormorant Garamond, Libre Baskerville, Baskerville, Georgia, serif" font-size="34" letter-spacing="7">EDUCATION CONSULTING</text>
  <path d="M380 885 H820" stroke="{GOLD}" stroke-width="4"/>
  <text x="600" y="958" text-anchor="middle" fill="{text}" font-family="Noto Serif CJK SC, Songti SC, STSong, serif" font-size="40" letter-spacing="3">艾美加教育顾问</text>
</svg>
'''


def svg_horizontal():
    mono = svg_monogram().split("<g", 1)[1].rsplit("</g>", 1)[0]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1800 460" role="img" aria-labelledby="title desc">
  <title id="title">Animetro Education Consulting horizontal logo</title>
  <desc id="desc">Horizontal website logo with A infinity monogram, English wordmark, and Chinese brand name.</desc>
  <rect width="1800" height="460" fill="none"/>
  <g transform="translate(40 -62) scale(.72)"{mono}</g>
  <path d="M470 110 V350" stroke="{GOLD}" stroke-width="5"/>
  <text x="560" y="170" fill="{NAVY}" font-family="Cinzel, Cormorant Garamond, Trajan Pro, Libre Baskerville, Baskerville, Georgia, serif" font-size="78" font-weight="600" letter-spacing="8">ANIMETRO</text>
  <text x="563" y="245" fill="{GOLD}" font-family="Cormorant Garamond, Libre Baskerville, Baskerville, Georgia, serif" font-size="35" letter-spacing="6">EDUCATION CONSULTING</text>
  <text x="563" y="326" fill="{NAVY}" font-family="Noto Serif CJK SC, Songti SC, STSong, serif" font-size="42" letter-spacing="3">艾美加教育顾问</text>
</svg>
'''


def svg_seal():
    mono = svg_monogram().split("<g", 1)[1].rsplit("</g>", 1)[0]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" role="img" aria-labelledby="title desc">
  <title id="title">Animetro Education Consulting seal</title>
  <desc id="desc">Circular academic crest with laurel wreath, double ring, A infinity monogram, consulting wordmark, and book symbol.</desc>
  <rect width="1000" height="1000" fill="none"/>
  <g transform="translate(-100 -70) scale(1)">
{svg_laurel("left")}
{svg_laurel("right")}
  </g>
  <circle cx="500" cy="470" r="325" fill="{WHITE}" stroke="{GOLD}" stroke-width="12"/>
  <circle cx="500" cy="470" r="295" fill="none" stroke="{NAVY}" stroke-width="8"/>
  <circle cx="500" cy="470" r="276" fill="none" stroke="{GOLD}" stroke-width="4"/>
  <g transform="translate(180 65) scale(1)"{mono}</g>
  <text x="500" y="602" text-anchor="middle" fill="{NAVY}" font-family="Cinzel, Cormorant Garamond, Libre Baskerville, Baskerville, Georgia, serif" font-size="62" font-weight="600" letter-spacing="7">ANIMETRO</text>
  <path d="M310 650 H390 M610 650 H690" stroke="{GOLD}" stroke-width="5"/>
  <text x="500" y="666" text-anchor="middle" fill="{GOLD}" font-family="Cormorant Garamond, Libre Baskerville, Baskerville, Georgia, serif" font-size="31" letter-spacing="6">CONSULTING</text>
{svg_book(500, 760, .48, NAVY)}
  <text x="500" y="920" text-anchor="middle" fill="{NAVY}" font-family="Noto Serif CJK SC, Songti SC, STSong, serif" font-size="34" letter-spacing="3">艾美加教育顾问</text>
</svg>
'''


def write_svg_assets():
    files = {
        "animetro-monogram.svg": svg_monogram(),
        "animetro-favicon.svg": svg_monogram(),
        "animetro-primary.svg": svg_primary(),
        "animetro-primary-white-bg.svg": svg_primary(PAPER),
        "animetro-primary-navy-bg.svg": svg_primary(NAVY, navy_bg=True),
        "animetro-daily-logo.svg": svg_daily_logo(),
        "animetro-daily-logo-white-bg.svg": svg_daily_logo(WHITE),
        "animetro-daily-logo-navy-bg.svg": svg_daily_logo(NAVY, navy_bg=True),
        "animetro-horizontal.svg": svg_horizontal(),
        "animetro-seal.svg": svg_seal(),
        "animetro-official-seal.svg": svg_seal(),
    }
    for name, data in files.items():
        (BRAND_DIR / name).write_text(data, encoding="utf-8")


def write_guide():
    guide = f"""# Animetro Education Consulting Brand Usage Guide

## Brand Names

- English: ANIMETRO EDUCATION CONSULTING
- Chinese: 艾美加教育顾问

## Brand Systems

This package has two primary systems:

- Official Luxury Seal: laurel wreath, double seal ring, open book, and A∞ monogram. Use for presentations, proposal covers, certificates, premium branding, and executive-facing materials.
- Clean Daily Logo: A∞ monogram with ANIMETRO EDUCATION CONSULTING and the Chinese brand name, without the wreath. Use for website headers, daily documents, email signatures, and compact digital placements.

## Colors

- Navy: `{NAVY}`
- Gold: `{GOLD}`
- Warm paper: `{PAPER}`
- White: `{WHITE}`

## Typography Direction

- English wordmark: Cinzel, Cormorant Garamond, Trajan Pro, Libre Baskerville, Baskerville, Georgia, serif.
- Chinese wordmark: Noto Serif CJK SC, Songti SC, STSong, serif.
- Keep English and Chinese brand versions visually related but do not mix languages in body copy.

## Logo Files

- Master official seal: `animetro-primary.svg`
- Official seal: `animetro-official-seal.svg`
- Clean daily logo: `animetro-daily-logo.svg`
- Horizontal website logo: `animetro-horizontal.svg`
- Monogram icon: `animetro-monogram.svg`
- Academic seal: `animetro-seal.svg`
- Favicon: `animetro-favicon.svg`
- Official seal white background: `animetro-primary-white-bg.svg`
- Official seal navy background: `animetro-primary-navy-bg.svg`
- Daily logo white background: `animetro-daily-logo-white-bg.svg`
- Daily logo navy background: `animetro-daily-logo-navy-bg.svg`

## PNG Exports

- Official seal transparent: `exports/official-seal-transparent.png`
- Official seal white background: `exports/official-seal-white-bg.png`
- Official seal navy background: `exports/official-seal-navy-bg.png`
- Clean daily logo transparent: `exports/daily-logo-transparent.png`
- Clean daily logo white background: `exports/daily-logo-white-bg.png`
- Clean daily logo navy background: `exports/daily-logo-navy-bg.png`
- Website header transparent: `exports/website-header-transparent.png`
- Website header white background: `exports/website-header-white-bg.png`
- Website header navy background: `exports/website-header-navy-bg.png`
- Monogram icon transparent: `exports/animetro-monogram-transparent.png`
- Seal icon transparent: `exports/animetro-seal-transparent.png`
- Print-ready seal: `exports/print-ready-official-seal-transparent-3600.png`
- Favicon PNG: `exports/favicon-512.png`
- Favicon ICO: `exports/favicon.ico`
- Social profile export: `exports/animetro-social-profile.png`
- Presentation cover: `exports/animetro-presentation-cover.png`

## Usage Rules

- Use navy and gold marks on white, paper, or very pale neutral backgrounds.
- Use white and gold marks on navy backgrounds.
- Keep clear space around the seal at least equal to one laurel leaf. Keep clear space around the daily logo at least equal to the height of the infinity loop.
- Do not apply blur, bevels, metallic textures, shadows, gradients, or AI-style painterly effects.
- Do not recolor the monogram outside the approved navy and gold palette.
- Do not add metallic bevels, 3D highlights, drop shadows, or glossy AI-rendered effects to the laurel, ring, book, or monogram.
- Use the horizontal daily logo for website headers and compact digital placements.
- Use the official seal only for formal covers, certificates, profile images, and presentation title pages.
"""
    (BRAND_DIR / "brand-usage-guide.md").write_text(guide, encoding="utf-8")


def write_png_assets():
    save_primary_png(EXPORT_DIR / "animetro-primary-transparent.png")
    save_primary_png(EXPORT_DIR / "animetro-primary-white-bg.png", bg=WHITE)
    save_primary_png(EXPORT_DIR / "animetro-primary-navy-bg.png", bg=NAVY, navy_variant=True)
    save_primary_png(EXPORT_DIR / "official-seal-transparent.png")
    save_primary_png(EXPORT_DIR / "official-seal-white-bg.png", bg=WHITE)
    save_primary_png(EXPORT_DIR / "official-seal-navy-bg.png", bg=NAVY, navy_variant=True)
    save_primary_png(EXPORT_DIR / "print-ready-official-seal-transparent-3600.png", size=3600)
    save_daily_logo_png(EXPORT_DIR / "daily-logo-transparent.png")
    save_daily_logo_png(EXPORT_DIR / "daily-logo-white-bg.png", bg=WHITE)
    save_daily_logo_png(EXPORT_DIR / "daily-logo-navy-bg.png", bg=NAVY, navy_variant=True)
    save_horizontal_png(EXPORT_DIR / "animetro-horizontal-transparent.png")
    save_horizontal_png(EXPORT_DIR / "website-header-transparent.png")
    save_horizontal_png(EXPORT_DIR / "website-header-white-bg.png", bg=WHITE)
    save_horizontal_png(EXPORT_DIR / "website-header-navy-bg.png", bg=NAVY, navy_variant=True)
    save_icon_png(EXPORT_DIR / "animetro-monogram-transparent.png", 1024)
    save_icon_png(EXPORT_DIR / "animetro-seal-transparent.png", 1400, seal=True)
    save_icon_png(EXPORT_DIR / "favicon-512.png", 512)
    favicon = Image.open(EXPORT_DIR / "favicon-512.png")
    favicon.save(EXPORT_DIR / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (128, 128), (256, 256)])
    save_social_png(EXPORT_DIR / "animetro-social-profile.png")
    save_cover_png(EXPORT_DIR / "animetro-presentation-cover.png")


def main():
    ensure_dirs()
    write_svg_assets()
    write_png_assets()
    write_guide()


if __name__ == "__main__":
    main()
