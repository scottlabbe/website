#!/usr/bin/env python3
"""Add SEO metadata to legacy article HTML pages that lack modern tags."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "articles"
SITE_NAME = "Scott Labbe"
TITLE_SEPARATOR = " | "
SUMMARY_OVERRIDES: dict[str, str] = {
    "ai-structure-make-institutional-memory-searchable": (
        "A practical framework for turning scattered documents into structured institutional memory teams can search, trust, and reuse."
    ),
    "automating-template-creation": (
        "How a small amount of coding plus AI can automate repetitive template creation and free up time for higher-value analysis."
    ),
    "beyond-summarize": (
        "How to write focused prompts that produce useful audit analysis instead of generic summaries, with a reusable structure you can adapt quickly."
    ),
    "building-reliable-data-pipelines": (
        "How to pair AI extraction with Python and Pydantic validation so document pipelines stay accurate, testable, and production-ready."
    ),
    "from-manual-to-automatic": (
        "How I automated spreadsheet data extraction with Python and AI to reduce manual copy-paste work and improve reporting consistency."
    ),
    "from-pdf-to-insight": (
        "A simple workflow that converts audit-report PDFs into structured data and actionable insights using AI-assisted extraction."
    ),
    "i-spent-hours-learning-python": (
        "A real example of how an AI coding agent completed in 60 seconds a Python automation task that took hours to do manually."
    ),
    "most-dangerous-question": (
        "Why asking only 'Is it accurate?' is risky, and how precision, recall, and risk-based evaluation lead to safer AI decisions."
    ),
    "notebooklm-medicaid-audits": (
        "An experiment using NotebookLM to turn Medicaid audit reports into accessible audio insights and faster policy research workflows."
    ),
    "pdfs-are-complicated": (
        "Why PDF structure breaks naive AI extraction, and practical techniques to improve reliability when processing complex government documents."
    ),
    "test-it-to-trust-it": (
        "A practical method for piloting AI in business workflows: test against real tasks, measure outcomes, and scale only what proves reliable."
    ),
    "tiny-ai-tools-big-wins": (
        "A practical walkthrough for auditors and program managers to build a local AI-assisted tool that extracts cost report data in minutes."
    ),
    "unlocking-institutional-memory": (
        "How audit teams can structure legacy reports into searchable findings and recommendations to unlock institutional knowledge at scale."
    ),
    "validate-review-reimburse": (
        "How AI coding agents can automate desk review validation, adjustments, and reimbursement-ready outputs for government program workflows."
    ),
    "why-accurate-context-matters-more-than-clever-prompting": (
        "Why strong context engineering beats clever prompting when building reliable AI tools for repetitive audit and program management work."
    ),
}

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


def first_paragraph_text(source: str) -> str:
    m = re.search(r"<p\b[^>]*>(.*?)</p>", source, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    return to_plain_text(m.group(1))


def finalize_summary(text: str) -> str:
    text = WS_RE.sub(" ", text).strip(" \n\t\r-").rstrip(" ,;:-")
    if text and text[-1] not in ".!?":
        text += "."
    return text


def summarize(text: str, max_len: int = 160) -> str:
    text = WS_RE.sub(" ", text).strip(" \n\t\r-")
    if len(text) <= max_len:
        return finalize_summary(text)
    sentence_end = text.rfind(". ", 100, max_len + 1)
    if sentence_end != -1:
        return finalize_summary(text[: sentence_end + 1])
    clipped = text[:max_len].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return finalize_summary(clipped)


def sentence_based_summary(text: str, max_len: int = 160) -> str:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    if not parts:
        return ""
    chosen: list[str] = []
    for part in parts:
        candidate = " ".join(chosen + [part]).strip()
        if len(candidate) <= max_len:
            chosen.append(part)
        else:
            break
    combined = " ".join(chosen).strip()
    if len(combined) >= 90:
        return finalize_summary(combined)
    first = parts[0]
    if 70 <= len(first) <= max_len:
        return finalize_summary(first)
    return ""


def fallback_summary(title: str) -> str:
    _ = title
    base = (
        "Practical AI automation insights from Scott Labbe on audit workflows, "
        "data extraction, and government program operations."
    )
    return summarize(base)


def excerpt_summary(text: str, max_words: int = 24) -> str:
    words = [w for w in text.split() if w]
    if not words:
        return ""
    excerpt = " ".join(words[:max_words])
    if excerpt and excerpt[-1] not in ".!?":
        excerpt += "."
    return summarize(excerpt)


def strip_site_suffix(title: str) -> str:
    return re.sub(r"\s*\|\s*Scott Labbe\s*$", "", title, flags=re.IGNORECASE).strip()


def unescape_fully(value: str) -> str:
    current = value
    while True:
        decoded = html.unescape(current)
        if decoded == current:
            return decoded
        current = decoded


def slug_from_canonical(canonical: str) -> str:
    return canonical.rstrip("/").split("/")[-1]


def format_page_title(title: str) -> str:
    clean = WS_RE.sub(" ", title).strip()
    if SITE_NAME.lower() in clean.lower():
        return clean
    return f"{clean}{TITLE_SEPARATOR}{SITE_NAME}"


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

    title_raw = unescape_fully(WS_RE.sub(" ", title_match.group(1)).strip())
    title = strip_site_suffix(title_raw)
    page_title = format_page_title(title)
    canonical = canonical_match.group(1).strip()
    published_match = PUBLISHED_RE.search(page)
    published = published_match.group(1) if published_match else ""

    content_fragment = extract_content_fragment(page)
    slug = slug_from_canonical(canonical)
    override = SUMMARY_OVERRIDES.get(slug)
    if override:
        description = summarize(override)
    else:
        description_plain = first_paragraph_text(content_fragment) or to_plain_text(content_fragment)
        description_plain = re.sub(r"^Home\s+Articles\s+Videos\s+", "", description_plain, flags=re.IGNORECASE)
        if len(description_plain) < 40:
            description_plain = to_plain_text(page)
            description_plain = re.sub(r"^Home\s+Articles\s+Videos\s+", "", description_plain, flags=re.IGNORECASE)
        description = sentence_based_summary(description_plain) or excerpt_summary(description_plain) or fallback_summary(title)

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
    cleaned = TITLE_RE.sub(f"<title>{html.escape(page_title)}</title>", cleaned, count=1)
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
