#!/usr/bin/env python3
"""Build article HTML pages from Markdown sources.

Usage:
  python scripts/build_articles.py
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "articles"
SITE_NAME = "Scott Labbe"
TITLE_SEPARATOR = " | "

FENCE_RE = re.compile(r"^```([\w+-]*)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
UL_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
OL_RE = re.compile(r"^\s*\d+\.\s+(.+?)\s*$")
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
CHAT_KEY_RE = re.compile(r"^([a-z_]+)\s*:\s*(.*)$", re.IGNORECASE)


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    body = text[m.end() :]
    meta: dict[str, str] = {}
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip().strip('"').strip("'")
    return meta, body


def first_h1(text: str) -> str | None:
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == 1:
            return m.group(2).strip()
    return None


def strip_leading_h1(text: str) -> str:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == 1:
            rest = lines[idx + 1 :]
            while rest and not rest[0].strip():
                rest = rest[1:]
            return "\n".join(rest)
        break
    return text


def render_inlines(raw: str) -> str:
    placeholders: list[str] = []

    def stash(val: str) -> str:
        placeholders.append(val)
        return f"@@P{len(placeholders)-1}@@"

    escaped = html.escape(raw, quote=False)

    def code_sub(m: re.Match[str]) -> str:
        return stash(f"<code>{m.group(1)}</code>")

    escaped = re.sub(r"`([^`]+)`", code_sub, escaped)

    def img_sub(m: re.Match[str]) -> str:
        alt = m.group(1).strip()
        src = m.group(2).strip()
        return stash(f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}" />')

    escaped = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", img_sub, escaped)

    def link_sub(m: re.Match[str]) -> str:
        text = m.group(1).strip()
        href = m.group(2).strip()
        return stash(f'<a href="{html.escape(href, quote=True)}">{text}</a>')

    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_sub, escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)

    for i, ph in enumerate(placeholders):
        escaped = escaped.replace(f"@@P{i}@@", ph)
    return escaped


def parse_chat_block(lines: list[str]) -> dict[str, str] | None:
    fields: dict[str, str] = {}
    current_key: str | None = None
    allowed = {"user", "model", "image", "user_label", "model_label"}

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if current_key and current_key in fields and current_key != "image":
                fields[current_key] += "\n"
            continue

        if raw.startswith("  ") and current_key:
            continuation = raw[2:].rstrip()
            if continuation:
                if fields[current_key]:
                    fields[current_key] += f"\n{continuation}"
                else:
                    fields[current_key] = continuation
            continue

        match = CHAT_KEY_RE.match(line.strip())
        if not match:
            return None

        key = match.group(1).lower()
        value = match.group(2).strip()
        if key in allowed:
            fields[key] = value
            current_key = key
        else:
            current_key = None

    if not fields.get("user") or not fields.get("model"):
        return None
    return fields


def render_chat_text(raw: str) -> str:
    parts = [p.strip() for p in re.split(r"\n\s*\n", raw.strip()) if p.strip()]
    if not parts:
        return ""
    return "".join(f"<p>{render_inlines(part.replace(chr(10), ' ').strip())}</p>" for part in parts)


def render_chat_block(fields: dict[str, str]) -> str:
    user_html = render_chat_text(fields["user"])
    model_html = render_chat_text(fields["model"])
    user_label = html.escape(fields.get("user_label", "User").strip() or "User")
    model_label = html.escape(fields.get("model_label", "Assistant").strip() or "Assistant")
    image_src = fields.get("image", "").strip()
    image_html = ""
    if image_src:
        image_html = (
            f'\n      <img src="{html.escape(image_src, quote=True)}" '
            'alt="Model response image" class="chat-image" loading="lazy" />'
        )

    return (
        '<section class="chat-example">\n'
        '  <div class="chat-row chat-row-user">\n'
        '    <div class="chat-bubble chat-bubble-user">\n'
        f'      <p class="chat-label">{user_label}</p>\n'
        f'{user_html}\n'
        '    </div>\n'
        "  </div>\n"
        '  <div class="chat-row chat-row-model">\n'
        '    <div class="chat-bubble chat-bubble-model">\n'
        f'      <p class="chat-label">{model_label}</p>\n'
        f'{model_html}{image_html}\n'
        '    </div>\n'
        "  </div>\n"
        "</section>"
    )


def render_markdown(md_text: str) -> str:
    lines = md_text.splitlines()
    out: list[str] = []
    para: list[str] = []
    code: list[str] = []
    code_lang = ""
    in_code = False
    in_ul = False
    in_ol = False
    in_blockquote = False

    def flush_para() -> None:
        nonlocal para
        if para:
            paragraph = " ".join(para).strip()
            if re.fullmatch(r"(?:!\[[^\]]*\]\([^)]+\)\s*){2}", paragraph):
                out.append(f'<p class="image-pair">{render_inlines(paragraph)}</p>')
            else:
                out.append(f"<p>{render_inlines(paragraph)}</p>")
            para = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def close_blockquote() -> None:
        nonlocal in_blockquote
        if in_blockquote:
            out.append("</blockquote>")
            in_blockquote = False

    for line in lines:
        fence = FENCE_RE.match(line)
        if fence:
            flush_para()
            close_lists()
            close_blockquote()
            if in_code:
                block = "\n".join(code)
                if code_lang.lower() == "chat":
                    chat_fields = parse_chat_block(code)
                    if chat_fields:
                        out.append(render_chat_block(chat_fields))
                    else:
                        lang_attr = f' class="language-{code_lang}"' if code_lang else ""
                        out.append(f"<pre><code{lang_attr}>{html.escape(block)}</code></pre>")
                else:
                    lang_attr = f' class="language-{code_lang}"' if code_lang else ""
                    out.append(f"<pre><code{lang_attr}>{html.escape(block)}</code></pre>")
                code = []
                code_lang = ""
                in_code = False
            else:
                in_code = True
                code_lang = fence.group(1).strip()
            continue

        if in_code:
            code.append(line)
            continue

        stripped = line.strip()
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            continue

        if not stripped:
            flush_para()
            close_lists()
            close_blockquote()
            continue

        if stripped in {"---", "***"}:
            flush_para()
            close_lists()
            close_blockquote()
            out.append("<hr />")
            continue

        heading = HEADING_RE.match(line)
        if heading:
            flush_para()
            close_lists()
            close_blockquote()
            level = len(heading.group(1))
            out.append(f"<h{level}>{render_inlines(heading.group(2).strip())}</h{level}>")
            continue

        if stripped.startswith(">"):
            flush_para()
            close_lists()
            if not in_blockquote:
                out.append("<blockquote>")
                in_blockquote = True
            quote_text = stripped.lstrip(">").strip()
            out.append(f"<p>{render_inlines(quote_text)}</p>")
            continue
        close_blockquote()

        ul = UL_RE.match(line)
        if ul:
            flush_para()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{render_inlines(ul.group(1).strip())}</li>")
            continue

        ol = OL_RE.match(line)
        if ol:
            flush_para()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{render_inlines(ol.group(1).strip())}</li>")
            continue

        para.append(stripped)

    flush_para()
    close_lists()
    close_blockquote()
    return "\n".join(out)


def parse_date(meta: dict[str, str], src: Path) -> dt.date:
    raw = meta.get("date", "").strip()
    if raw:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return dt.datetime.strptime(raw, fmt).date()
            except ValueError:
                pass
    return dt.datetime.fromtimestamp(src.stat().st_mtime).date()


def to_plain_text(html_fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_fragment)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def first_paragraph_text(html_fragment: str) -> str:
    m = re.search(r"<p\b[^>]*>(.*?)</p>", html_fragment, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    return normalize_summary(to_plain_text(m.group(1)))


def normalize_summary(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" \n\t\r-")


def finalize_summary(text: str) -> str:
    text = normalize_summary(text).rstrip(" ,;:-")
    if text and text[-1] not in ".!?":
        text += "."
    return text


def truncate_for_meta(text: str, max_len: int = 160) -> str:
    text = normalize_summary(text)
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
    return truncate_for_meta(base)


def excerpt_summary(text: str, max_words: int = 24) -> str:
    words = [w for w in text.split() if w]
    if not words:
        return ""
    excerpt = " ".join(words[:max_words])
    if excerpt and excerpt[-1] not in ".!?":
        excerpt += "."
    return truncate_for_meta(excerpt)


def summarize(meta: dict[str, str], article_html: str, title: str) -> str:
    raw = normalize_summary(meta.get("summary", ""))
    if raw:
        candidate = sentence_based_summary(raw) or truncate_for_meta(raw)
        return candidate if len(candidate) >= 80 else fallback_summary(title)
    candidate_source = first_paragraph_text(article_html) or normalize_summary(to_plain_text(article_html))
    plain = normalize_summary(candidate_source)
    if not plain:
        return fallback_summary(title)
    return sentence_based_summary(plain) or excerpt_summary(plain) or fallback_summary(title)


def format_page_title(title: str) -> str:
    clean = re.sub(r"\s+", " ", title).strip()
    if SITE_NAME.lower() in clean.lower():
        return clean
    return f"{clean}{TITLE_SEPARATOR}{SITE_NAME}"


def article_template(
    title: str,
    published: dt.date,
    article_html: str,
    slug: str,
    summary: str,
    status: str,
) -> str:
    pub_display = published.isoformat()
    canonical = f"https://scottlabbe.me/articles/{slug}/"
    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": summary,
            "author": {
                "@type": "Person",
                "name": "Scott Labbe",
            },
            "datePublished": pub_display,
            "dateModified": pub_display,
            "mainEntityOfPage": canonical,
            "url": canonical,
            "publisher": {
                "@type": "Person",
                "name": "Scott Labbe",
            },
        }
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(format_page_title(title))}</title>
  <meta name="description" content="{html.escape(summary, quote=True)}" />
  <link rel="canonical" href="{canonical}" />
  <meta name="article:published" content="{pub_display}" />
  <meta name="article:status" content="{html.escape(status, quote=True)}" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{html.escape(title, quote=True)}" />
  <meta property="og:description" content="{html.escape(summary, quote=True)}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:site_name" content="Scott Labbe" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{html.escape(title, quote=True)}" />
  <meta name="twitter:description" content="{html.escape(summary, quote=True)}" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/css/main.css" />
  <script type="application/ld+json">{json_ld}</script>
  <style>
    body {{
      background-color: #FDF5E6;
      color: #333333;
      font-family: 'Libre Baskerville', serif;
      max-width: 820px;
      margin: 0 auto;
      padding: 4rem 1.5rem;
      line-height: 1.7;
      font-size: 1rem;
    }}
    h1, h2, h3, h4 {{
      font-family: 'Space Mono', monospace;
      color: #333333;
      line-height: 1.3;
      margin: 1.2rem 0 0.6rem;
    }}
    h1 {{ font-size: 2rem; margin-top: 0; }}
    .site-article-nav {{
      margin: 0 0 1.6rem;
      font-family: 'Space Mono', monospace;
      font-size: 0.95rem;
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }}
    .site-article-nav a {{
      color: #2D5D4B;
      text-decoration: none;
    }}
    .site-article-nav a:hover {{
      text-decoration: underline;
    }}
    p {{ margin: 0.9rem 0; }}
    .published {{
      color: rgba(0,0,0,0.6);
      font-size: 0.9rem;
      margin-bottom: 1.4rem;
    }}
    a {{ color: #2D5D4B; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    ul, ol {{ margin: 0.9rem 0; padding-left: 1.4rem; }}
    li {{ margin: 0.3rem 0; }}
    code {{
      background: rgba(0, 0, 0, 0.06);
      padding: 0.08rem 0.28rem;
      border-radius: 4px;
      font-size: 0.9em;
    }}
    pre {{
      background: rgba(0, 0, 0, 0.06);
      padding: 1rem;
      overflow-x: auto;
      border-radius: 8px;
    }}
    pre code {{
      background: transparent;
      padding: 0;
      border-radius: 0;
    }}
    blockquote {{
      border-left: 3px solid #2D5D4B;
      margin: 1.1rem 0;
      padding-left: 1rem;
      color: rgba(0,0,0,0.85);
    }}
    img {{
      width: 100%;
      height: auto;
      display: block;
      margin: 1rem 0;
      border: 1px solid rgba(0,0,0,0.08);
    }}
    hr {{
      border: 0;
      border-top: 1px solid rgba(0,0,0,0.2);
      margin: 1.4rem 0;
    }}
    .chat-example {{
      border: 1px solid rgba(45, 93, 75, 0.22);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.55);
      padding: 1rem;
      margin: 1.2rem 0;
    }}
    .chat-row {{
      display: flex;
      width: 100%;
      margin: 0.55rem 0;
    }}
    .chat-row-user {{
      justify-content: flex-end;
    }}
    .chat-row-model {{
      justify-content: flex-start;
    }}
    .chat-bubble {{
      max-width: min(86%, 660px);
      border-radius: 12px;
      padding: 0.8rem 0.9rem;
      font-size: 0.96rem;
      line-height: 1.6;
      box-shadow: 0 1px 0 rgba(0,0,0,0.05);
    }}
    .chat-bubble p {{
      margin: 0 0 0.6rem;
    }}
    .chat-bubble p:last-child {{
      margin-bottom: 0;
    }}
    .chat-label {{
      margin: 0 0 0.45rem;
      font-family: 'Space Mono', monospace;
      font-size: 0.78rem;
      letter-spacing: 0.02em;
      color: rgba(0,0,0,0.68);
      text-transform: uppercase;
    }}
    .chat-bubble-user {{
      background: #f3ecdc;
      border: 1px solid rgba(0,0,0,0.1);
    }}
    .chat-bubble-model {{
      background: #e7f1ec;
      border: 1px solid rgba(45, 93, 75, 0.28);
    }}
    .chat-image {{
      margin-top: 0.7rem;
      border-radius: 8px;
      border: 1px solid rgba(0,0,0,0.12);
    }}
    p.image-pair {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.85rem;
      align-items: start;
    }}
    p.image-pair img {{
      margin: 0;
      max-height: 360px;
      object-fit: cover;
    }}
    @media (max-width: 640px) {{
      .chat-example {{
        padding: 0.75rem;
      }}
      .chat-bubble {{
        max-width: 100%;
      }}
      p.image-pair {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <nav class="site-article-nav" aria-label="Article navigation">
    <a href="/">Home</a>
    <a href="/articles/">Articles</a>
    <a href="/videos/">Videos</a>
  </nav>
  <h1>{html.escape(title)}</h1>
  <p class="published">Published on {pub_display}</p>
  <article>
{article_html}
  </article>
</body>
</html>
"""


def build_one(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    title = meta.get("title", "").strip() or first_h1(body) or md_path.parent.name
    status = meta.get("status", "published").strip().lower() or "published"
    content = strip_leading_h1(body)
    published = parse_date(meta, md_path)
    slug = md_path.parent.name
    rendered = render_markdown(content)
    summary = summarize(meta=meta, article_html=rendered, title=title)
    html_text = article_template(
        title=title,
        published=published,
        article_html=rendered,
        slug=slug,
        summary=summary,
        status=status,
    )
    out = md_path.parent / "index.html"
    out.write_text(html_text, encoding="utf-8")
    return slug


def main() -> None:
    md_files = sorted(p for p in ARTICLES_DIR.glob("*/index.md") if p.parent.name != "data")
    if not md_files:
        print("No markdown article sources found.")
    else:
        for md_path in md_files:
            slug = build_one(md_path)
            print(f"Built /articles/{slug}/")

    subprocess.run([sys.executable, str(ROOT / "scripts" / "enhance_legacy_articles_seo.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_articles_index.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "make_sitemap.py")], check=True)


if __name__ == "__main__":
    main()
