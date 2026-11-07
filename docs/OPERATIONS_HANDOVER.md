# AFRICAN INTELLIGENCE — BDBV SITREP INGESTION OPERATIONS

**System:** `AriesConsult/african-intelligence-sitrep`  
**Revision:** 7 November 2026  
**Boundary:** GitHub acquisition, numerical and narrative classification, source verification and release archiving. The existing One.com observatory, forecasting models and literature portal are *not* modified.

## Workflow and destinations

The regular workflow `.github/workflows/bdbv-sitrep-pipeline.yml` executes:
1. Test the Python code against real archived SitRep extracts.
2. Discover official 2026/17th-epidemic SitReps and register original source SHA-256 hashes.
3. Reprocess the table extraction queue with per-table reconciliation; never replace the INRB cases/deaths baseline.
4. Reprocess hash-verified narrative candidates. The first complete backfill covers the full historical catalogue; daily runs check the latest reports.
5. Compile review-only longitudinal themes and exact-repeat signals.
6. Write the integrity audit, then run the **independent publication gate**.
7. Commit validated results only if the branch has not advanced. Never force-push over newer evidence.

The separate workflow `.github/workflows/bdbv-source-archive.yml` creates immutable GitHub Release assets containing unmodified source PDFs, each checked against its recorded SHA-256. It updates `published/source_archive_index.json` only after a release has been created successfully. It runs monthly and on manual dispatch. It archives only new report/hash identities.

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
- Original source PDFs must be present in confirmed immutable releases before long-term source preservation is certified.
- The AI editorial event register and daily/weekly/monthly bulletins require separate review and publication approval.
- The live One.com dashboard remains unchanged until historical coverage and source labels are suitable for public consumption.

**Do not interpret `publication_qa.pass=true` as a claim that every historical SitRep table has been recovered.**
