# African Intelligence — BDBV 2026 SitRep evidence pipeline

**Status (8 November 2026): operational scheduled discovery, original-PDF archiving, review-controlled extraction and qualified historical evidence release.** This repository is a reproducible research evidence pipeline; it is **not** a claim that every historical provincial/health-zone table, narrative section or epidemiological estimate has been independently verified.

The principal operational objective is to **keep collecting new INSP SitReps reliably**, preserve source PDF bytes and hashes, and detect revisions without replacing the historical evidence. Historical numerical and narrative fidelity can be improved incrementally through explicit versioned review.

## At a glance

| Layer | Current verified state | Use |
| --- | --- | --- |
| Core scraper and intake | Latest reviewed scheduled GitHub Action succeeded **8 Nov 2026**; checks discovery, PDF identity, table/narrative extraction and publication QA | Ongoing ingestion, subject to job status and source availability |
| Original SitRep archive | **158** catalogued machine-extracted PDFs / **1,721** pages, original hashes and durable releases | Primary source evidence |
| Supplemental scanned originals | SitReps **007–009**, **37** pages, preserved and OCR-processed; numerical transcription **not verified** | Archive and review only |
| Operational feed | **27** QA-verified machine observations across **five** operational indicators, in `published/feed.json` | Limited existing operational feed, **not** the full historical dataset |
| Historical evidence release | **15,726** pinned INRB-curated records, **31** indicators; **14,442** qualified for labelled descriptive use and **1,284** restricted | Historical descriptive research under published acceptance rules |
| Original PDF visual checks | **17** individually documented verbatim numerical readings; 13 of these differ from corresponding INRB values | Source-specific *as reported* evidence; not independent epidemiological validation |
| Narrative evidence | Full digitally extractable page text preserved; **4,744** heuristic section segments and separately labelled scanned OCR segments | Narrative-completeness verification in a **separate** research track |

**Important:** Workflow success verifies that its coded checks passed. It does not certify all historical observations. The source PDF, INRB-curated value, any corrections and the relevant report date remain distinguishable.

## Start here

- **[Operations and runbook](docs/OPERATIONS_HANDOVER.md)** — scheduled jobs, safe manual runs, failure and revision handling.
- **[Quality gates](docs/QUALITY_GATES.md)** — source, numerical and narrative certification requirements.
- **[Historical acceptance and release catalogue](docs/DATA_RELEASES.md)** — download links, accepted use, explicit restrictions and provenance.
- **[Scientific evidence gate](docs/SCIENTIFIC_CERTIFICATION_EVIDENCE_GATE_20261108.md)** — remaining verification limitations.
- **[Historical implementation checkpoint](docs/IMPLEMENTATION_CHECKPOINT_20261108.md)** — extraction methods, audits and narrative progress.
- **[Review queue](review_queue/README.md)** — how to check or approve a specific original PDF cell.

## How the scraper works

`discovery.py` searches public **INSP** listings/WordPress media and the **INRB-UMIE/BDBV2026-Data** PDF archive as a secondary discovery source. Official INSP PDFs are preferred where available. `run_pipeline.py` downloads candidates, checks the **2026 / 17th-outbreak** identity, rejects report-number mismatches, computes SHA-256 hashes, records source/report-date provenance and creates reviewable table candidates.

- An already registered identical PDF hash is not re-ingested.
- A changed PDF hash for an existing report is a **new revision**, not permission to overwrite earlier figures.
- Missing source, malformed cover, unconfirmed reporting date, ambiguous table cell, `ND` or unallocated geographic values remain explicit exceptions.
- A successful scraper run does **not** imply all historic source reports were published, found or fully extracted.
- Nothing in the qualified historical release automatically changes the existing African Intelligence / One.com website or forecasting models.

## Scheduled automation (UTC; Nairobi = UTC+3)

