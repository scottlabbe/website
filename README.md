# scottlabbe.me

A minimal static site built with HTML, CSS, and JavaScript. Designed for speed and deployed on Cloudflare Pages.

## Local Preview

```bash
python3 -m http.server 8080
```

Then open `http://127.0.0.1:8080`

## Pages

- **Home** (`/`) — About page with interactive reveal blocks
- **Articles** (`/articles/`) — Auto-generated from HTML files in `/articles/data/Articles/`
- **Videos** (`/videos/`) — Links to YouTube channel

## Adding Articles

1. Drop your HTML file into `/articles/data/Articles/`
2. Include a `<p class="published">Published on YYYY-MM-DD HH:MM</p>` tag in the file for date sorting
3. Run: `python scripts/generate_articles_index.py`
4. Commit and push

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
