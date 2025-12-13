# scottlabbe.me

A minimal static site (HTML/CSS/JS) designed to deploy cleanly to Cloudflare Pages.

## Local preview

From the project root:

```bash
python3 -m http.server 8080
```

Then open http://localhost:8080

## Add / update articles

1. Drop HTML files into:

`articles/data/Articles/`

2. Regenerate the articles index:

```bash
python scripts/generate_articles_index.py
```

3. Commit the changes.

## Cloudflare Pages deploy (quick)

- Create a new **Pages** project in Cloudflare and connect it to this repo.
- Framework preset: **None**
- Build command: `exit 0`
- Build output directory: `/` (project root)

Then add the custom domain `scottlabbe.me` to the Pages project.

See Cloudflare docs:
- Custom domains: https://developers.cloudflare.com/pages/configuration/custom-domains/
- Redirects: https://developers.cloudflare.com/pages/configuration/redirects/
