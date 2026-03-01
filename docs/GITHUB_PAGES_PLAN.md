# Deploy Docus Site to GitHub Pages

## Overview

Deploy the `docs/` Docus site to **https://briancaffey.github.io/waywo** using GitHub Actions.

---

## Step 1: GitHub Repository Settings

In your GitHub repo (`briancaffey/waywo`), go to **Settings > Pages** and set:

- **Source**: `GitHub Actions`

That's the only setting you need to change. Do **not** select a branch — the workflow will handle deployment via the `actions/deploy-pages` action.

## Step 2: Set the Base URL

Since the site is served from a subpath (`/waywo/`), Nuxt needs to know this so that asset paths and routing work correctly.

Create `docs/nuxt.config.ts`:

```ts
export default defineNuxtConfig({
  app: {
    baseURL: '/waywo/'
  }
})
```

## Step 3: Add the GitHub Actions Workflow

Create `.github/workflows/docs.yml`:

```yaml
name: Deploy Docs to GitHub Pages

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install dependencies
        run: npm install
        working-directory: docs

      - name: Generate static site
        run: npm run generate
        working-directory: docs

      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs/.output/public

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

## Step 4: Push and Verify

1. Commit the two new files (`docs/nuxt.config.ts` and `.github/workflows/docs.yml`)
2. Push to `main`
3. Go to **Actions** tab in your repo to watch the workflow run
4. Once complete, visit **https://briancaffey.github.io/waywo**

## Notes

- The workflow only triggers on changes to `docs/**`, so normal code pushes won't cause a redeploy. You can also trigger it manually via `workflow_dispatch`.
- `nuxt generate` outputs static files to `docs/.output/public/`, which is already gitignored.
- No secrets or tokens are needed — the built-in `GITHUB_TOKEN` with the declared permissions is sufficient.
