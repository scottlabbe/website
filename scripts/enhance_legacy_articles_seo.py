#!/usr/bin/env python3
"""Add SEO metadata to legacy article HTML pages that lack modern tags."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "articles"

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
CANONICAL_RE = re.compile(
    r'<link\s+rel="canonical"\s+href="([^"]+)"\s*/?>',
    re.IGNORECASE,
)
PUBLISHED_RE = re.compile(r"Published on\s+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def to_plain_text(source: str) -> str:
    no_style = re.sub(r"<style\b[^>]*>.*?</style>", " ", source, flags=re.IGNORECASE | re.DOTALL)
    no_script = re.sub(r"<script\b[^>]*>.*?</script>", " ", no_style, flags=re.IGNORECASE | re.DOTALL)
    text = TAG_RE.sub(" ", no_script)
    return WS_RE.sub(" ", text).strip()


def summarize(text: str, max_len: int = 160) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def extract_content_fragment(page: str) -> str:
    body_start = page.lower().find("<body")
    body_html = page[body_start:] if body_start >= 0 else page

    article_match = re.search(r"<article\b[^>]*>(.*?)</article>", body_html, flags=re.IGNORECASE | re.DOTALL)
    if article_match:
        return article_match.group(1)

    div_blocks = re.findall(r"<div\b[^>]*>.*?</div>", body_html, flags=re.IGNORECASE | re.DOTALL)
    if div_blocks:
        return max(div_blocks, key=len)

    return body_html


def insert_metadata(page: str) -> str | None:
    if "<!doctype html>" in page.lower():
        return None

    title_match = TITLE_RE.search(page)
    canonical_match = CANONICAL_RE.search(page)
    if not title_match or not canonical_match:
        return None

    title = WS_RE.sub(" ", title_match.group(1)).strip()
    canonical = canonical_match.group(1).strip()
    published_match = PUBLISHED_RE.search(page)
    published = published_match.group(1) if published_match else ""

    content_fragment = extract_content_fragment(page)
    description_plain = to_plain_text(content_fragment)
    description_plain = re.sub(r"^Home\s+Articles\s+Videos\s+", "", description_plain, flags=re.IGNORECASE)
    description = summarize(description_plain)

    json_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "author": {"@type": "Person", "name": "Scott Labbe"},
        "mainEntityOfPage": canonical,
        "url": canonical,
        "publisher": {"@type": "Person", "name": "Scott Labbe"},
    }
    if published:
        json_ld["datePublished"] = published
        json_ld["dateModified"] = published

    published_meta = f'\n  <meta name="article:published" content="{published}" />' if published else ""
    metadata = (
        f'\n  <meta name="description" content="{html.escape(description, quote=True)}" />'
        f"{published_meta}\n"
        '  <meta property="og:type" content="article" />\n'
        f'  <meta property="og:title" content="{html.escape(title, quote=True)}" />\n'
        f'  <meta property="og:description" content="{html.escape(description, quote=True)}" />\n'
        f'  <meta property="og:url" content="{html.escape(canonical, quote=True)}" />\n'
        '  <meta property="og:site_name" content="Scott Labbe" />\n'
        '  <meta name="twitter:card" content="summary" />\n'
        f'  <meta name="twitter:title" content="{html.escape(title, quote=True)}" />\n'
        f'  <meta name="twitter:description" content="{html.escape(description, quote=True)}" />\n'
        f'  <script type="application/ld+json">{json.dumps(json_ld)}</script>'
    )

    cleanup_patterns = [
        r'\s*<meta name="description" content="[^"]*"\s*/?>',
        r'\s*<meta name="article:published" content="[^"]*"\s*/?>',
        r'\s*<meta property="og:type" content="[^"]*"\s*/?>',
        r'\s*<meta property="og:title" content="[^"]*"\s*/?>',
        r'\s*<meta property="og:description" content="[^"]*"\s*/?>',
        r'\s*<meta property="og:url" content="[^"]*"\s*/?>',
        r'\s*<meta property="og:site_name" content="[^"]*"\s*/?>',
        r'\s*<meta name="twitter:card" content="[^"]*"\s*/?>',
        r'\s*<meta name="twitter:title" content="[^"]*"\s*/?>',
        r'\s*<meta name="twitter:description" content="[^"]*"\s*/?>',
        r'\s*<script type="application/ld\+json">\{.*?"@type": "Article".*?\}</script>',
    ]
    cleaned = page
    for pattern in cleanup_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)

    canonical_match = CANONICAL_RE.search(cleaned)
    if canonical_match:
        insert_at = canonical_match.end()
        return cleaned[:insert_at] + metadata + cleaned[insert_at:]

    head_close = HEAD_CLOSE_RE.search(cleaned)
    if not head_close:
        return None
    return cleaned[: head_close.start()] + metadata + "\n" + cleaned[head_close.start() :]


def main() -> None:
    updated = 0
    for html_path in sorted(ARTICLES_DIR.glob("*/index.html")):
        content = html_path.read_text(encoding="utf-8")
        new_content = insert_metadata(content)
        if new_content is None:
            continue
        html_path.write_text(new_content, encoding="utf-8")
        updated += 1
        print(f"Updated {html_path.relative_to(ROOT)}")

    print(f"Updated {updated} legacy article page(s).")


if __name__ == "__main__":
    main()