| Workflow | Schedule | Role |
| --- | --- | --- |
| [Main SitRep ingestion](.github/workflows/bdbv-sitrep-pipeline.yml) | Daily **05:27 UTC / 08:27 EAT**; separate Sunday full backfill at 04:41 UTC / 07:41 EAT | New/revised report discovery; extraction, table/narrative QA, bounded operational publication gate |
| [Original-PDF source archive](.github/workflows/bdbv-source-archive.yml) | Daily **06:10 UTC / 09:10 EAT** | Durable SHA-checked original-PDF GitHub Releases |
| [Future source-change control](.github/workflows/bdbv-future-change-control.yml) | Daily **06:55 UTC / 09:55 EAT** | Compare registry with frozen historical identities; flag new/revised sources |
| [Qualified historical acceptance](.github/workflows/bdbv-qualified-historical-acceptance.yml) | Manual or relevant code changes | Rebuild versioned qualification / exclusions from frozen historical evidence |

GitHub-hosted scheduled executions can start late; check **Actions** for the actual latest run and conclusion. The three daily workflows are independently scheduled, not an atomic dependency chain, so check timestamps before assuming the same-day archive and QA both refer to the latest ingestion.

Successful observed workflow examples:
- [Daily scraper, extraction and publication checks (8 Nov 2026)](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42478204067)
- [Original source archive](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42484149332)
- [Future change-control test](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42482128386)
- [Qualified historical acceptance](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42498372593)

## Run or verify locally

Run from the **repository root**, not from an obsolete `sitrep_pipeline/` subdirectory:

```bash
python3 -m pip install -r requirements.txt pytest reportlab
python3 -m pytest -q tests

# Review the most recent discoverable SitReps without a full historical backfill.
python3 run_pipeline.py --limit 12 --work work

# Broader source discovery/backfill (network intensive).
python3 run_pipeline.py --limit 0 --work work

# Recompute local source/table and narrative audits.
python3 reprocess_tables.py
python3 backfill_narratives.py --limit 0
python3 build_narrative_signals.py
python3 audit_ingestion.py
python3 audit_source_to_extraction.py
python3 verify_publication.py

# Compare present source inventory against the historical identity freeze.
python3 audit_future_ingestion.py --out work/future_qa
```

**Caution:** `run_pipeline.py` and reprocessing commands can update local `state/`, `published/` and `review_queue/` files. Use a clean working branch or Actions for routine execution. Avoid committing generated observations without the independent publication QA.

## Important paths and their meaning

| Path | Role |
| --- | --- |
| `state/registry.json` | Report number, date, SHA and original PDF source metadata |
| `state/historical_source_freeze_20261108.json` | Original 158-PDF historical source identities; never silently rewrite |
| `published/source_archive_index.json` | Durable archived source assets, hashes and releases |
| `published/scanned_source_index.json` | Separate, unverified scanned-original source custody for 007–009 |
| `review_queue/report_*.json` | Raw candidate PDF table cells requiring review |
| `reviewed/approved_observations.csv` | Explicitly reviewed individual source cells, subject to validation |
| `published/tables/` and `published/table_index.json` | Per-report table snapshots and coverage |
| `published/feed.json` | Separately gated, bounded operational indicators, **not** the 31-metric historical research series |
| `published/narrative_candidates/`, `published/narrative_index.json` | Selected excerpt and thematic review material |
| `published/ingestion_audit.json`, `published/publication_qa.json` | Core ingestion and publication safety audit |
| [Qualified historical GitHub Release](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-qualified-historical-42498372593) | Complete long-form historical CSV, tier decisions, exclusions and final acceptance report |


## Daily, weekly and monthly outbreak bulletins (no AI)

The first deterministic source-led bulletin backfill completed successfully on **9 November 2026**: **129 daily**, **26 ISO-weekly** and **7 monthly** editions (162 EN/FR publication periods). It reads the frozen, qualified historical release plus newly staged version-pinned INRB GitHub observations, preserving historical exclusions and indicating where cumulative totals cannot support incidence claims.

