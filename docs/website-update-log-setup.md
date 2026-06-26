# Animetro Website Update Log Setup

This repository logs confirmed website updates to Google Sheets after a change is pushed or merged into the `main` branch.

The workflow appends rows to a tab named:

```text
Animetro Website Update Log
```

## Google Sheet

This automation writes to:

```text
Google Sheet ID: 1MjWHgypp0SItMQI6AHiUoTAqTzhe8pyeFVUblcnSDTg
Service account: animetro-sheet-logger@hardy-abode-499712-e7.iam.gserviceaccount.com
```

Open the Google Sheet and share it with this service account as an `Editor`:

```text
animetro-sheet-logger@hardy-abode-499712-e7.iam.gserviceaccount.com
```

The workflow will create the `Animetro Website Update Log` tab if it does not already exist. It will also write this header row:

```text
Date | Page Updated | Section Updated | Change Type | Before | After | Reason for Change | Status | Branch Name | Commit SHA | Pull Request Link | Notes
```

The workflow also creates a separate review tab named:

```text
Codex Change Log
```

This tab is a conservative reverse-sync path for direct website content edits made in GitHub or Codex. It does not overwrite approved Google Sheet rows. Instead, it appends review rows with this header:

```text
Date/Time | File Changed | Section/Page | Old Text | New Text | Commit SHA | Changed By | Action Needed
```

Use this tab to review direct website edits and decide whether those changes should be copied into the approved source-of-truth sheet rows.

## Keyless Google Sheets Connection

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

## GitHub Secret

Add this in GitHub:

```text
Settings > Secrets and variables > Actions > New repository secret
```

Add exactly this secret:

```text
GOOGLE_WORKLOAD_IDENTITY_PROVIDER
```

Use the provider resource name from the `echo` command as the value.

No JSON key is needed for the update-log workflow or the content-sync workflow
when Workload Identity Federation is configured.

Optional repository variable:

```text
WEBSITE_UPDATE_LOG_TAB_NAME = Animetro Website Update Log
CODEX_CHANGE_LOG_TAB_NAME = Codex Change Log
```

## Automatic Logging

The workflow runs on:

- pushes to `main`
- merged pull requests, because GitHub records them as updates to `main`
- manual test runs from the Actions page

It does not log draft changes, uncommitted files, or work-in-progress branch edits.

For direct website content changes, the workflow also appends rows to `Codex Change Log`. It watches:

- `en/**/index.html`
- `zh/**/index.html`
- `index.html`
- `content/*.csv`
- `assets/contact.js`

This is intentionally review-only. Google Sheet rows are not overwritten automatically unless a future workflow can match the exact approved row with certainty. If there is uncertainty, the change stays in `Codex Change Log` for manual review.

The `Sync website content from Google Sheet` workflow also checks for conflicts before exporting Sheet content into the website. If generated website content files were changed more recently than the Google Sheet, the sync will:

- write back a direct `content/website-content.csv` edit only when the content key matches exactly one Google Sheet row
- append unclear direct edits to `Codex Change Log`
- stop the sync before older Sheet content can silently overwrite newer Codex/GitHub edits

`Codex Change Log` uses this review header:

```text
Date/Time | File Changed | Section/Page | Old Text | New Text | Commit SHA | Changed By | Action Needed
```

The Google Sheet remains the master database, but direct Codex edits are either safely synced back or logged for owner review.

For each confirmed `main` update, the workflow fills:

- `Date`: commit date
- `Status`: `Confirmed`
- `Branch Name`: branch name from GitHub
- `Commit SHA`: latest commit SHA
- `Pull Request Link`: pull request link when GitHub can match one
- `Notes`: parsed notes, or automatic fallback notes

The workflow reads these optional fields from the commit message when present:

```text
Page Updated:
Section Updated:
Change Type:
Before:
After:
Reason:
Notes:
```

If a field is missing, the logger leaves it blank instead of guessing.

## Recommended Commit Message Format

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

## Fallback Logging

If the commit message does not include structured fields, the workflow still logs:

- date
- changed files
- commit message
- branch name
- commit SHA
- pull request link when available
- `Status: Confirmed`
- `Notes: Auto-logged from main branch update`

Changed files are placed in `Section Updated` so the row still shows what area of the website changed.

## Safe Test

After adding the GitHub secrets:

1. Go to `Actions`.
2. Open `Log confirmed website update`.
3. Click `Run workflow`.
4. Keep mode as `test-row`.

This appends one safe test row without needing to merge a website change.

To test the direct-content review log, run the same workflow and choose:

```text
test-codex-change-log
```

This appends one safe test row to `Codex Change Log`.
