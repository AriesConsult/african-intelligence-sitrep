# AFRICAN INTELLIGENCE — BDBV SITREP INGESTION OPERATIONS

## CURRENT PRODUCTION RUNBOOK — 11 NOVEMBER 2026

**Analytical methods, calculations and exact prompt-inventory status:** [current methodology and prompts](ANALYTICAL_METHODS_AND_PROMPTS_20261111.md).

### Current automated chain (11 November 2026)

1. **08:27 Africa/Nairobi (05:27 UTC)** — `.github/workflows/bdbv-sitrep-pipeline.yml` discovers original INSP/INRB SitReps, maintains source identities, SHA-256 and release custody, reprocesses archived extraction grids, and runs numerical/narrative publication checks. Sunday 07:41 EAT invokes full backfill. Do not equate a green workflow with full independent cell verification.
2. **10:25 EAT (07:25 UTC)** — `.github/workflows/bdbv-bulletins.yml` builds the source-only bilingual HTML/JSON bundle. It is also triggered by changes to `published/table_index.json` or `published/feed.json` on main. GitHub scheduling may be delayed; each release remains hash- and version-addressable.
3. **Every six hours** — cron-job.org uses `0 */6 * * *` in **Africa/Nairobi** (00:00, 06:00, 12:00, 18:00 EAT) to call the existing One.com authenticated `webcron_task=bdbv_source_sync` route. The website validates the GitHub Release asset and per-file manifest, imports allowlisted source-only assets, records backups, and skips unchanged releases. **Never commit or reproduce the webcron token.**
4. **Public observatory** — `/bdvd2026/dashboard.php` reads the imported evidence files. The contact tab only displays source-identical, internally reconciled `MACHINE_VALIDATED` Table 4 rows; SitReps 178 (8 Nov; 30,444/38,453 = 79.2%) and 179 (9 Nov; 27,012/33,900 = 79.7%) are validated in the repository. Missing/rejected dates are not inferred or silently zero-filled.
5. **Separate editorial layer** — One.com, not GitHub, holds the active prompts and the daily/weekly/monthly AI-draft, historical backfill, assessment QA, approval and publication mechanisms. Source synchronization **does not** imply automatic AI publication. Approved narratives are versioned and evidence-fingerprint-bound; mismatches require a fresh review.

**Scientific interpretation:** differences of cumulative reported cases/deaths are net reporting changes, **not** onset-date incidence. Source extracts marked `REVIEW_REQUIRED` remain unverified narrative leads. Exploratory dashboard apparent Rₜ must not be presented as validated reproduction number or used as a scientific model result without dedicated validation.

### Routine checks and failures