- [Bulletin pipeline documentation, source rules and site deployment](docs/BULLETINS.md)
- [Initial GitHub bulletin release, including One.com upload ZIP](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-rulebased-bulletins-c00b8843e6eb-897fa8e99a64)
- [Automated generation workflow](.github/workflows/bdbv-bulletins.yml) — **07:25 UTC / 10:25 EAT daily** (subject to scheduling delay)
- Generated site assets: `/bdvd2026/assets/data/bulletins_public.json`, `contact_tracing_public.json` and `weekly_national_public.json` plus bilingual HTML bulletins.

The GitHub generation and archive runs are working; **automatic FTPS deployment to One.com is optional and disabled until the site owner configures FTPS credentials**. No credentials are committed or shown publicly. Bulletins are labelled automated, not independently expert-reviewed.

## Historical acceptance policy

The 8 November 2026 qualified historical release retains **every** of the 15,726 curated records; it does **not** certify all of them as epidemiological truth.

- **Tier A:** 3 unrestricted-by-this-policy as-reported PDF/INRB concordant descriptive observations (still not independent epidemiological validation).
- **Tier B:** 4,222 PDF/INRB machine concordance candidates, **provisional descriptive use**.
- **Tier C:** 10,217 pinned INRB-curated candidates, **provisional descriptive use**.
- **Restricted:** 1,284 records excluded from the qualified descriptive pool; all remain preserved for audit. Includes numerical ambiguity, unadjudicated cumulative declines, missingness, competing verified-source figures and unverified records on scanned-source dates.
- **No row** is approved by this release for blindly differencing cumulative data into daily incidence. The 114 historical cumulative-decrease events are flagged and excluded from that use.
- Narratives remain on a **separate** completeness and fidelity track. The 37 scanned pages remain source archived; OCR is review-only.

The acceptance report and restrictions are in the [release catalogue](docs/DATA_RELEASES.md). For a scientific paper, explicitly state the chosen tier, source version, exclusions and endpoint-specific validation—not just “verified SitRep data.”

## Licensing, provenance and safeguards

This project preserves and indexes publicly available third-party SitReps for research. Original reports remain attributable to their publishing organisations; no INSP/INRB endorsement is implied. GitHub Releases are durable versioned preservation assets, not immutable against repository deletion or changes in external hosting; maintain an independent backup if long-term custody is essential. Public raw narratives can include named people and contact details; use access-controlled review workflows where appropriate.

**Current operating priority:** keep **daily discovery → original-PDF archival → revision checks** functioning. Improve historical cells and narrative completeness through distinct, versioned evidence updates without destabilising the scraper or replacing original source measurements.

## Bulletin delivery

The bilingual daily, weekly and monthly bulletin build is documented in [docs/BULLETINS.md](docs/BULLETINS.md), including complete-source-paragraph display and the optional GitHub Actions → One.com FTPS deployment. The deployment is disabled by default until hosting credentials and the remote root are configured. A GitHub Release ZIP remains available for manual upload and rollback.

## BDBV weekly/monthly AI assessment drafts and SFTP publication

The source bulletins now produce [daily evidence → ISO-weekly/monthly review packs](docs/BULLETINS.md), with an optional **private, editorial-review-required** AI draft workflow. There is no automatic AI publication. The approved site delivery route is One.com SFTP on port 22 with pinned SSH host key, not FTP; configuration and operational safeguards are documented in [docs/BULLETINS.md](docs/BULLETINS.md).

## Current BDBV publication architecture (10 November 2026)

**GitHub generates versioned source-only bulletins and analytical evidence JSON; One.com performs HTTPS pulls and runs the existing website AI protocols.** There is no GitHub AI call and no SFTP/FTPS deployment in the active bulletin workflow. The GitHub ZIP contains a per-file SHA-256 manifest, daily evidence, ISO-week and monthly evidence packs. The website-side synchronizer/editorial approval integration is pending; use manual ZIP upload until implemented. See [docs/BULLETINS.md](docs/BULLETINS.md) (10 November section). Earlier references to SFTP and GitHub AI in this README describe superseded architecture.
