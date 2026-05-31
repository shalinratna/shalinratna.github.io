#!/usr/bin/env python3
"""
Generates Pinterest-optimized vertical images (1000x1500) for every article.
Pinterest drives traffic in weeks, not months. Run this after build_site.py.
"""
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1000, 1500

PALETTES = [
    {"bg": "#0f0f1a", "card": "#1a1a2e", "accent": "#6c63ff", "text": "#ffffff", "sub": "#b0b0cc"},
    {"bg": "#0d1117", "card": "#161b22", "accent": "#58a6ff", "text": "#ffffff", "sub": "#8b949e"},
    {"bg": "#1a0a2e", "card": "#2d1b4e", "accent": "#c084fc", "text": "#ffffff", "sub": "#e9d5ff"},
    {"bg": "#0a1628", "card": "#0f2744", "accent": "#34d399", "text": "#ffffff", "sub": "#a7f3d0"},
    {"bg": "#1a0a0a", "card": "#2d1515", "accent": "#f87171", "text": "#ffffff", "sub": "#fecaca"},
]

def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def get_font(size, bold=False):
    for p in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except:
                pass
    return ImageFont.load_default()

def wrap(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = ' '.join(cur + [w])
        if draw.textbbox((0,0), test, font=font)[2] > max_w and cur:
            lines.append(' '.join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(' '.join(cur))
    return lines

def make_pin(title, description, slug, palette_idx=0):
    p = PALETTES[palette_idx % len(PALETTES)]
    img = Image.new("RGB", (W, H), hex_rgb(p["bg"]))
    draw = ImageDraw.Draw(img)

    # Gradient overlay
    for y in range(H):
        alpha = y / H
        bg = hex_rgb(p["bg"])
        card = hex_rgb(p["card"])
        r = int(bg[0] + (card[0]-bg[0]) * alpha)
        g = int(bg[1] + (card[1]-bg[1]) * alpha)
        b = int(bg[2] + (card[2]-bg[2]) * alpha)
        draw.line([(0,y),(W,y)], fill=(r,g,b))

    # Top accent bar
    draw.rectangle([0, 0, W, 12], fill=hex_rgb(p["accent"]))

    # Site name
    f_site = get_font(28, bold=True)
    draw.text((W//2, 60), "AI Money Tools", font=f_site,
              fill=hex_rgb(p["accent"]), anchor="mm")

    # Decorative elements
    draw.ellipse([W//2-200, 140, W//2+200, 540], fill=hex_rgb(p["card"]))
    draw.ellipse([W//2-180, 160, W//2+180, 520], fill=hex_rgb(p["bg"]))

    # Center icon area - dollar/AI symbol
    f_icon = get_font(120, bold=True)
    draw.text((W//2, 340), "💰", font=f_icon, anchor="mm")

    # Title
    f_title = get_font(52, bold=True)
    lines = wrap(title, f_title, W - 80, draw)
    y = 580
    for line in lines[:4]:
        draw.text((W//2, y), line, font=f_title,
                  fill=hex_rgb(p["text"]), anchor="mm")
        y += 70

    # Divider
    draw.rectangle([W//2-100, y+10, W//2+100, y+16], fill=hex_rgb(p["accent"]))
    y += 50

    # Description teaser
    f_desc = get_font(34)
    desc_short = description[:120] + "..." if len(description) > 120 else description
    desc_lines = wrap(desc_short, f_desc, W - 100, draw)
    for line in desc_lines[:3]:
        draw.text((W//2, y), line, font=f_desc,
                  fill=hex_rgb(p["sub"]), anchor="mm")
        y += 50

    # CTA button
    btn_y = H - 220
    draw.rounded_rectangle([W//2-200, btn_y, W//2+200, btn_y+70],
                            radius=35, fill=hex_rgb(p["accent"]))
    f_btn = get_font(30, bold=True)
    draw.text((W//2, btn_y+35), "Read Full Guide →",
              font=f_btn, fill=(255,255,255), anchor="mm")

    # URL
    f_url = get_font(24)
    draw.text((W//2, H-80), "shalinratna.github.io",
              font=f_url, fill=hex_rgb(p["sub"]), anchor="mm")

    # Bottom accent
    draw.rectangle([0, H-12, W, H], fill=hex_rgb(p["accent"]))

    return img

def generate_all_pins():
    articles_dir = Path("articles")
    pins_dir = Path("pinterest_pins")
    pins_dir.mkdir(exist_ok=True)

    count = 0
    for i, md_file in enumerate(sorted(articles_dir.glob("*.md"))):
        content = md_file.read_text(encoding='utf-8')
        if not content.startswith('---'):
            continue

        parts = content.split('---', 2)
        fm_raw = parts[1]
        fm = {}
        for line in fm_raw.strip().split('\n'):
            if ':' in line:
                k, _, v = line.partition(':')
                fm[k.strip()] = v.strip().strip('"').strip("'")

        title = fm.get('title', '')
        desc = fm.get('description', fm.get('meta', ''))
        slug = fm.get('slug', md_file.stem)

        if not title:
            continue

        pin_path = pins_dir / f"{slug}.png"
        if pin_path.exists():
            continue

        img = make_pin(title, desc, slug, palette_idx=i)
        img.save(str(pin_path), quality=95)
        count += 1
        print(f"Pin created: {slug}.png")

    print(f"\nDone. {count} new Pinterest pins in pinterest_pins/")

if __name__ == "__main__":
    generate_all_pins()
