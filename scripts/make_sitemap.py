from pathlib import Path
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

SITE = "https://scottlabbe.me"
BUILD_DIR = Path(".")  # run from /Users/scottlabbe/Projects/website
EXCLUDE_DIRS = {"assets", "scripts", ".git"}  # tweak if you add more later
SKIP_FILES = {"404.html"}  # add any utility pages you don't want indexed
SKIP_PATHS = {"about/index.html"}  # redirect-only page

def is_excluded(path: Path) -> bool:
    if any(part.startswith(".") or part in EXCLUDE_DIRS for part in path.parts):
        return True
    # Skip legacy article sources; only clean slugs should be indexed.
    parts = set(path.parts)
    if "articles" in parts and "data" in parts:
        return True
    return False

def to_url(path: Path) -> str:
    rel = path.relative_to(BUILD_DIR).as_posix()
    if rel == "index.html":
        rel = ""
    elif rel.endswith("/index.html"):
        rel = rel[:-10]  # drop trailing "index.html"
    elif rel.endswith(".html"):
        rel = rel[:-5]
    if rel and not rel.startswith("/"):
        rel = "/" + rel
    return SITE + rel

urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

count = 0
for html in BUILD_DIR.rglob("*.html"):
    if html.name in SKIP_FILES or is_excluded(html):
        continue
    rel_path = html.relative_to(BUILD_DIR).as_posix()
    if rel_path in SKIP_PATHS:
        continue
    url = ET.SubElement(urlset, "url")
    ET.SubElement(url, "loc").text = to_url(html)
    lastmod = datetime.fromtimestamp(html.stat().st_mtime, tz=timezone.utc).date().isoformat()
    ET.SubElement(url, "lastmod").text = lastmod
    count += 1

out = BUILD_DIR / "sitemap.xml"
ET.ElementTree(urlset).write(out, encoding="utf-8", xml_declaration=True)
print(f"Wrote {out} with {count} URLs")
