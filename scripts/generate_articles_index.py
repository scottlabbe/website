#!/usr/bin/env python3
"""Generate /articles/index.html from article pages in /articles/*/index.html.

Usage:
  python scripts/generate_articles_index.py
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "articles"
OUT = ROOT / "articles" / "index.html"
SITE = "https://scottlabbe.me"

H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", flags=re.IGNORECASE | re.DOTALL)
PUBLISHED_RE = re.compile(r'class="published">\s*Published on\s*([^<]+)<', flags=re.IGNORECASE)
CREATED_RE = re.compile(r'class="created">\s*Created on\s*([^<]+)<', flags=re.IGNORECASE)
META_PUBLISHED_RE = re.compile(r'name="article:published"\s+content="([^"]+)"', flags=re.IGNORECASE)
META_STATUS_RE = re.compile(r'name="article:status"\s+content="([^"]+)"', flags=re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")

def parse_dt(s: str) -> dt.datetime:
    if not s:
        return dt.datetime.min
    try:
        return dt.datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")
    except Exception:
        pass
    try:
        return dt.datetime.strptime(s.strip(), "%Y-%m-%d")
    except Exception:
        return dt.datetime.min

def fmt_date(d: dt.datetime) -> str:
    if d == dt.datetime.min:
        return "Unknown"
    # Avoid %-d portability issues
    return d.strftime("%b %d, %Y").replace(" 0", " ")


def summarize_title(title: str) -> str:
    base = f"Articles by Scott Labbe on AI automation, auditing workflows, and Medicaid program operations. Latest posts are listed first."
    if len(base) <= 160:
        return base
    return base[:157] + "..."

def extract_meta(html: str) -> tuple[str, str, str, str]:
    h1m = H1_RE.search(html)
    title = TAG_RE.sub("", h1m.group(1)).strip() if h1m else "(Untitled)"
    pubm = PUBLISHED_RE.search(html)
    crem = CREATED_RE.search(html)
    meta_pubm = META_PUBLISHED_RE.search(html)
    meta_status = META_STATUS_RE.search(html)
    published = pubm.group(1).strip() if pubm else ""
    if not published and meta_pubm:
        published = meta_pubm.group(1).strip()
    created = crem.group(1).strip() if crem else ""
    status = meta_status.group(1).strip().lower() if meta_status else "published"
    return title, created, published, status

def main() -> None:
    items = []
    for p in sorted(ARTICLES_DIR.glob("*/index.html")):
        slug = p.parent.name
        if slug in {"data"} or slug.startswith("."):
            continue
        html = p.read_text(encoding="utf-8", errors="ignore")
        title, created, published, status = extract_meta(html)
        if status == "draft":
            continue
        published_dt = parse_dt(published)
        if published_dt == dt.datetime.min:
            published_dt = dt.datetime.fromtimestamp(p.stat().st_mtime)
        items.append({
            "file": str(p),
            "slug": slug,
            "title": title,
            "created": created,
            "published": published,
            "published_dt": published_dt,
        })

    items.sort(key=lambda x: x["published_dt"], reverse=True)

    rows = []
    for it in items:
        rows.append(f"""<li>
  <div><a href="/articles/{it['slug']}/">{it['title']}</a></div>
  <div class="small">Published {fmt_date(it['published_dt'])}</div>
</li>""")
    rows_html = "\n".join(rows)
    canonical = f"{SITE}/articles/"
    description = summarize_title("Articles")
    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": "Articles",
            "description": description,
            "url": canonical,
        }
    )

    page = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Articles — Scott Labbe</title>
  <meta name=\"description\" content=\"{description}\" />
  <link rel=\"canonical\" href=\"{canonical}\" />
  <meta property=\"og:type\" content=\"website\" />
  <meta property=\"og:title\" content=\"Articles — Scott Labbe\" />
  <meta property=\"og:description\" content=\"{description}\" />
  <meta property=\"og:url\" content=\"{canonical}\" />
  <meta property=\"og:site_name\" content=\"Scott Labbe\" />
  <meta name=\"twitter:card\" content=\"summary\" />
  <meta name=\"twitter:title\" content=\"Articles — Scott Labbe\" />
  <meta name=\"twitter:description\" content=\"{description}\" />
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
  <link href=\"https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap\" rel=\"stylesheet\">
  <link rel=\"stylesheet\" href=\"/assets/css/main.css\" />
  <script type=\"application/ld+json\">{json_ld}</script>
</head>
<body>
  <div class=\"container\">
    <header>
      <h1>Articles</h1>
      <nav aria-label=\"Primary\">
        <a href=\"/\">Home</a>
        <a href=\"/videos/\">Videos</a>
      </nav>
    </header>

    <main>
      <p class=\"small\">Newest first.</p>

      <ul style=\"list-style:none; padding:0; margin:2rem 0 0;\">
        {rows_html}
      </ul>
    </main>

    <footer>
      © <span id=\"y\"></span> Scott Labbe
    </footer>
  </div>

  <script>document.getElementById('y').textContent = new Date().getFullYear();</script>
</body>
</html>
"""

    OUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUT} with {len(items)} article(s).")

if __name__ == "__main__":
    main()
