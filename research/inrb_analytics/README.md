# Public INRB–UMIE aggregate acquisition (research-only)

This contained directory hosts the read-only, **non-publishing** utility originating from the BDBV Observatory 22 November 2026 development package.

## Boundaries
- **Not part of the scheduled SitRep extraction, bulletin build, automatic publishing, or One.com deployment.**
- Fetches only preselected public aggregate files at **pinned upstream commits**. No person-level/private data, no spatial-invasion forecasts.
- Stores acquisition-date folders immutably under a caller-specified output directory, with SHA-256, upstream commit, and column/missingness audit in a manifest.
- All acquired records remain `NOT_APPROVED_FOR_PUBLICATION`. Do not feed them into `published/`, `analysis_inputs/`, the Observatory, or Gemini until validated.
- The embedded paths represent **21 November 2026 contact-tracing** and **18 November 2026 labelled Rt** snapshots. Rt observation dates may be older. New releases require a deliberate source and date review.
- Compare case definitions, denominators, event time versus reporting time, censoring, and revision vintages before making analytical claims.

## Manual use (never run from a public web directory)

Save a local JSON file mapping these public repositories to their exact 40-character Git commit hashes:

```json
{
  "BDBV2026-Contact_Tracing_Analytics": "REPLACE_WITH_40_CHARACTER_COMMIT_SHA",
  "BDBV2026-Epidemic_Dashboard": "REPLACE_WITH_40_CHARACTER_COMMIT_SHA"
}
```

Then run:

```bash
python research/inrb_analytics/fetch_public_analytics.py \
  --commits-json /private/path/commits.json \
  --vintage 2026-11-22 \
  --output /private/path/inrb-quarantine
```

Review the resulting `manifest.json`, failures, content schemas and historical date coverage. The command exits unsuccessfully if any configured source fails. A preexisting dated output directory is never overwritten. Keep output data untracked and away from publicly served website paths.

## Future integration
After methodological review, create a **separate, deliberate publication gate** and explicit server-side import contract. Keep source acquisition separate from data acceptance and bulletin publication. No cron or workflow trigger is created by this PR.

## Website layout principle
The BDBV Observatory is potentially temporary. Keep all module-specific PHP/JS/CSS/data and eventual export interfaces inside `bdvd2026/`; do not scatter files or folders throughout the African Intelligence web root. This GitHub research folder is not a website upload.
