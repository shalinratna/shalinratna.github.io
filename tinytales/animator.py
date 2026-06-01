#!/usr/bin/env python3
"""
Animation engine for Tiny Tales.
Handles: slam, typewriter, bounce, slide, flash, shake, zoom.
All frame-by-frame with numpy — fast enough for M4 Max.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

W, H = 1080, 1920
FPS  = 30

def font(size, bold=False):
    for p in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if Path(p).exists():
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def wrap(text, fnt, max_w, draw):
    words = text.split()
    lines, cur = [], []
    for w in words:
        if draw.textbbox((0,0),' '.join(cur+[w]),font=fnt)[2] > max_w and cur:
            lines.append(' '.join(cur)); cur=[w]
        else: cur.append(w)
    if cur: lines.append(' '.join(cur))
    return lines

# ── Background generators ─────────────────────────────────────────

def gradient_bg(theme, t=0, w=W, h=H):
    """Animated gradient background."""
    img = np.zeros((h,w,3), dtype=np.uint8)
    c1, c2 = np.array(theme["bg1"]), np.array(theme["bg2"])
    acc = np.array(theme["accent"])
    pulse = 0.4 + 0.4*np.sin(t * 1.2)
    gx = int(w*0.5 + np.sin(t*0.4)*w*0.25)
    gy = int(h*0.35 + np.cos(t*0.3)*h*0.12)
    Y, X = np.ogrid[:h, :w]
    p = Y/h
    base = (c1*(1-p[:,:,None]) + c2*(p[:,:,None])).astype(float)
    dist = np.sqrt((X-gx)**2 + (Y-gy)**2)
    glow = np.exp(-dist**2/(2*(w*0.38)**2)) * pulse
    for i in range(3):
        img[:,:,i] = np.clip(base[:,:,i] + glow*acc[i]*0.35, 0, 255)
    return img

def particles(base_img, t, acc_color, count=60):
    """Add floating particles to a background array."""
    rng = np.random.default_rng(int(t*100) % 9999)
    img = base_img.copy()
    speeds = rng.uniform(0.4, 1.4, count)
    px = (rng.random(count)*W).astype(int)
    py = ((rng.random(count)*H - t*35*speeds) % H).astype(int)
    sizes = rng.integers(2, 7, count)
    brightness = rng.integers(80, 180, count)
    for i in range(count):
        x,y,r = px[i],py[i],sizes[i]
        b = brightness[i]/255
        c = tuple(int(acc_color[j]*b) for j in range(3))
        y1,y2 = max(0,y-r),min(H,y+r)
        x1,x2 = max(0,x-r),min(W,x+r)
        img[y1:y2,x1:x2] = np.clip(img[y1:y2,x1:x2].astype(int)+np.array(c),0,255)
    return img

# ── Text animation helpers ────────────────────────────────────────

def slam_text(draw, text, cx, cy, scale, fnt, color=(255,255,255), shadow=True):
    """Draw text at a given scale (1.0=normal, >1=zoomed in)."""
    actual_size = int(fnt.size * scale)
    f = font(actual_size, bold=True)
    lines = wrap(text, f, int((W-80)/scale), draw)
    y = cy - (len(lines)*int(actual_size*1.3))//2
    for line in lines:
        if shadow:
            draw.text((cx+3, y+3), line, font=f, fill=(0,0,0), anchor="mm")
        draw.text((cx, y), line, font=f, fill=color, anchor="mm")
        y += int(actual_size * 1.35)

def typewriter_text(draw, text, cx, cy, progress, fnt, color=(255,255,255)):
    """Show text typed out to 'progress' (0.0-1.0)."""
    chars = int(len(text) * progress)
    partial = text[:chars] + ("▌" if progress < 1.0 else "")
    lines = wrap(partial, fnt, W-80, draw)
    y = cy - (len(lines)*75)//2
    for line in lines:
        draw.text((cx+2, y+2), line, font=fnt, fill=(0,0,0), anchor="mm")
        draw.text((cx, y), line, font=fnt, fill=color, anchor="mm")
        y += 75

def slide_in_y(draw, text, cx, target_y, offset_y, fnt, color=(255,255,255)):
    """Text slides in from offset_y to target_y."""
    y = target_y + int(offset_y)
    lines = wrap(text, fnt, W-80, draw)
    y -= (len(lines)*72)//2
    for line in lines:
        draw.text((cx+2, y+2), line, font=fnt, fill=(0,0,0), anchor="mm")
        draw.text((cx, y), line, font=fnt, fill=color, anchor="mm")
        y += 72

# ── Easing ────────────────────────────────────────────────────────

def ease_out(t): return 1-(1-t)**3
def ease_in(t): return t**2
def ease_bounce(t):
    if t < 0.364: return 7.5625*t*t
    elif t < 0.727: t-=0.545; return 7.5625*t*t+0.75
    elif t < 0.909: t-=0.818; return 7.5625*t*t+0.9375
    else: t-=0.955; return 7.5625*t*t+0.984375

# ── Frame sequence builders ───────────────────────────────────────

def hook_sequence(hook_text, emoji, theme, n_frames=45):
    """
    3-part hook: flash → slam text → hold.
    Total: ~1.5 seconds. Grabs attention immediately.
    """
    frames = []
    acc = theme["accent"]

    for i in range(n_frames):
        t = i/n_frames
        bg = gradient_bg(theme, i*0.05)
        bg = particles(bg, i*0.05, acc)
        img = Image.fromarray(bg)
        draw = ImageDraw.Draw(img)

        # Flash (frames 0-6)
        if i < 6:
            flash_alpha = int(255 * (1 - i/6))
            flash = Image.new("RGB", (W,H), acc)
            img = Image.blend(img, flash, flash_alpha/255)
            draw = ImageDraw.Draw(img)

        # Big emoji drops in (frames 4-20)
        if i >= 4:
            ep = ease_bounce(min(1.0, (i-4)/16))
            ey = int(H*0.38 - (1-ep)*H*0.4)
            f_em = font(int(200 + 30*(1-ep)), bold=True)
            draw.text((W//2, ey), emoji, font=f_em, anchor="mm")

        # Hook text slams in (frames 18-35)
        if i >= 18:
            tp = ease_out(min(1.0, (i-18)/17))
            scale = 2.0 - tp*1.0  # 2.0 → 1.0
            alpha_c = tuple(int(c*tp) for c in (255,255,255))
            slam_text(draw, hook_text, W//2, int(H*0.7),
                     scale, font(72, bold=True), color=alpha_c)

        # "WAIT..." tag
        if i >= 30:
            ta = ease_out(min(1.0, (i-30)/10))
            f_tag = font(40, bold=True)
            badge_w = draw.textbbox((0,0), "👀 WAIT FOR IT...", font=f_tag)[2]+40
            bx = W//2 - badge_w//2
            draw.rounded_rectangle([bx, H*3//4+40, bx+badge_w, H*3//4+95],
                                   radius=25, fill=acc)
            draw.text((W//2, H*3//4+67), "👀 WAIT FOR IT...",
                     font=f_tag, fill=(20,15,30), anchor="mm")

        # Progress bar
        draw.rectangle([0, H-8, int(W*t), H], fill=acc)
        frames.append(np.array(img))

    return frames

def title_sequence(title, c1, c2, ep_num, theme, n_frames=60):
    """Characters bounce in, title slams. ~2 seconds."""
    frames = []
    acc = theme["accent"]

    for i in range(n_frames):
        t = i/n_frames
        bg = gradient_bg(theme, i*0.06)
        bg = particles(bg, i*0.06, acc)
        img = Image.fromarray(bg)
        draw = ImageDraw.Draw(img)

        # Top bar
        draw.rectangle([0,0,W,8], fill=acc)

        # "TINY TALES" header
        f_show = font(52, bold=True)
        draw.text((W//2, 75), "✨ TINY TALES ✨", font=f_show, fill=acc, anchor="mm")

        # Character 1 slides in from left
        if i >= 5:
            p1 = ease_out(min(1.0, (i-5)/20))
            x1 = int(-200 + p1*(W//3+200))
            bob1 = int(np.sin(i*0.3)*12)
            f_em = font(180)
            draw.text((x1, H//2 - 80 + bob1), c1["emoji"], font=f_em, anchor="mm")

        # Character 2 slides in from right
        if i >= 10:
            p2 = ease_out(min(1.0, (i-10)/20))
            x2 = int(W+200 - p2*(W - 2*W//3 + 200))
            bob2 = int(np.sin(i*0.3+1)*12)
            f_em = font(180)
            draw.text((x2, H//2 - 80 + bob2), c2["emoji"], font=f_em, anchor="mm")

        # "+" pops in
        if i >= 20:
            pp = ease_bounce(min(1.0, (i-20)/12))
            ps = 0.5 + pp*0.5
            f_plus = font(int(90*ps), bold=True)
            draw.text((W//2, H//2 - 80), "+", font=f_plus, fill=acc, anchor="mm")

            # Character names
            f_n = font(38, bold=True)
            draw.text((W//3, H//2 + 80), c1["name"], font=f_n, fill=(220,220,240), anchor="mm")
            draw.text((2*W//3, H//2 + 80), c2["name"], font=f_n, fill=(220,220,240), anchor="mm")

        # Title slams in
        if i >= 32:
            tp = ease_out(min(1.0, (i-32)/18))
            sc = 1.6 - tp*0.6
            slam_text(draw, title, W//2, int(H*0.72), sc,
                     font(68, bold=True), color=(255,255,255))

        # Episode badge
        if i >= 45:
            ep = ease_out(min(1.0, (i-45)/10))
            f_ep = font(34)
            draw.text((W//2, H-95), f"Episode {ep_num} ⭐",
                     font=f_ep, fill=tuple(int(c*ep) for c in acc), anchor="mm")

        draw.rectangle([0,H-8,W,H], fill=acc)
        frames.append(np.array(img))

    return frames

def dialogue_sequence(text, speaker, emoji, theme, audio_dur, is_speaker1=True):
    """Animated dialogue slide. Text types in, character bounces."""
    n = max(FPS*2, int(audio_dur*FPS))
    frames = []
    acc = theme["accent"]
    f_text = font(64, bold=True) if len(text) < 50 else font(52, bold=True)
    f_name = font(40, bold=True)
    f_narrator = font(44)
    is_narrator = speaker == "NARRATOR"

    for i in range(n):
        t = i/FPS
        prog = i/n

        bg = gradient_bg(theme, t+hash(speaker)%10)
        bg = particles(bg, t, acc, count=40)
        img = Image.fromarray(bg)
        draw = ImageDraw.Draw(img)

        draw.rectangle([0,0,W,8], fill=acc)

        if is_narrator:
            # Narrator: book emoji + typing text
            f_em = font(160)
            bob = int(np.sin(t*4)*8)
            draw.text((W//2, H//3 - 20 + bob), "📖", font=f_em, anchor="mm")

            # "NARRATOR" label
            f_nl = font(36, bold=True)
            nw = draw.textbbox((0,0),"✨ NARRATOR ✨",font=f_nl)[2]+40
            draw.rounded_rectangle([W//2-nw//2, H//3+110, W//2+nw//2, H//3+163],
                                   radius=20, fill=acc)
            draw.text((W//2, H//3+136), "✨ NARRATOR ✨",
                     font=f_nl, fill=(20,15,30), anchor="mm")

            # Typing text
            type_p = min(1.0, prog*2.5)
            typewriter_text(draw, text, W//2, int(H*0.68), type_p, f_narrator)
        else:
            # Character: big emoji bounces, speech bubble appears
            bounce = int(np.sin(t*8)*18)
            f_em = font(200)
            draw.text((W//2, H//3 - 30 + bounce), emoji, font=f_em, anchor="mm")

            # Character name badge
            nw = draw.textbbox((0,0), speaker, font=f_name)[2]+50
            bx = W//2-nw//2
            draw.rounded_rectangle([bx, H//3+120, bx+nw, H//3+175],
                                   radius=28, fill=acc)
            draw.text((W//2, H//3+147), speaker,
                     font=f_name, fill=(20,15,30), anchor="mm")

            # Speech bubble
            if prog > 0.1:
                slide_p = ease_out(min(1.0, (prog-0.1)*4))
                offset_y = (1-slide_p) * 120

                lines = wrap(text, f_text, W-100, draw)
                total_h = len(lines)*85+50
                by = int(H*0.58 + offset_y)

                # Bubble
                draw.rounded_rectangle([40, by, W-40, by+total_h],
                                      radius=25, fill=(255,255,255,0) if False else (30,25,45))
                # Pointer
                draw.polygon([(W//2-20, by),(W//2+20, by),(W//2, by-22)],
                            fill=(30,25,45))
                # Text
                ty = by+25
                for line in lines:
                    alpha_c = tuple(int(c * slide_p) for c in (255,255,255))
                    draw.text((W//2+2, ty+2), line, font=f_text, fill=(0,0,0), anchor="mm")
                    draw.text((W//2, ty), line, font=f_text, fill=alpha_c, anchor="mm")
                    ty += 85

        # Progress bar
        draw.rectangle([0, H-8, int(W*prog), H], fill=acc)
        # CTA
        f_cta = font(32)
        draw.text((W//2, H-50), "Follow Tiny Tales! ✨",
                 font=f_cta, fill=tuple(int(c*0.7) for c in acc), anchor="mm")

        frames.append(np.array(img))

    return frames

def lesson_sequence(lesson, theme, n_frames=75):
    """Lesson card with heart animation. ~2.5 seconds."""
    frames = []
    acc = theme["accent"]

    for i in range(n_frames):
        t = i/FPS
        bg = gradient_bg(theme, t+20)
        bg = particles(bg, t+20, acc, count=80)
        img = Image.fromarray(bg)
        draw = ImageDraw.Draw(img)

        draw.rectangle([0,0,W,8], fill=acc)

        # "TODAY'S LESSON" header drops in
        if i >= 5:
            p = ease_bounce(min(1.0, (i-5)/18))
            f_head = font(48, bold=True)
            draw.text((W//2, int(H*0.3 - (1-p)*200)), "⭐ TODAY'S LESSON ⭐",
                     font=f_head, fill=acc, anchor="mm")

        # Heart pulses
        if i >= 20:
            pulse = 1.0 + 0.15*np.sin(t*6)
            f_heart = font(int(160*pulse))
            draw.text((W//2, int(H*0.5)), "💛", font=f_heart, anchor="mm")

        # Lesson text types in
        if i >= 28:
            tp = min(1.0, (i-28)/30)
            f_les = font(58, bold=True)
            typewriter_text(draw, lesson, W//2, int(H*0.68), tp, f_les)

        # CTA slides in
        if i >= 55:
            cp = ease_out(min(1.0, (i-55)/15))
            f_cta1 = font(40, bold=True)
            f_cta2 = font(34)
            draw.text((W//2, int(H*0.85)),
                     "Share with someone you love 🥰",
                     font=f_cta1, fill=tuple(int(c*cp) for c in (255,255,255)), anchor="mm")
            draw.text((W//2, int(H*0.91)),
                     "Follow for a new story every day! ✨",
                     font=f_cta2, fill=tuple(int(c*cp) for c in acc), anchor="mm")

        draw.rectangle([0, H-8, W, H], fill=acc)
        frames.append(np.array(img))

    return frames
