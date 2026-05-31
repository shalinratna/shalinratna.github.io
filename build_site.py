#!/usr/bin/env python3
import json
import re
import markdown2
from datetime import datetime
from pathlib import Path

SITE_NAME = "AI Money Tools"
SITE_URL = "https://shalinratna.github.io"
SITE_DESCRIPTION = "Free guides on using AI tools to save money, earn more, and work smarter."
ADSENSE_ID = "ca-pub-1674705461176233"
AMAZON_TAG = ""  # Set to your Amazon Associates tag e.g. "aimoneytools-20"

# Auto-affiliate: keywords → Amazon search links (injected into articles)
AFFILIATE_LINKS = {
    "YNAB": "https://www.amazon.com/s?k=ynab+budget+book&tag=AMZN_TAG",
    "ChatGPT": "https://www.amazon.com/s?k=chatgpt+book+guide&tag=AMZN_TAG",
    "budgeting": "https://www.amazon.com/s?k=personal+finance+budget+planner&tag=AMZN_TAG",
    "investing": "https://www.amazon.com/s?k=investing+for+beginners+book&tag=AMZN_TAG",
    "passive income": "https://www.amazon.com/s?k=passive+income+book&tag=AMZN_TAG",
    "credit score": "https://www.amazon.com/s?k=improve+credit+score+guide&tag=AMZN_TAG",
    "retirement": "https://www.amazon.com/s?k=retirement+planning+book&tag=AMZN_TAG",
    "side hustle": "https://www.amazon.com/s?k=side+hustle+ideas+book&tag=AMZN_TAG",
    "freelancing": "https://www.amazon.com/s?k=freelancing+guide+book&tag=AMZN_TAG",
    "dropshipping": "https://www.amazon.com/s?k=dropshipping+guide&tag=AMZN_TAG",
}

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #ffffff; --text: #1a1a2e; --muted: #555770;
  --accent: #6c63ff; --light: #f8f8ff; --border: #e5e5f0;
  --max: 780px; --font: 'Segoe UI', system-ui, sans-serif;
}
body { font-family: var(--font); color: var(--text); background: var(--bg); line-height: 1.7; font-size: 17px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

header { background: var(--text); padding: 16px 24px; position: sticky; top: 0; z-index: 100; }
nav { max-width: 1100px; margin: 0 auto; display: flex; align-items: center; gap: 24px; }
.logo { font-size: 1.2rem; font-weight: 700; color: #fff; }
nav a:not(.logo) { color: rgba(255,255,255,0.75); font-size: 0.9rem; }
nav a:not(.logo):hover { color: #fff; text-decoration: none; }

.hero { background: linear-gradient(135deg, var(--text) 0%, #2d2b55 100%); color: #fff; padding: 72px 24px; text-align: center; }
.hero h1 { font-size: 2.6rem; font-weight: 800; margin-bottom: 16px; line-height: 1.2; }
.hero p { font-size: 1.15rem; opacity: 0.85; max-width: 560px; margin: 0 auto; }

.container { max-width: 1100px; margin: 0 auto; padding: 0 24px; }
.section-title { font-size: 1.5rem; font-weight: 700; margin: 56px 0 28px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; margin-bottom: 56px; }
.card { border: 1px solid var(--border); border-radius: 12px; padding: 24px; transition: box-shadow 0.2s; }
.card:hover { box-shadow: 0 4px 20px rgba(108,99,255,0.12); }
.card-date { font-size: 0.8rem; color: var(--muted); margin-bottom: 8px; }
.card h2 { font-size: 1.05rem; font-weight: 600; margin-bottom: 10px; line-height: 1.4; }
.card p { font-size: 0.9rem; color: var(--muted); line-height: 1.6; }
.card-tags { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 6px; }
.tag { background: var(--light); border: 1px solid var(--border); border-radius: 99px; padding: 3px 10px; font-size: 0.75rem; color: var(--muted); }
.read-more { display: inline-block; margin-top: 14px; font-size: 0.85rem; font-weight: 600; color: var(--accent); }

.article-page { max-width: var(--max); margin: 56px auto; padding: 0 24px 80px; }
.article-page h1 { font-size: 2rem; font-weight: 800; line-height: 1.3; margin-bottom: 12px; }
.article-meta { color: var(--muted); font-size: 0.875rem; margin-bottom: 40px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }
.article-page h2 { font-size: 1.35rem; font-weight: 700; margin: 40px 0 16px; color: var(--text); }
.article-page h3 { font-size: 1.1rem; font-weight: 600; margin: 28px 0 12px; }
.article-page p { margin-bottom: 20px; }
.article-page ul, .article-page ol { margin: 16px 0 20px 24px; }
.article-page li { margin-bottom: 8px; }
.article-page blockquote { background: var(--light); border-left: 4px solid var(--accent); padding: 16px 20px; margin: 28px 0; border-radius: 0 8px 8px 0; }
.article-page blockquote p { margin: 0; font-style: normal; color: var(--text); }
.article-page table { width: 100%; border-collapse: collapse; margin: 24px 0; font-size: 0.9rem; }
.article-page th { background: var(--text); color: #fff; padding: 10px 14px; text-align: left; }
.article-page td { padding: 10px 14px; border-bottom: 1px solid var(--border); }
.article-page tr:nth-child(even) td { background: var(--light); }
.article-page code { background: var(--light); padding: 2px 6px; border-radius: 4px; font-size: 0.85em; }

.ad-slot { background: var(--light); border: 1px dashed var(--border); border-radius: 8px; padding: 24px; text-align: center; margin: 32px 0; color: var(--muted); font-size: 0.85rem; }

.static-page { max-width: var(--max); margin: 56px auto; padding: 0 24px 80px; }
.static-page h1 { font-size: 2rem; font-weight: 800; margin-bottom: 32px; }
.static-page h2 { font-size: 1.25rem; font-weight: 700; margin: 32px 0 12px; }
.static-page p { margin-bottom: 16px; color: var(--muted); }

footer { background: var(--text); color: rgba(255,255,255,0.6); text-align: center; padding: 32px 24px; font-size: 0.85rem; }
.tools-box { background: var(--light); border: 1px solid var(--border); border-left: 4px solid var(--accent); border-radius: 8px; padding: 20px 24px; margin: 32px 0; }
.tools-box-title { font-weight: 700; font-size: 1rem; margin-bottom: 12px; color: var(--text); }
.tools-box ul { margin-left: 16px; }
.tools-box li { margin-bottom: 8px; font-size: 0.9rem; }
.kofi-box { text-align: center; margin: 24px 0; padding: 16px; background: #fff4e6; border-radius: 8px; border: 1px solid #ffe0b2; }
.kofi-box a { color: #ff5722; font-weight: 600; font-size: 0.95rem; }
footer a { color: rgba(255,255,255,0.6); }
footer a:hover { color: #fff; }

@media (max-width: 600px) {
  .hero h1 { font-size: 1.8rem; }
  .grid { grid-template-columns: 1fr; }
}
"""

def read_article(filepath):
    content = filepath.read_text(encoding='utf-8')
    if not content.startswith('---'):
        return {}, content
    parts = content.split('---', 2)
    fm_raw, body = parts[1], parts[2].strip()
    fm = {}
    for line in fm_raw.strip().split('\n'):
        if ':' in line:
            k, _, v = line.partition(':')
            v = v.strip().strip('"').strip("'")
            if v.startswith('['):
                try: v = json.loads(v)
                except: pass
            fm[k.strip()] = v
    return fm, body

def to_html(md):
    return markdown2.markdown(md, extras=["fenced-code-blocks", "tables", "header-ids", "strike"])

def head(title, desc, url, canonical=None):
    adsense = f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_ID}" crossorigin="anonymous"></script>' if ADSENSE_ID else ''
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical or url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<link rel="stylesheet" href="/assets/style.css">
{adsense}
</head>"""

def nav_html():
    return f"""<header>
<nav>
  <a href="/" class="logo">{SITE_NAME}</a>
  <a href="/">Home</a>
  <a href="/about.html">About</a>
</nav>
</header>"""

def footer_html():
    return f"""<footer>
<p>&copy; {datetime.now().year} {SITE_NAME} &nbsp;|&nbsp; <a href="/privacy.html">Privacy Policy</a> &nbsp;|&nbsp; <a href="/about.html">About</a></p>
<p style="margin-top:8px">Information on this site is for educational purposes only. Not financial advice.</p>
</footer>"""

def build_article_page(fm, body_html, depth="../../"):
    title = fm.get('title', 'Article')
    desc = fm.get('description', fm.get('meta', ''))
    slug = fm.get('slug', '')
    date = fm.get('date', '')
    tags = fm.get('tags', [])
    url = f"{SITE_URL}/articles/{slug}/"
    tag_html = ''.join(f'<span class="tag">{t}</span>' for t in (tags if isinstance(tags, list) else []))

    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": desc,
        "datePublished": date,
        "publisher": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL}
    })

    ad_slot = '<ins class="adsbygoogle" style="display:block" data-ad-client="{}" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>'.format(ADSENSE_ID) if ADSENSE_ID else ''

    tools_box = """<div class="tools-box">
  <div class="tools-box-title">🔧 Recommended Tools</div>
  <ul>
    <li><a href="https://www.amazon.com/s?k=personal+finance+book&tag={tag}" target="_blank" rel="noopener">Top Personal Finance Books on Amazon</a></li>
    <li><a href="https://www.amazon.com/s?k=ai+productivity+tools&tag={tag}" target="_blank" rel="noopener">Best AI Productivity Gadgets</a></li>
    <li><a href="https://www.amazon.com/s?k=budget+planner+notebook&tag={tag}" target="_blank" rel="noopener">Budget Planners &amp; Journals</a></li>
  </ul>
</div>""".format(tag=AMAZON_TAG or "aimoneytools-20") if AMAZON_TAG else ""

    kofi = '<div class="kofi-box"><a href="https://ko-fi.com/aimoneytools" target="_blank" rel="noopener">☕ Found this helpful? Buy me a coffee</a></div>'

    h = head(f"{title} | {SITE_NAME}", desc, url)
    h = h.replace('rel="stylesheet" href="/assets/style.css"', f'rel="stylesheet" href="{depth}assets/style.css"')

    return f"""{h}
<body>
{nav_html()}
<main class="article-page">
  <h1>{title}</h1>
  <div class="article-meta"><time datetime="{date}">{date}</time>{' &nbsp;|&nbsp; ' + tag_html if tag_html else ''}</div>
  {ad_slot}
  {body_html}
  {tools_box}
  {kofi}
  {ad_slot}
</main>
{footer_html()}
<script type="application/ld+json">{schema}</script>
</body>
</html>"""

def build_index(articles):
    cards = ""
    for a in articles[:60]:
        fm, _ = a
        title = fm.get('title', '')
        desc = fm.get('description', fm.get('meta', ''))[:120]
        slug = fm.get('slug', '')
        date = fm.get('date', '')
        tags = fm.get('tags', [])
        tag_html = ''.join(f'<span class="tag">{t}</span>' for t in (tags[:3] if isinstance(tags, list) else []))
        cards += f"""
<div class="card">
  <div class="card-date">{date}</div>
  <h2><a href="/articles/{slug}/">{title}</a></h2>
  <p>{desc}</p>
  <div class="card-tags">{tag_html}</div>
  <a class="read-more" href="/articles/{slug}/">Read guide &rarr;</a>
</div>"""

    return f"""{head(SITE_NAME + " — AI Tools for Money & Productivity", SITE_DESCRIPTION, SITE_URL)}
<body>
{nav_html()}
<div class="hero">
  <h1>Use AI to Save Money &amp; Work Smarter</h1>
  <p>Free, practical guides on using AI tools to budget better, earn more, and get more done every day.</p>
</div>
<div class="container">
  <div class="section-title">Latest Guides</div>
  <div class="grid">{cards}</div>
</div>
{footer_html()}
</body>
</html>"""

def build_about():
    return f"""{head("About | " + SITE_NAME, "Learn about " + SITE_NAME + " and our mission to help you use AI to improve your finances.", SITE_URL + "/about.html")}
<body>
{nav_html()}
<div class="static-page">
  <h1>About {SITE_NAME}</h1>
  <p>{SITE_NAME} is a free resource dedicated to helping everyday people use AI tools to make smarter financial decisions, save more money, and work more efficiently.</p>
  <h2>What We Cover</h2>
  <p>We publish practical, no-fluff guides on using tools like ChatGPT, Claude, and other AI assistants to budget, invest, earn more income, and automate tedious tasks.</p>
  <h2>Who This Is For</h2>
  <p>Anyone who wants to use AI practically — whether you're trying to pay off debt, start a side hustle, or just stop wasting money every month.</p>
  <h2>Contact</h2>
  <p>Questions or suggestions? The best way to reach us is through our contact form (coming soon).</p>
</div>
{footer_html()}
</body>
</html>"""

def build_privacy():
    today = datetime.now().strftime("%B %d, %Y")
    return f"""{head("Privacy Policy | " + SITE_NAME, "Privacy policy for " + SITE_NAME, SITE_URL + "/privacy.html")}
<body>
{nav_html()}
<div class="static-page">
  <h1>Privacy Policy</h1>
  <p><em>Last updated: {today}</em></p>
  <h2>Information We Collect</h2>
  <p>This website uses Google Analytics and Google AdSense, which may collect anonymized usage data such as pages visited, time on site, and general location. We do not collect personal information directly.</p>
  <h2>Cookies</h2>
  <p>Google AdSense and Analytics use cookies to serve relevant ads and analyze traffic. You can disable cookies in your browser settings at any time.</p>
  <h2>Third-Party Advertising</h2>
  <p>We use Google AdSense to display advertisements. Google may use cookies to serve ads based on your prior visits to this website or other websites. You can opt out at <a href="https://www.google.com/settings/ads">Google Ads Settings</a>.</p>
  <h2>Affiliate Links</h2>
  <p>Some links on this site may be affiliate links. We may earn a small commission if you click and make a purchase, at no extra cost to you.</p>
  <h2>Disclaimer</h2>
  <p>Content on this site is for educational purposes only and does not constitute financial advice. Always consult a qualified professional before making financial decisions.</p>
  <h2>Contact</h2>
  <p>Questions about this policy? Contact us through the About page.</p>
</div>
{footer_html()}
</body>
</html>"""

def build_sitemap(articles):
    urls = [SITE_URL + "/", SITE_URL + "/about.html", SITE_URL + "/privacy.html"]
    for fm, _ in articles:
        slug = fm.get('slug', '')
        date = fm.get('date', datetime.now().strftime("%Y-%m-%d"))
        if slug:
            urls.append((SITE_URL + f"/articles/{slug}/", date))

    items = ""
    for url in urls:
        if isinstance(url, tuple):
            items += f"  <url><loc>{url[0]}</loc><lastmod>{url[1]}</lastmod><changefreq>monthly</changefreq></url>\n"
        else:
            items += f"  <url><loc>{url}</loc><changefreq>weekly</changefreq></url>\n"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}</urlset>"""

def main():
    articles_dir = Path("articles")
    docs_dir = Path("docs")
    docs_articles = docs_dir / "articles"
    docs_assets = docs_dir / "assets"

    docs_articles.mkdir(parents=True, exist_ok=True)
    docs_assets.mkdir(parents=True, exist_ok=True)

    (docs_assets / "style.css").write_text(CSS)

    articles = []
    for md_file in sorted(articles_dir.glob("*.md"), reverse=True):
        fm, body = read_article(md_file)
        if fm.get('slug'):
            articles.append((fm, body))

    print(f"Building site with {len(articles)} articles...")

    for fm, body in articles:
        slug = fm.get('slug', '')
        html_body = to_html(body)
        page = build_article_page(fm, html_body)
        article_dir = docs_articles / slug
        article_dir.mkdir(exist_ok=True)
        (article_dir / "index.html").write_text(page, encoding='utf-8')

    (docs_dir / "index.html").write_text(build_index(articles), encoding='utf-8')
    (docs_dir / "about.html").write_text(build_about(), encoding='utf-8')
    (docs_dir / "privacy.html").write_text(build_privacy(), encoding='utf-8')
    (docs_dir / "sitemap.xml").write_text(build_sitemap(articles), encoding='utf-8')
    (docs_dir / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

    print(f"Site built → docs/ ({len(articles)} articles)")

if __name__ == "__main__":
    main()
