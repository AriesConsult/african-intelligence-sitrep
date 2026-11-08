# INRB–INSP SitRep source and numerical reconciliation protocol

Status: PROPOSED; no INRB-derived numerical value is approved for the African Intelligence public feed by this document.

## Source roles

1. **Primary evidence:** original INSP SitRep PDF, identified by original byte SHA-256, publication/report date and report number.
2. **Parallel curated transcription:** INRB-UMIE/BDBV2026-Data `data/insp_sitrep/processed/` CSVs, pinned to a Git commit SHA. This is generally a transcription of the SAME SitRep evidence, not independent epidemiological confirmation.
3. **Additional contextual evidence:** `data/insp_sitrep/reports/` digitiser notes, `data/public_health_response/` narrative data and INRB datasets not derived directly from PDFs. Explicitly flag values furnished directly by INSP to INRB.
4. **Our machine extraction:** source-hash-linked PDF page text, table bounding boxes and candidate records, each retaining the original raw cell.

Never silently use the curated transcription to overwrite the PDF or promote an unverified observation.

## Inventory findings (8 November 2026)

- INRB Git tree: 144 PDF filenames with 143 distinct SitRep numbers (SitRep 012 and 012_v2).
- INRB processed numerical files: 31 daily indicator CSVs.
- INRB per-SitRep digitisation notes: 133 Markdown files.
- INRB operational-response processed CSVs: 54.
- Source numbers in INRB PDFs and absent in the current African Intelligence registry: 007, 008, 009.
- Source numbers in African Intelligence registry but not INRB PDF tree: 061, 063, 068, 071, 086, 087, 088, 090, 092, 098, 103, 105, 107, 158, 159, 160, 161, 163.
- The absent numbers are source-discovery leads, not automatic missing-report flags.
- Check versions and authenticity of 007–009 using PDF cover identity, date, size and SHA before incorporation.

## Observation ledger: immutable candidates and review status

Each candidate row should include:

`source_pdf_sha256, source_report_number, report_date, publication_date, pdf_page, table_id, cell_bbox, row_label_raw, column_label_raw, raw_text, metric_id, unit, geography_raw, geography_canonical, grain, value_raw, value_parsed, missingness_code, extraction_method, extraction_version, validation_flags, validation_status`.

INRB comparison separately records:
`inrb_repo_commit_sha, inrb_csv_path, inrb_csv_row_key, inrb_value_raw, inrb_digitisation_note_path, inrb_transformation_class, inrb_independence_class`.

A canonical observation key is:
`(source_report_identity, reporting_date, metric_id, geography_grain, geographic_identifier, period_definition, measurement_type)`.
One report can contain a different reference period for a daily figure than its cover reporting date. Record the reference period separately.

## Transformations and fidelity statuses

- `DIRECT_PDF`: value and headers transcribed from a traceable PDF cell/banner.
- `CARRIED_FORWARD`: previous value propagated, not directly reported at current date.
- `DERIVED_SUM`: inferred from zone aggregates or two national components.
- `EXTERNAL_TO_PDF`: data delivered separately to INRB/INSP, not visible in archived SitRep.
- `ND`: not reported. Never convert ND, blank or absent to zero.
- `REVISION`: changed historical value in a revised SitRep.
- `UNRESOLVED`: missing source attribution or discrepancy.

Concordance outcomes:
`EXACT_MATCH, DIFFERENCE, DATE_ALIGNMENT_REQUIRED, PROVINCE_MAPPING_REQUIRED, SOURCE_VERSION_DIFFERENCE, TRANSFORMATION_DIFFERENCE, INRB_ONLY, PDF_ONLY, INSUFFICIENT_PROVENANCE`.

Only exact same-grain, same-period, same-definition DIRECT_PDF values can be compared cell-for-cell. Never compare a carried-forward or derived value as if it were a verbatim source cell.

## Verification and quality gates

**Gate 0 — source integrity:** independently hash every source PDF, identify revisions and pin the INRB commit. Confirm primary-source identity before using INRB-only reports.

**Gate 1 — extraction preservation:** retain unmodified cell text, table structure, page/bbox and original PDF identity. OCR is a separately labelled fallback only when visually necessary.

**Gate 2 — deterministic rules:** parse dates, numerals, percent signs, nonstandard thousands separators, ND and NA; enforce case/death nonnegativity, valid rate bounds and denominators when available. Cumulative revisions are possible; do not require monotonicity.

**Gate 3 — dual-path concordance:** reconcile our PDF-derived candidate with INRB manual digitisation at identical geographic granularity, unit and reference period. Pin and record the upstream INRB revision.

**Gate 4 — source adjudication:** for disagreements, compare the original PDF page, identify split cells, spanning headers, unallocated deaths, missing provinces and changed report versions; resolve with explicit reviewer note. Prefer original PDF for verbatim values; preserve INRB's separately sourced values with their own provenance.

**Gate 5 — publication:** only fully reconciled source-linked numerical observations may enter an approved dataset. Discrepancies and unmatched observations remain in review queue and appear in coverage reports.

## Important cautions grounded in INRB's documentation

INRB's README explicitly describes:
- Manual transcription and use of the national banner as first choice for national totals.
- Health-zone cumulative values sometimes carried forward when not reported.
- National suspected counts sometimes summed from components.
- Occasional health-zone records supplied directly to INRB by INSP, which may not appear in public PDFs.
- Revision replacement when a SitRep is updated.
- ND as distinct from zero.
- Geographic aliases, including non-geographic rows `NA` and `Sans Fiche`.

One report note for SitRep 175 says “05th October, 2026”, although the corresponding national CSV row and our primary SitRep registry refer to 5 November 2026. Treat it as a suspected metadata typo pending cover verification; do not shift dates automatically.

## Initial comparison and reporting outputs

Create separate, *review-only* files:
- `source_inventory_crosswalk.csv`: reports, versions, dates and hashes present in either repository.
- `observation_candidates.parquet` (or JSONL): original PDF rows plus provenance and QA flags.
- `inrb_comparison.csv`: metric-grain-date aligned comparisons and divergence reasons.
- `adjudication_ledger.csv`: human-confirmed resolutions, source page, reviewer and date.
- `coverage_matrix.csv`: report by metric/granularity/source status with missingness explicit.

Start with national cumulative confirmed cases/deaths and the 3 most recent fully structured reports, then extend to one SitRep from each historical table-layout regime. Do not limit the final inventory to the five known tables or the 31 INRB metrics.

Sources:
- https://github.com/INRB-UMIE/BDBV2026-Data/tree/main/data/insp_sitrep
- https://github.com/INRB-UMIE/BDBV2026-Data/tree/main/data/public_health_response
- https://github.com/AriesConsult/african-intelligence-sitrep
