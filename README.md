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
python3 -m http.server 4173
```

Then open:

```text
http://localhost:4173/
```

## Google Sheet Content Sync

The website content sync can export the latest Google Sheet into:

```text
content/website-content.csv
```

Then it updates the static website files from that CSV.

Required GitHub repository secrets for the automatic sync workflow:

```text
GOOGLE_SHEET_ID
GOOGLE_SERVICE_ACCOUNT_JSON
GOOGLE_DRIVE_FOLDER_ID
```

Optional repository variable:

```text
GOOGLE_SHEET_TAB_NAME
```

Default:

```text
Website Copy
```

Manual local run:

```bash
python3 scripts/sync_website_content.py
```

GitHub Action:

```text
Sync website content from Google Sheet
```

### Google Drive Folder Access

The sync workflow can also verify read-only access to a Google Drive folder that is explicitly shared with the service account:

```text
animetro-sheet-logger@hardy-abode-499712-e7.iam.gserviceaccount.com
```

This does not download, replace, or change website images. It only confirms the automation can read the shared folder when `GOOGLE_DRIVE_FOLDER_ID` is set.

To find the Google Drive folder ID:

1. Open the folder in Google Drive.
2. Copy the URL from the browser.
3. Use the ID after `/folders/`.

Example:

```text
https://drive.google.com/drive/folders/1_-jbZCPZBW8HgVVGdnOr6WsOw95NJhS_
```

Add this GitHub repository secret:

```text
GOOGLE_DRIVE_FOLDER_ID = 1_-jbZCPZBW8HgVVGdnOr6WsOw95NJhS_
```

To share the folder:

1. Open the Google Drive folder.
2. Click `Share`.
3. Add `animetro-sheet-logger@hardy-abode-499712-e7.iam.gserviceaccount.com`.
4. Give it `Viewer` access.

To add the same value in Vercel:

1. Open the Vercel project.
2. Go to `Settings > Environment Variables`.
3. Add:

```text
GOOGLE_DRIVE_FOLDER_ID = 1_-jbZCPZBW8HgVVGdnOr6WsOw95NJhS_
```

Keep `GOOGLE_SERVICE_ACCOUNT_JSON` in GitHub Secrets only. Do not commit it into the repository.

## Vercel Deployment

This is a plain static HTML/CSS/JavaScript website. It is not Vite, React, or Next.js.

Use these Vercel settings:

- Framework Preset: `Other`
- Build Command: leave blank
- Output Directory: leave blank
- Install Command: leave blank

Vercel should deploy the static files directly from the repository root.

## GitHub Upload

Upload these files and folders to GitHub:

- `index.html`
- `en/`
- `zh/`
- `assets/`
- `content/`
- `.github/`
- `scripts/`
- `docs/`
- `vercel.json`
- `.gitignore`
- `README.md`

Do not upload:

- `dist/`
- `node_modules/`
- `.DS_Store`
- `package.json`

## Automatic Website Update Log

This repository includes a GitHub Actions workflow that appends one confirmed update row to a Google Sheet after changes are pushed or merged into the `main` branch.

The workflow writes to a sheet tab named:

```text
Animetro Website Update Log
```

The tab uses these columns:

```text
Date | Page Updated | Section Updated | Change Type | Before | After | Reason for Change | Status | Branch Name | Commit SHA | Pull Request Link | Notes
```

### 1. Google Sheet

```text
Google Sheet ID: 1MjWHgypp0SItMQI6AHiUoTAqTzhe8pyeFVUblcnSDTg
Service account: animetro-sheet-logger@hardy-abode-499712-e7.iam.gserviceaccount.com
```

Open the Google Sheet and share it with this service account as an `Editor`:

```text
animetro-sheet-logger@hardy-abode-499712-e7.iam.gserviceaccount.com
```

The workflow will create the `Animetro Website Update Log` tab and header row if they do not already exist.

### 2. Connect GitHub Actions Without a JSON Key

Use Google Cloud Workload Identity Federation. This lets GitHub Actions use the service account without downloading a JSON key.

Set these values in Google Cloud Shell:

```text
PROJECT_ID="hardy-abode-499712-e7"
REPO="animetroconsulting-ui/Animetro-Consulting"
POOL_ID="github-actions-pool"
PROVIDER_ID="animetro-github-provider"
SERVICE_ACCOUNT="animetro-sheet-logger@hardy-abode-499712-e7.iam.gserviceaccount.com"
```

Enable the needed Google APIs:

```bash
gcloud config set project "$PROJECT_ID"
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com sheets.googleapis.com
```

Get the project number:

```bash
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
```

Create the Workload Identity Pool:

```bash
gcloud iam workload-identity-pools create "$POOL_ID" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"
```

Create the GitHub OIDC provider:

```bash
gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="$POOL_ID" \
  --display-name="Animetro GitHub Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='${REPO}'"
```

Allow this GitHub repository to use the service account:

```bash
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO}"
```

Copy the provider resource name:

```bash
echo "projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
```

### 3. Add GitHub Secret

```text
Settings > Secrets and variables > Actions > New repository secret
```

Add exactly this secret:

```text
GOOGLE_WORKLOAD_IDENTITY_PROVIDER
```

Use the provider resource name from the `echo` command as the value.

No JSON key is needed for the update-log workflow. The separate content-sync workflow uses `GOOGLE_SERVICE_ACCOUNT_JSON`.

Optional repository variable:

```text
WEBSITE_UPDATE_LOG_TAB_NAME = Animetro Website Update Log
```

### 4. How Automatic Logging Works

The workflow run only on:

- pushes to `main`
- merged pull requests, because GitHub records them as updates to `main`
- manual test runs from the Actions page

It does not log draft changes, uncommitted files, or work-in-progress branches.

If the commit message includes structured fields, the logger places them in the matching sheet columns:

```text
Page Updated:
Section Updated:
Change Type:
Before:
After:
Reason:
Notes:
```

Example commit message:

```text
Update homepage consultation CTA

Page Updated: Homepage
Section Updated: Main CTA button
Change Type: Copy update
Before: Book a Private Consultation
After: Book a Free Private Consultation
Reason: Make the consultation offer clearer and more attractive for parents.
Notes: Applied to homepage hero CTA and repeated homepage CTA.
```

If those fields are not present, the workflow still logs:

- date
- changed files
- commit message
- branch name
- commit SHA
- pull request link when GitHub can find one
- `Status: Confirmed`
- `Notes: Auto-logged from main branch update`

### 5. Safe Test

After adding the secrets:

1. Go to the GitHub repository.
2. Open `Actions`.
3. Select `Log confirmed website update`.
4. Click `Run workflow`.
5. Keep mode as `test-row`.

This appends one safe test row without needing to merge a website change.

## Domain

After the Vercel project is deployed:

1. Open the Vercel project dashboard.
2. Go to Settings > Domains.
3. Add `animetro.ca`.
4. Follow Vercel's DNS instructions for the domain registrar.
5. Add the recommended `A` record or `CNAME` record shown by Vercel.
6. Wait for DNS verification to finish.
