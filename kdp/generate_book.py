#!/usr/bin/env python3
"""
Generates full Amazon KDP ebooks automatically.
One book per week. You upload Saturday morning. Takes 5 min.
$9.99/book × 70% royalty = $7/sale. 20 sales/month = $140/book passive forever.
"""
import json, re, subprocess
from datetime import datetime
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont

OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2:3b"
BOOKS_DIR = Path("kdp/books")
COVERS_DIR = Path("kdp/covers")
EPUB_DIR = Path("kdp/epub")

BOOK_TOPICS = [
    {"title": "ChatGPT for Personal Finance: The Complete Beginner's Guide", "subtitle": "Use AI to Budget, Invest, and Build Wealth in 2025", "keywords": "chatgpt finance, ai budgeting, chatgpt money, ai investing beginner"},
    {"title": "The AI Side Hustle Bible", "subtitle": "50 Ways to Make Money Online Using AI Tools in 2025", "keywords": "ai side hustle, make money ai, chatgpt side hustle, ai income"},
    {"title": "30 Days to Financial Freedom with AI", "subtitle": "A Step-by-Step Guide to Using ChatGPT to Transform Your Money", "keywords": "financial freedom ai, chatgpt budget, ai wealth building, 30 day money"},
    {"title": "AI Investing for Beginners", "subtitle": "How to Use Artificial Intelligence to Make Smarter Investment Decisions", "keywords": "ai investing, chatgpt investing, ai stock market, artificial intelligence finance"},
    {"title": "The Lazy Person's Guide to Passive Income with AI", "subtitle": "Build Income Streams That Run Themselves Using ChatGPT and AI Tools", "keywords": "passive income ai, chatgpt passive income, ai make money, automated income"},
    {"title": "ChatGPT Prompts for Financial Success", "subtitle": "500 Proven Prompts to Budget, Invest, Negotiate, and Build Wealth", "keywords": "chatgpt prompts finance, chatgpt money prompts, ai financial prompts"},
    {"title": "Quit Your Job in 12 Months Using AI", "subtitle": "The Realistic Blueprint for Building an AI-Powered Income That Replaces Your Salary", "keywords": "quit job ai, replace salary ai, ai income business, financial freedom"},
    {"title": "The AI Debt Destroyer", "subtitle": "How to Use ChatGPT to Pay Off Debt Faster Than You Ever Thought Possible", "keywords": "ai debt payoff, chatgpt debt, ai pay off debt, debt free ai"},
    {"title": "Make Money While You Sleep with AI", "subtitle": "Building Automated Income Streams Using the Latest AI Tools", "keywords": "passive income ai 2025, automated money ai, ai income streams, make money sleeping"},
    {"title": "AI Tools for Small Business Owners", "subtitle": "Cut Costs, Increase Revenue, and Run Your Business Smarter with Artificial Intelligence", "keywords": "ai small business, chatgpt business, ai business tools, small business automation"},
]

CHAPTER_PROMPT = """Write chapter {chapter_num} of a book called "{title}".
Chapter title: {chapter_title}

Write 1,200-1,500 words. This is a practical, helpful book for everyday people.
- Use conversational but professional tone
- Include specific examples, step-by-step instructions, and real actionable advice
- Include at least one numbered or bulleted list
- Start with an engaging opening, not "In this chapter"
- End with a chapter summary of 3-4 key takeaways
- Make it genuinely useful — real advice, not filler

Write the chapter now:"""

OUTLINE_PROMPT = """Create a detailed book outline for: "{title}"
Subtitle: "{subtitle}"

The book should be practical, actionable, and genuinely helpful.

Reply in this exact format:
DESCRIPTION: [150-word back cover description — compelling, benefit-focused]
CHAPTER_1: [Chapter title]
CHAPTER_2: [Chapter title]
CHAPTER_3: [Chapter title]
CHAPTER_4: [Chapter title]
CHAPTER_5: [Chapter title]
CHAPTER_6: [Chapter title]
CHAPTER_7: [Chapter title]
CHAPTER_8: [Chapter title]
CHAPTER_9: [Chapter title]
CHAPTER_10: [Chapter title]

Generate the outline now:"""

