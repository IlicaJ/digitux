#!/usr/bin/env python3
"""Generador de ilustraciones estilizadas (cartoon plano) para DigiTux v2.

Carcasa redondeada + placa + nombre + perillas. Los amplificadores usan un color
por estilo (ámbar, plata, británico, oscuro, moderno), los pedales por categoría.
Arte 100% propio.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC = Path(__file__).parent / "nexus" / "rp360_effects.json"
OUT = Path(__file__).parent / "nexus" / "assets" / "img"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_COND_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"

# Tamaños de lienzo (lo que la UI escala/espera)
PEDAL_W, PEDAL_H = 220, 364
AMP_W, AMP_H = 572, 194            # fuente; la UI lo muestra más grande (640x217)
CAB_W, CAB_H = 200, 200

# --- paleta por categoría (pedales) ---
CAT_COLOR = {
    "Wah":        (201, 94, 26),
    "Compressor": (96, 160, 90),
    "Distortion": (178, 58, 47),
    "Amplifier":  (70, 72, 78),
    "EQ":         (180, 140, 60),
    "Gate":       (56, 70, 88),
    "Mod":        (95, 175, 185),
    "Delay":      (58, 140, 130),
    "Reverb":     (88, 150, 120),
    "Other":      (120, 120, 120),
}

MOD_COLOR = {
    "Chorus":   (95, 175, 185),
    "Flanger":  (120, 120, 200),
    "Phaser":   (170, 120, 200),
    "VibRot":   (160, 90, 160),
    "Tremolo":  (150, 150, 200),
    "EnvSpec":  (90, 170, 130),
    "PitchFX":  (200, 130, 90),
}

CAB_COLOR = (120, 90, 60)

# --- clasificación de amplificadores por estilo (color del chasis) ---
AMP_STYLE_COLOR = {
    "Amber":  (176, 130, 35),     # ámbar dorado
    "Silver": (168, 172, 178),    # gris plata
    "Brit":   (78, 120, 150),     # azul británico
    "Dark":   (52, 52, 50),       # negro
    "Modern": (52, 90, 150),      # azul DigiTux
}

# address → estilo (por grupos técnicos de amplificador)
STYLE_AMBER = {"45 JTM", "68 PLEXI", "JUMPPANL", "MASTRVOL", "800 JCM", "900 JCM", "2000 JCM"}
STYLE_SILVER = {"57 CHAMP", "57DELUXE", "59BASSMN", "62BASSMN", "65 TWIN", "65DLUXRV"}
STYLE_BRIT = {"AC15", "AC30 TB", "HIWATTAG"}
STYLE_DARK = {"MARK IIC", "MARK IV", "DUALRECT", "TRIPRECT", "22CALIBR"}


def amp_style(address):
    if address in STYLE_AMBER:
        return "Amber"
    if address in STYLE_SILVER:
        return "Silver"
    if address in STYLE_BRIT:
        return "Brit"
    if address in STYLE_DARK:
        return "Dark"
    if address.startswith("DIG") or address.startswith("2101"):
        return "Modern"
    return None  # color neutro por defecto


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def darker(color, amt=40):
    return tuple(max(0, c - amt) for c in color)


def draw_knobs(d, cx, cy, r, n, label_font, labels=None):
    """Dibuja n perillas pequeñas apiladas/espaciadas con puntero dorado."""
    for i in range(n):
        x = cx[i] if isinstance(cx, list) else cx
        y = cy[i] if isinstance(cy, list) else cy
        d.ellipse([x - r, y - r, x + r, y + r], fill=(43, 43, 43), outline=(18, 18, 18), width=2)
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 196, 90))
        if labels and i < len(labels):
            b = d.textbbox((0, 0), labels[i], font=label_font)
            d.text((x - (b[2] - b[0]) / 2, y + r + 4), labels[i], font=label_font, fill=(225, 225, 225))


def make_pedal(name, cat, sub):
    color = MOD_COLOR.get(sub, CAT_COLOR[cat]) if cat == "Mod" else CAT_COLOR.get(cat, (120, 120, 120))
    im = Image.new("RGBA", (PEDAL_W, PEDAL_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # carcasa
    d.rounded_rectangle([20, 16, PEDAL_W - 20, PEDAL_H - 24], radius=22,
                        fill=color, outline=(35, 35, 35), width=4)
    d.rounded_rectangle([20, 16, PEDAL_W - 20, PEDAL_H - 24], radius=22,
                        outline=darker(color), width=8)
    # placa de controles OSCURA (zona de perillas) para que las etiquetas blancas resalten
    d.rounded_rectangle([30, 34, PEDAL_W - 30, 172], radius=12,
                        fill=(42, 42, 46), outline=(90, 90, 95), width=2)
    # nombre en la zona inferior del chasis, hasta 2 líneas
    f_name = font(FONT_COND_BOLD, 24)
    max_w = PEDAL_W - 60
    # partir en líneas que quepan
    lines = wrap_text(d, name, f_name, max_w, max_lines=2)
    y0 = 200
    lh = 26
    for i, line in enumerate(lines):
        bbox = d.textbbox((0, 0), line, font=f_name)
        tw = bbox[2] - bbox[0]
        tx = (PEDAL_W - tw) / 2
        yy = y0 + i * lh
        d.text((tx + 1, yy + 1), line, font=f_name, fill=(15, 15, 15, 150))
        d.text((tx, yy), line, font=f_name, fill=(235, 235, 235))
    return im


def wrap_text(d, text, f, max_w, max_lines=2):
    """Divide `text` en hasta `max_lines` líneas que quepan en `max_w` px."""
    words = text.split()
    if not words:
        return [text]
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        bbox = d.textbbox((0, 0), trial, font=f)
        if bbox[2] - bbox[0] <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines - 1:
                break
    if cur:
        lines.append(cur)
    # si aún sobra texto tras el límite, agrega el resto a la última línea con ...
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines[:max_lines] if lines else [text]


def make_amp(name, address):
    style = amp_style(address)
    color = AMP_STYLE_COLOR.get(style) if style else (70, 72, 78)
    im = Image.new("RGBA", (AMP_W, AMP_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # carcasa
    d.rounded_rectangle([14, 12, AMP_W - 14, AMP_H - 12], radius=20,
                        fill=color, outline=(30, 30, 30), width=4)
    d.rounded_rectangle([14, 12, AMP_W - 14, AMP_H - 12], radius=20,
                        outline=darker(color, 45), width=8)
    # placa dorada compacta (solo el nombre, arriba)
    d.rounded_rectangle([20, 22, 360, 78], radius=12,
                        fill=(224, 192, 112), outline=(150, 120, 60), width=3)
    # nombre grabado
    f_name = font(FONT_COND_BOLD, 34 if len(name) <= 16 else 28)
    bbox = d.textbbox((0, 0), name, font=f_name)
    tw = bbox[2] - bbox[0]
    tx = 20 + (340 - tw) / 2
    d.text((tx + 2, 36), name, font=f_name, fill=(95, 62, 20, 160))
    d.text((tx, 34), name, font=f_name, fill=(58, 38, 10))
    return im


def make_cab(name):
    im = Image.new("RGBA", (CAB_W, CAB_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 40, CAB_W - 20, CAB_H - 20], radius=10,
                        fill=CAB_COLOR, outline=(40, 28, 15), width=4)
    inner = (CAB_COLOR[0] - 25, CAB_COLOR[1] - 20, CAB_COLOR[2] - 10)
    d.rectangle([28, 56, CAB_W - 28, CAB_H - 44], fill=inner, outline=(30, 20, 10), width=2)
    # número de bocinas según el nombre (1x, 2x, 4x)
    import re
    m = re.match(r"(\d+)x", name)
    n_speakers = int(m.group(1)) if m else 1
    speaker = (48, 46, 42)
    rim = (20, 18, 16)
    crust = (200, 196, 188)
    if n_speakers <= 1:
        x0, y0 = 48, 80
        d.ellipse([x0, y0, x0 + 104, y0 + 104], fill=speaker, outline=rim, width=3)
        d.ellipse([x0 + 12, y0 + 12, x0 + 92, y0 + 92], outline=crust, width=2)
    elif n_speakers == 2:
        for cx in (40, 116):
            d.ellipse([cx, 80, cx + 60, 140], fill=speaker, outline=rim, width=3)
            d.ellipse([cx + 7, 87, cx + 53, 133], outline=crust, width=2)
    else:  # 4 bocinas (2x2)
        for cx in (40, 112):
            for cy in (70, 122):
                d.ellipse([cx, cy, cx + 48, cy + 48], fill=speaker, outline=rim, width=2)
                d.ellipse([cx + 6, cy + 6, cx + 42, cy + 42], outline=crust, width=2)
    f_name = font(FONT_REG, 13)
    bbox = d.textbbox((0, 0), name, font=f_name)
    tw = bbox[2] - bbox[0]
    d.text(((CAB_W - tw) / 2, CAB_H - 20), name, font=f_name, fill=(230, 225, 210))
    return im


def main():
    data = json.load(open(SRC))
    out_pedals = OUT / "pedals"
    out_amps = OUT / "amps"
    out_cabs = OUT / "cabs"
    for p in (out_pedals, out_amps, out_cabs):
        p.mkdir(parents=True, exist_ok=True)

    n = 0
    for e in data["effects"]:
        cat = e["category"]
        name = e["displayName"]
        addr = e["address"]
        fn = e.get("image") or ""
        base = Path(fn).name if fn else f"{addr}.png"
        if cat == "Amplifier":
            im = make_amp(name, addr)
            im.save(out_amps / base)
        else:
            if cat == "Other":
                name = "Volume"
            im = make_pedal(name, cat, e.get("subcategory"))
            im.save(out_pedals / base)
        n += 1

    for c in data["cabinets"]:
        fn = c.get("image") or ""
        base = Path(fn).name if fn else f"cab_{c.get('id')}.png"
        im = make_cab(c["displayName"])
        im.save(out_cabs / base)
        n += 1

    print(f"generadas {n} ilustraciones")


if __name__ == "__main__":
    main()