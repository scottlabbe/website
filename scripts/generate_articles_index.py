#!/usr/bin/env python3
"""Generate /articles/index.html from the HTML files in /articles/data/Articles.

Usage:
  python scripts/generate_articles_index.py
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "articles" / "data" / "Articles"
OUT = ROOT / "articles" / "index.html"

H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", flags=re.IGNORECASE | re.DOTALL)
PUBLISHED_RE = re.compile(r'class="published">\s*Published on\s*([^<]+)<', flags=re.IGNORECASE)
CREATED_RE = re.compile(r'class="created">\s*Created on\s*([^<]+)<', flags=re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")

# Map legacy filenames to clean slugs. Files not listed here are skipped.
SLUG_MAP = {
    "why-accurate-context-matters-more-than-clever-prompting-labbe-cpa.html": "why-accurate-context-matters-more-than-clever-prompting",
    "validate-review-reimburse-automating-desk-reviews-ai-part-labbe-cpa-r60ue.html": "validate-review-reimburse",
    "tiny-ai-tools-big-wins-automating-cost-report-your-scott-labbe-cpa-qhgde.html": "tiny-ai-tools-big-wins",
    "ai-structure-make-institutional-memory-searchable-scott-labbe-cpa-zbuce.html": "ai-structure-make-institutional-memory-searchable",
    "i-spent-hours-learning-python-automate-task-ai-agent-did-labbe-cpa-dvy5c.html": "i-spent-hours-learning-python",
    "most-dangerous-question-ai-accurate-scott-labbe-cpa-7bwve.html": "most-dangerous-question",
    "unlocking-institutional-memory-ai-reimagining-audit-scott-labbe-cpa-j0mje.html": "unlocking-institutional-memory",
    "test-trust-making-ai-work-you-scott-labbe-cpa-teebe.html": "test-it-to-trust-it",
    "from-routine-remarkable-automating-template-creation-ai-labbe-cpa-c3foe.html": "automating-template-creation",
    "pdfs-complicated-making-documents-work-ai-tools-scott-labbe-cpa-djkqe.html": "pdfs-are-complicated",
    "building-reliable-data-pipelines-ai-tools-using-scott-labbe-cpa-ymztc.html": "building-reliable-data-pipelines",
    "using-googles-notebooklm-transform-medicaid-audit-full-labbe-cpa-tkmoe.html": "notebooklm-medicaid-audits",
    "experimenting-gpt-4os-image-extraction-capabilities-ai-labbe-cpa-82ede.html": "gpt-4o-image-extraction",
    "from-manual-automatic-how-ai-python-can-automate-data-labbe-cpa-gogic.html": "from-manual-to-automatic",
    "beyond-summarize-crafting-simple-effective-ai-prompt-audit-scott-tjyre.html": "beyond-summarize",
    "from-pdf-insight-leveraging-ai-streamline-audit-scott-labbe-cpa-gjgve.html": "from-pdf-to-insight",
}

def parse_dt(s: str) -> dt.datetime:
    try:
        return dt.datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")
    except Exception:
        return dt.datetime.min

def fmt_date(d: dt.datetime) -> str:
    # Avoid %-d portability issues
    return d.strftime("%b %d, %Y").replace(" 0", " ")

def extract_meta(html: str) -> tuple[str, str, str]:
    h1m = H1_RE.search(html)
    title = TAG_RE.sub("", h1m.group(1)).strip() if h1m else "(Untitled)"
    pubm = PUBLISHED_RE.search(html)
    crem = CREATED_RE.search(html)
    published = pubm.group(1).strip() if pubm else ""
    created = crem.group(1).strip() if crem else ""
    return title, created, published

def main() -> None:
    items = []
    for p in sorted(ARTICLES_DIR.glob("*.html")):
        slug = SLUG_MAP.get(p.name)
        if not slug:
            continue
        html = p.read_text(encoding="utf-8", errors="ignore")
        title, created, published = extract_meta(html)
        published_dt = parse_dt(published)
        items.append({
            "file": p.name,
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

    page = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Articles — Scott Labbe</title>
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
  <link href=\"https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap\" rel=\"stylesheet\">
  <link rel=\"stylesheet\" href=\"/assets/css/main.css\" />
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