def call_ollama(prompt, tokens=2000):
    r = requests.post(f"{OLLAMA_URL}/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": False,
              "options": {"temperature": 0.7, "num_predict": tokens}},
        timeout=300)
    return r.json()["response"]

def make_cover(book, out_path):
    W, H = 1600, 2560
    img = Image.new("RGB", (W, H), (8, 8, 20))
    draw = ImageDraw.Draw(img)

    # Gradient
    colors = [(8,8,20), (20,15,50), (15,10,35)]
    third = H // 3
    for y in range(H):
        seg = min(y // third, 1)
        c1, c2 = colors[seg], colors[seg+1]
        r = int(c1[0] + (c2[0]-c1[0]) * (y % third) / third)
        g = int(c1[1] + (c2[1]-c1[1]) * (y % third) / third)
        b = int(c1[2] + (c2[2]-c1[2]) * (y % third) / third)
        draw.line([(0,y),(W,y)], fill=(r,g,b))

    def font(size, bold=False):
        for p in [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc"]:
            if Path(p).exists():
                try: return ImageFont.truetype(p, size)
                except: pass
        return ImageFont.load_default()

    # Accent bars
    draw.rectangle([0, 0, W, 20], fill=(108, 99, 255))
    draw.rectangle([0, H-20, W, H], fill=(108, 99, 255))

    # Icon area
    draw.ellipse([W//2-250, 180, W//2+250, 680], fill=(20, 18, 55))
    f_icon = font(280, True)
    draw.text((W//2, 430), "💰", font=f_icon, anchor="mm")

    # Title
    title_words = book["title"].split(":")
    main_title = title_words[0].strip()
    f_title = font(110 if len(main_title) < 30 else 85, True)

    def wrap(text, f, max_w):
        words = text.split()
        lines, cur = [], []
        for w in words:
            test = ' '.join(cur + [w])
            if draw.textbbox((0,0), test, font=f)[2] > max_w and cur:
                lines.append(' '.join(cur)); cur = [w]
            else: cur.append(w)
        if cur: lines.append(' '.join(cur))
        return lines

    y = 780
    for line in wrap(main_title.upper(), f_title, W-120):
        draw.text((W//2, y), line, font=f_title, fill=(255,255,255), anchor="mm")
        y += 130

    # Subtitle
    if len(title_words) > 1:
        f_sub = font(52)
        for line in wrap(title_words[1].strip(), f_sub, W-160):
            draw.text((W//2, y+20), line, font=f_sub, fill=(180,180,220), anchor="mm")
            y += 65

    # Divider
    draw.rectangle([W//2-150, y+40, W//2+150, y+46], fill=(108, 99, 255))

    # Author line
    f_auth = font(55)
    draw.text((W//2, H-120), "AI Money Tools", font=f_auth, fill=(108,99,255), anchor="mm")

    img.save(str(out_path), quality=95)

def generate_epub(book_data, out_path):
    """Build a clean HTML-based epub without requiring ebooklib."""
    title = book_data["title"]
    author = "AI Money Tools"
    chapters = book_data["chapters"]
    description = book_data["description"]

    # Write as a simple combined HTML file (can be converted to EPUB with Calibre)
    html_path = out_path.with_suffix('.html')
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>{title}</title>
<style>
body {{ font-family: Georgia, serif; max-width: 700px; margin: 0 auto; padding: 40px 20px; line-height: 1.8; color: #222; }}
h1 {{ color: #1a1a2e; font-size: 2em; margin-bottom: 10px; }}
h2 {{ color: #1a1a2e; font-size: 1.5em; margin-top: 50px; border-bottom: 2px solid #6c63ff; padding-bottom: 8px; }}
h3 {{ color: #333; font-size: 1.2em; margin-top: 30px; }}
p {{ margin-bottom: 16px; }}
ul, ol {{ margin: 16px 0 16px 24px; }}
li {{ margin-bottom: 8px; }}
.subtitle {{ color: #666; font-size: 1.2em; font-style: italic; margin-bottom: 30px; }}
.author {{ color: #888; margin-bottom: 60px; }}
.chapter {{ page-break-before: always; margin-top: 60px; }}
</style>
</head><body>
<h1>{title}</h1>
<p class="subtitle">{book_data.get('subtitle', '')}</p>
<p class="author">By {author}</p>
<hr/>
<h2>About This Book</h2>
<p>{description}</p>
"""
    for i, ch in enumerate(chapters):
        html += f"""<div class="chapter">
<h2>Chapter {i+1}: {ch['title']}</h2>
{ch['content'].replace(chr(10), '</p><p>')}
</div>
"""
    html += "</body></html>"
    html_path.write_text(html, encoding='utf-8')

    # Try to convert to EPUB with Calibre if available
    if subprocess.run(['which', 'ebook-convert'], capture_output=True).returncode == 0:
        subprocess.run(['ebook-convert', str(html_path), str(out_path),
                       '--title', title, '--authors', author,
                       '--book-producer', 'AI Money Tools'],
                      capture_output=True)
        html_path.unlink(missing_ok=True)
    else:
        out_path.with_suffix('.html').rename(out_path)

    return out_path

def main():
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    EPUB_DIR.mkdir(parents=True, exist_ok=True)

    # Pick next ungenerated book
    used = [p.stem for p in EPUB_DIR.glob("*.epub") ] + [p.stem for p in EPUB_DIR.glob("*.html")]
    book = next((b for b in BOOK_TOPICS
                 if re.sub(r'[^a-z0-9]', '-', b["title"].lower())[:40] not in ' '.join(used)), None)

    if not book:
        print("All books generated!")
        return

    slug = re.sub(r'[^a-z0-9]', '-', book["title"].lower())[:50]
    print(f"\nGenerating book: {book['title']}")

    # Get outline
    print("  Creating outline...")
    raw_outline = call_ollama(OUTLINE_PROMPT.format(**book), 800)
    chapters = []
    description = ""
    for line in raw_outline.split('\n'):
        s = line.strip()
        if s.startswith("DESCRIPTION:"):
            description = s[12:].strip()
        for i in range(1, 11):
            if s.startswith(f"CHAPTER_{i}:"):
                chapters.append({"title": s[len(f"CHAPTER_{i}:"):].strip(), "content": ""})

    if not chapters:
        chapters = [{"title": f"Chapter {i+1}", "content": ""} for i in range(10)]

    # Generate each chapter
    for i, ch in enumerate(chapters):
        print(f"  Chapter {i+1}/{len(chapters)}: {ch['title'][:50]}...")
        content = call_ollama(CHAPTER_PROMPT.format(
            chapter_num=i+1, title=book["title"], chapter_title=ch["title"]), 2000)
        ch["content"] = content

    # Build book data
    book_data = {**book, "slug": slug, "description": description,
                 "chapters": chapters, "date": datetime.now().strftime("%Y-%m-%d")}

    # Save metadata
    (BOOKS_DIR / f"{slug}.json").write_text(json.dumps(book_data, indent=2))

    # Generate cover
    cover_path = COVERS_DIR / f"{slug}.jpg"
    print("  Creating cover...")
    make_cover(book, cover_path)

    # Generate EPUB
    epub_path = EPUB_DIR / f"{slug}.epub"
    print("  Building EPUB...")
    generate_epub(book_data, epub_path)

    # Copy to iCloud
    icloud = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/KDP Books"
    icloud.mkdir(exist_ok=True)
    import shutil
    final_epub = list(EPUB_DIR.glob(f"{slug}*"))[0]
    shutil.copy(final_epub, icloud / f"{book['title'][:60]}.{final_epub.suffix[1:]}")
    shutil.copy(cover_path, icloud / f"{book['title'][:60]}_COVER.jpg")

    print(f"\n  DONE: {book['title']}")
    print(f"  Files in iCloud Drive → 'KDP Books' folder")
    print(f"  Upload at: kdp.amazon.com")
    print(f"  Price: $9.99 | Royalty: ~$7/sale")

if __name__ == "__main__":
    main()
