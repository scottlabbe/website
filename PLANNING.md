# Site plan — scottlabbe.me

## Goals
- **About Me is the homepage** (root `/`).
- Keep the site minimal, sharp, and fast.
- Use your existing **HTML articles as-is** (no reformatting required).
- Deploy on **Cloudflare Pages** and attach the custom domain `scottlabbe.me`.

## Repo location (your machine)
`/Users/scottlabbe/Projects/website`

## Pages
### 1) Home (About Me) — `/index.html`
- Cream background, black text.
- Five unbulleted sentences **exactly** as provided.
- Each sentence contains one underlined phrase. Hover/tap reveals the bullet links beneath it.
- Spacing: each block is separated by a few line breaks (implemented as margin).

### 2) Articles — `/articles/index.html`
- Lists every `*.html` file in `/articles/data/Articles/`
- Sorted by **published date descending**, extracted from:
  - `<p class="published">Published on YYYY-MM-DD HH:MM</p>`

### 3) Videos — `/videos/index.html`
- Links to your YouTube channel for now.
- Later: curate individual video links with short blurbs.

### 4) Optional alternate path — `/about/`
- Exists so `/about` still works.
- Redirects to `/` via `_redirects` and a simple HTML fallback.

## Directory structure
```text
website/
  index.html
  _redirects
  assets/
    css/main.css
    js/main.js
  about/index.html
  articles/
    index.html
    data/Articles/*.html
  videos/
    index.html
  scripts/
    generate_articles_index.py
```

## Styling choices
- Background: cream (`#fbf6ea`)
- Text: near-black (`#111`)
- System sans for nav + headings; serif for body text.
- Underlined trigger text uses `cursor: pointer` and an offset underline.

## Interaction design for the About blocks
- **Desktop**: hover over a block (underlined text is the visual cue) reveals links.
- **Mobile / keyboard**: tapping/pressing Enter on underlined text toggles links open (via `assets/js/main.js`).

## Redirect behavior
- Use Cloudflare Pages `_redirects` file to keep `/about` and `/index.html` stable.

## Deployment (Cloudflare Pages)
- Framework preset: None / static
- Build command: `exit 0` (no build step required)
- Output directory: repository root

Then attach the custom domain in Cloudflare Pages project settings.

## Content maintenance workflow
1. Add or edit article HTML files in `articles/data/Articles/`.
2. Run: `python scripts/generate_articles_index.py`
3. Commit + push. Cloudflare will deploy automatically.