- Confirm last successful [ingestion Actions run](https://github.com/AriesConsult/african-intelligence-sitrep/actions/workflows/bdbv-sitrep-pipeline.yml) and [source-bulletin build](https://github.com/AriesConsult/african-intelligence-sitrep/actions/workflows/bdbv-bulletins.yml); compare actual completion timestamps, not scheduled start times.
- Verify `published/table_index.json`, `published/publication_qa.json`, and report-level `published/tables/<report>_<sha>.json` before interpreting a skipped Table 4 date. Reconcile the original PDF's printed table, including shifted/split rows, with the exact hash-pinned extraction.
- Confirm the **latest new GitHub source-bulletin release** and whether cron-job.org reported `imported` or `unchanged`. `unchanged` means the site has already seen the latest selected release, **not** that a new upstream SitRep was necessarily validated.
- On GitHub concurrency: an ingestion run can report success while safely declining to push stale results after main advances. Check the logs for `Remote branch advanced during extraction; this stale run will not publish`. Re-run cleanly from current main if needed; never force-push.
- If a source changes SHA or fails reconciliation, preserve earlier revisions and withhold affected indicators. If import fails, retain the previous site bundle and check the manifest/allowlist and importer logs; never overwrite PHP controllers or prompt storage with source releases.
- Cron cadence is controlled in **cron-job.org**, not GitHub. Rotate and update the webcron token in both the website configuration and each configured job; never log or paste its value publicly.

### Active One.com paths (not part of the GitHub source bundle)

`public_html/index.php` webcron dispatcher; `cron/bdbv_source_sync.php`; `includes/bdbv_github_sync.php`; `admin_bdbv_sync.php`; `admin_bdbv_assessments.php`; `admin_bdbv_backfill.php`; `admin_bdbv_bulk_approve.php`; `admin_ai_prompts.php`; `bdvd2026/dashboard.php`; `bdvd2026/assessment.php`; `bdvd2026/assessment_pdf.php`. These path names describe the live site architecture, not files mirrored or editable by this repository.

### Prompts and authoritative copies

The live One.com prompt manager stores the active daily/weekly/monthly FR/EN text. The GitHub `build_bdbv_assessments.py` contains an **older, optional GitHub-side English review draft SYSTEM prompt**, not the current production prompt. Do not substitute it for a One.com prompt. For prompt change-control export from `admin_ai_prompts.php` (including IDs, language, model, version, effective date and exact text), retain the previous version, and run historical EN/FR regression samples before activation. Known active IDs include `bdbv_daily_v1` and `bdbv_monthly_v1`; the reported default model is `gemini-2.5-flash-lite`, subject to verification against live configuration. Prompt text is **not available from the GitHub source repository**.

---


**System:** `AriesConsult/african-intelligence-sitrep`  
**Revision:** 8 November 2026 (qualified historical acceptance and routine daily source collection)  
**Boundary:** GitHub acquisition, numerical and narrative classification, source verification and release archiving. The existing One.com observatory, forecasting models and literature portal are *not* modified.

## Current operating decision

The core scraper and publication QA are operational. The latest inspected scheduled run on **8 November 2026** succeeded across source discovery, downloads, table/narrative processing, integrity and publication gates: [run 42478204067](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42478204067).

The **qualified historical evidence dataset** is separately released with 15,726 pinned source rows and explicit acceptance tiers (14,442 eligible for labelled descriptive use, 1,284 restricted); it is **not** automatically published into the operational feed or the One.com website. See [release guide](DATA_RELEASES.md).

**Priority:** preserve reliable daily source collection. Historical cells and narrative text can be improved independently in versioned, review-controlled evidence releases.

## Daily schedule and operational monitoring

| Job | GitHub Actions workflow | Schedule in UTC / EAT | What to verify |
| --- | --- | --- | --- |
| New SitRep discovery and extraction | [Core pipeline](../.github/workflows/bdbv-sitrep-pipeline.yml) | 05:27 / 08:27 daily | Success, `state/registry.json`, `published/ingestion_audit.json`, `published/publication_qa.json` |
| Sunday complete source backfill | [Same pipeline](../.github/workflows/bdbv-sitrep-pipeline.yml) | 04:41 / 07:41 Sunday | Full source discovery `--limit 0`, source failures, publication QA |
| Archive original PDF bytes | [Source archive](../.github/workflows/bdbv-source-archive.yml) | 06:10 / 09:10 daily | SHA-256 manifest, GitHub Release, `published/source_archive_index.json` |
| Detect later original-PDF revisions | [Source change control](../.github/workflows/bdbv-future-change-control.yml) | 06:55 / 09:55 daily | No disappearing frozen hash; new/revised sources routed to review |

GitHub schedules may start late. **Do not assume the 09:10 archive is for today's newest PDF without checking job/run timestamps**; the three schedules are independently triggered and not a single transactional workflow.

If the daily pipeline does not complete successfully:

1. Check the [Actions runs](https://github.com/AriesConsult/african-intelligence-sitrep/actions) and inspect the failing step; source discovery or upstream HTTP errors may be temporary.
2. Check `published/ingestion_audit.json` and `published/publication_qa.json` before interpreting the prior successful result as current.
3. Use **Run workflow** on the core pipeline; choose `full_backfill=false` for a normal bounded run and `true` only when a historical discovery/backfill is needed.
4. Once the source registry is updated and the pipeline has passed, run the **source archive** workflow if its daily execution already happened before new PDF ingestion.
5. Run **future source-change control** afterwards; investigate any new report hash or revision before approving changed historical figures. Never force-push or wipe existing archive revisions.
6. If upstream access repeatedly fails, retain the previous accepted data and record the source gap/freshness warning; do not replace missing reports or `ND` with zero.

For local checks, run commands from the **repository root**, using `python3 -m pip install -r requirements.txt pytest reportlab` and `python3 -m pytest -q tests`. The older `sitrep_pipeline/` directory path in the former README was obsolete.

## Workflow and destinations

The regular workflow `.github/workflows/bdbv-sitrep-pipeline.yml` executes:
1. Test the Python code against real archived SitRep extracts.
2. Discover official 2026/17th-epidemic SitReps and register original source SHA-256 hashes.
3. Reprocess the table extraction queue with per-table reconciliation; never replace the INRB cases/deaths baseline.
4. Reprocess hash-verified narrative candidates. The first complete backfill covers the full historical catalogue; daily runs check the latest reports.
5. Compile review-only longitudinal themes and exact-repeat signals.
6. Write the integrity audit, then run the **independent publication gate**.
7. Commit validated results only if the branch has not advanced. Never force-push over newer evidence.

The separate workflow `.github/workflows/bdbv-source-archive.yml` creates immutable GitHub Release assets containing unmodified source PDFs, each checked against its recorded SHA-256. It updates `published/source_archive_index.json` only after a release has been created successfully. It runs daily at 09:10 East Africa Time, on archive-code changes, and on manual dispatch. It archives only new report/hash identities.

## Qualified historical evidence, distinct from the operational feed

The [qualified historical release](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-qualified-historical-42498372593) contains:

- `historical_qualified_release.csv` — all 15,726 source records and their classification.
- `historical_exclusions.csv` — the 1,284 restricted records and their precise, possibly overlapping reasons.
- `metric_tier_coverage.csv` — distribution by indicator.
- `HISTORICAL_ACCEPTANCE_REPORT.md` and `historical_acceptance_report.json` — human/machine audit decisions plus frozen input hashes.

**A: 3**, **B: 4,222**, **C: 10,217** rows permitted for their specified *descriptive* uses, with different evidentiary confidence; no row is automatically suitable for deriving daily incidence from cumulative figures. The 17 existing individually visually checked PDF transcriptions live in a separate source-reading release. The 114 cumulative declines and ambiguous cells are preserved as review evidence; no retrospective case/death dates are invented.

The three scanned SitReps 007–009 are separately hash-archived (37 pages); OCR text and numbers are provisional. Narrative completeness is a **separate** track: 158 digitally extracted originals and three additional scanned identities, with heuristic segments and INRB source comparisons requiring substantive verification.

Any subsequent historical update needs a new immutable-convention release, source revision and acceptance report. Do **not** edit the frozen historical originals or treat a green Actions run as automatic evidence promotion.

## Primary data products

| Path | Status and role |
| --- | --- |
| `state/registry.json` | Original PDF identity, report date and source URLs |
| `review_queue/report_*.json` | Unverified, archived candidate table extractions |
| `published/tables/*.json` | Five-table snapshots with per-table validation and flags |
| `published/table_index.json` | Historical coverage and incomplete-table flags |
| `published/feed.json` | Source-reconciled operational indicators only |
| `published/narrative_candidates/*.json` | Page-linked excerpts and lexical classification leads; **not accepted events** |
| `published/narrative_index.json` | Narrative archive coverage |
| `published/narrative_signal_index.json` | Longitudinal topics/repetition patterns; **review-only** |
| `published/ingestion_audit.json` | Source/report/release completeness and gaps |
| `published/publication_qa.json` | Independent observation-to-source check; `pass=true` is mandatory |
| `published/source_archive_index.json` | Immutable source PDF release inventory |

## Verification commands

```bash
python -m pip install -r requirements.txt pytest reportlab
python -m pytest -q tests
python run_pipeline.py --limit 12 --work work
python reprocess_tables.py
python backfill_narratives.py --limit 12
python build_narrative_signals.py
python audit_ingestion.py
python verify_publication.py
```

For a full narrative/source extraction pass, use `python backfill_narratives.py --limit 0`. A full tabular discovery/backfill uses `python run_pipeline.py --limit 0`. The archive is managed by the separate Actions workflow and must not be simulated by expiring workflow artifacts.

## Acceptance definitions

**Integrity verified** means queue/register hashes agree, index snapshots correspond to their correct originals, and every published machine observation matches its original validated national total, date, page, and PDF hash. A successful GitHub Actions job without these checks is not sufficient.

**Historically complete** would additionally mean every officially published 2026 SitRep has been located and the full range of relevant original tables has been reconstructed, including layout changes, missing provinces and partial reporting. No amount of automatic arithmetic can certify an unrecoverable table without human review.

**Narrative classification complete** means all catalogued original PDFs have been processed through the same hash-linked narrative classifier. Tags and province mentions remain leads for editorial fact-checking, not verified incidents; identical text repeated across days is not counted as independent events.

## Outstanding research/editorial controls

- Gaps in report numbering are **unconfirmed publications** until official primary-source evidence establishes whether those report numbers were issued.
- Historical PDFs use changing table layouts and table numbers. Partially extracted rows stay quarantined and must never be labelled a fully validated provincial/health-zone history.
- Original source PDFs for the current 158-document primary registry have confirmed SHA-checked versioned GitHub Releases; retain independent backups for custody resilience.
- The AI editorial event register and daily/weekly/monthly bulletins require separate review and publication approval.
- The live One.com dashboard remains unchanged until historical coverage and source labels are suitable for public consumption.

**Do not interpret `publication_qa.pass=true` as a claim that every historical SitRep table has been recovered.**
