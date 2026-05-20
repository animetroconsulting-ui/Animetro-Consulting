# Animetro Education Consulting

Static bilingual website for Animetro Education Consulting / 艾美加教育顧問.

## Structure

- `/` is the language landing page.
- `/en/` contains English pages.
- `/zh/` contains Traditional Chinese pages.
- `/assets/styles.css` contains shared design styles.

## Edit Content

Edit the page text directly in the matching language folder:

- English homepage: `en/index.html`
- English services: `en/services/index.html`
- English about: `en/about/index.html`
- English contact: `en/contact/index.html`
- Chinese homepage: `zh/index.html`
- Chinese services: `zh/services/index.html`
- Chinese about: `zh/about/index.html`
- Chinese contact: `zh/contact/index.html`

## Local Preview

From this folder, run:

```bash
npm run preview
```

Then open:

```text
http://localhost:4173/
```

## Vercel Deployment

This is a plain static HTML/CSS/JavaScript website. It is not Vite, React, or Next.js.

Use these Vercel settings:

- Framework Preset: `Other`
- Build Command: `npm run build`
- Output Directory: `dist`
- Install Command: leave as default

The build command copies the current static website into `dist/` for deployment.

## GitHub Upload

Upload these files and folders to GitHub:

- `index.html`
- `en/`
- `zh/`
- `assets/`
- `content/`
- `scripts/`
- `package.json`
- `vercel.json`
- `.gitignore`
- `README.md`

Do not upload:

- `dist/`
- `node_modules/`
- `.DS_Store`

## Domain

After the Vercel project is deployed:

1. Open the Vercel project dashboard.
2. Go to Settings > Domains.
3. Add `animetro.ca`.
4. Follow Vercel's DNS instructions for the domain registrar.
5. Add the recommended `A` record or `CNAME` record shown by Vercel.
6. Wait for DNS verification to finish.
