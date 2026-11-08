# AFRICAN INTELLIGENCE — BDBV SITREP INGESTION OPERATIONS

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
