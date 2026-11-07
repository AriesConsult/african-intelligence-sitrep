# BDBV 2026 SITREP SCRAPER — PROTOTYPE, REVIEW-ONLY

This is a **real automated PDF discovery, download, archiving, and table-extraction prototype**, not a published dashboard data feed. The supplied GitHub Actions workflow runs at 08:25 Nairobi time daily (GitHub Actions schedules can be delayed), and on manual request. It saves a review ZIP as a workflow artifact. It performs **no changes to the African Intelligence website** and **does not publish extracted figures automatically**.

## Inputs and source hierarchy

1. INSP official publication PDFs listed through `https://insp.cd/sitrep/`, the 17th-epidemic page, and the public WordPress media API.
2. `INRB-UMIE/BDBV2026-Data` GitHub `data/insp_sitrep/raw/` files as systematic secondary discovery and archive. Git LFS fallback is implemented.

The pipeline ignores INSP links outside `/wp-content/uploads/2026/`. After download it checks the PDF cover for **2026** and the **17th epidemic / BDBV**, to avoid mixing in the 2025 16th-epidemic PDFs also hosted on INSP. A report-number mismatch also blocks ingestion.

## Running locally

```sh
python3 -m pip install -r sitrep_pipeline/requirements.txt
python3 sitrep_pipeline/ingest.py --out sitrep_pipeline/output --limit 8
```

For an initial backfill: use `--limit 0` and review network load / rate limits. The downloader respects a pause of at least 1.25 seconds between reports by default. To test with existing downloaded PDFs, use `--offline-dir path/to/pdfs`.

## Outputs

- `source_pdfs/`: copies of the original reports with SHA256 hashes in filenames.
- `unverified_extractions/`: page text and candidate tables with table cells, table titles, page numbers, approximate bounding boxes and simple indicator classifications. Text extraction can be incomplete; **no OCR is performed**.
- `unverified_table_cells.csv`: candidate numeric cells with source-page and table identifiers, raw value, column label and `REVIEW_REQUIRED` status. It is a convenient reviewer worksheet, **not an epidemiological timeseries**.
- `review_manifest.json`: source URL, report number, checksum, extraction status and errors.

## Critical limitations

- The INSP site sometimes uses embedded PDF viewers, pagination or access controls; discovery from the INRB archive is a fallback. The workflow warns when a source fails.
- WordPress PDF media search and Git LFS download must be tested from the selected GitHub runner before treating discovery as complete.
- SitRep tables have merged cells, varying headers and retrospective corrections. `pdfplumber` finds candidate tables, **not validated epidemiological figures**; none is currently mapped to definitive dashboard indicator fields.
- Contact follow-up must retain numerator, denominator, date and reporting window. Missing values cannot be interpreted as zero, and successive snapshots cannot automatically be differenced as incidence.
- Full backfill, schema harmonisation, rate/denominator checks, audit log, manual override screen, safe auto-publication of high-confidence observations, and a PHP dashboard JSON endpoint are **next stages**.

Before connecting this pipeline to the live dashboard, implement a reviewer approval step and publish only verified data. Keep the original INRB national series as the authoritative baseline for confirmed cases/deaths.
