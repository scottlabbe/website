# scottlabbe.me

A minimal static site built with HTML, CSS, and JavaScript. Designed for speed and deployed on Cloudflare Pages.

## Local Preview

```bash
python3 -m http.server 8080
```

Then open `http://127.0.0.1:8080`

## Pages

- **Home** (`/`) — About page with interactive reveal blocks
- **Articles** (`/articles/`) — Auto-generated from published article pages in `/articles/*/index.html`
- **Videos** (`/videos/`) — Links to YouTube channel

## Adding Articles

1. Create a folder: `/articles/<slug>/`
2. Add your markdown source: `/articles/<slug>/index.md`
3. Optional front matter at top of `index.md`:
   - `title: Your Title`
   - `date: YYYY-MM-DD`
   - `summary: Short 1-2 sentence summary for search snippets`
   - `status: published` (or `draft`)
4. Save images under `/articles/<slug>/images/` and reference like `![Alt](./images/file.png)`
5. Run: `python scripts/build_articles.py`
6. Commit and push

### What `build_articles.py` does

- Converts all `/articles/*/index.md` files into `/articles/*/index.html`
- Rebuilds `/articles/index.html` sorted by publish date (newest first)
- Rebuilds `/sitemap.xml`

## Design

- **Fonts:** Libre Baskerville (body) + Space Mono (headers/UI)
- **Colors:** Warm cream background, charcoal text, hunter green accents
- **Interaction:** Hover/tap underlined words to reveal links with smooth dropdown animation

## Deployment

- Push to GitHub
- Connect repo to Cloudflare Pages
- Set build command: `exit 0`
- Set build output directory: `/` (root)
- Add custom domain `scottlabbe.me` in project settings
