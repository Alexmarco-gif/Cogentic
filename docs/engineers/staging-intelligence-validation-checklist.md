# Staging Intelligence Validation Checklist

This runbook is for engineers validating that Cogent is not just deployed, but actively producing live intelligence from real monitoring coverage.

## Goal

Prove the full chain below is working in staging:

1. A contract or managed source exists.
2. Acquisition jobs queue successfully.
3. Workers consume those jobs.
4. Signals land in the database and become visible through the API.
5. Briefs and downstream intelligence surfaces refresh from live data.
6. The frontend reflects those live results honestly.

## Prerequisites

- Backend and worker container apps are healthy.
- Redis and Postgres are reachable from the running apps.
- Required provider credentials are present in Key Vault or app secrets.
- You have an **admin** bearer token for the staging backend.
- At least one active contract exists, or you are ready to create/activate one.

## Step 1: Run the automated validation script

From the repo root:

```powershell
$env:COGENT_BASE_URL = "https://cogent-stg-backend.purpleglacier-069239e0.uksouth.azurecontainerapps.io"
$env:COGENT_BEARER_TOKEN = "<admin bearer token>"
python scripts/validate_intelligence_pipeline.py --trigger-fetch
```

If you want the fetch step to fail hard when no new signals appear:

```powershell
python scripts/validate_intelligence_pipeline.py --trigger-fetch --require-signal-growth
```

## Step 2: Interpret the automated results

### A healthy run should show

- `Backend health` passed
- `Scheduler` passed
- `Workers` passed with at least one worker online
- `Queue health` passed or only mild warnings
- `Provider readiness` passed, or only warns about providers you intentionally have not configured
- `Contracts` passed with at least one active contract
- `Signals feed` passed or at least shows some known non-zero live signals
- `Briefs` passed or warns only for a fresh workspace
- `Manual fetch` passed

### Failures that must be fixed before trusting staging

- No workers online
- Scheduler not running
- Manual fetch fails to queue
- Source health reports critical contracts
- Contract fetch target cannot resolve

### Warnings that may still be acceptable

- No briefs yet in a fresh workspace
- No signal growth after one manual fetch when the provider returned duplicates or no fresh content
- Some premium providers not configured if you are only validating generic RSS/API/scraper coverage

## Step 3: Validate the pipeline in the product UI

After the script passes or mostly passes, confirm the user-facing journey:

### Home

- The page should load without generic dead states.
- If there are still no signals, the page should explain the next step clearly.
- Once signals land, recent live activity should start appearing.

### Studio

- Create or review a real contract.
- Trigger activation or a fetch from the live controls.
- Confirm the UI frames this as real acquisition, not simulation output.

### Marketplace

- Confirm managed templates are visible.
- Activate one managed source if relevant to the validation scenario.

### Signals

- Confirm new signals appear in the table or feed.
- Open a signal drawer and confirm the dossier renders real content.

### Library

- Refresh the library.
- Confirm at least one brief appears once enough signals exist.

### Investigate

- Confirm a new thread can reference real signals or workspace context.

## Step 4: If the script fails, use this triage order

### Workers are offline

- Check the worker container app revisions.
- Confirm Redis URL is valid.
- Confirm the worker process is actually starting and heartbeating.

### Provider readiness warns or fails

- Check Key Vault secrets and container app secret references.
- Confirm the provider-specific env vars are present in the backend and worker.

### Queues are growing but signals do not land

- Check worker logs for acquisition failures.
- Check source health for stale, degraded, or critical contracts.
- Confirm the contract resolves to a real managed endpoint or source URL.

### Signals land but Home/Signals/Library stay empty

- Verify the frontend is pointing to the correct backend URL.
- Confirm the authenticated user belongs to the org that owns the signals.
- Check feature gating and credits for intelligence briefs.

## Step 5: Recommended staging validation cadence

- Run the script after each major deployment.
- Run it again after rotating provider credentials.
- Run it before demos or user testing where live intelligence is expected.

## Notes

- The automated script is intentionally conservative: it proves operational readiness, not business correctness for every source.
- Paid upstream integrations such as NewsAPI, X, NGX market data, and OpenAI-backed synthesis still depend on valid production-grade credentials and network access.
- Generic RSS, scraper, and JSON API acquisition should already be considered part of the baseline platform health.
