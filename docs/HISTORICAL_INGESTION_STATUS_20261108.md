# AFRICAN INTELLIGENCE — BDBV 2026 HISTORICAL INGESTION STATUS

> **STATUS UPDATE — 8 November 2026:** This document captures an earlier implementation/review checkpoint. The subsequent [qualified historical evidence release](DATA_RELEASES.md) is now published (15,726 rows; 14,442 permitted for labelled descriptive use; 1,284 restricted). The [main README](../README.md) and [operations runbook](OPERATIONS_HANDOVER.md) describe the current ongoing scraper. Numerical source-cell and narrative-fidelity review remain separate and are not silently certified.


**8 November 2026**  
**Research policy:** source custody and full extraction first; numerical reconciliation second; research products and dashboards are out of scope until explicit QA approval.

## Source holdings

- **158** original SitRep PDFs are in the principal SHA-verified archive. Those cover **1,721 pages**, with full digital-text extracts, raster-image binaries and pinned INRB comparison data preserved in a durable GitHub Release.
- **Three additional scanned SitReps (007, 008, 009; 37 pages)** have been admitted to a **separate, versioned source-custody register**, with SHA-verified original PDFs and complete rendered-page sets. This is source admission, **not** yet full transcription or numerical validation. The 158-document machine-text extraction count remains unchanged until these scans undergo complete page-level review.
- SitRep numbering is substantially consistent with elapsed reporting days. Skipped numbers are not automatically source gaps.

## Numerical recovery: what works

**Pinned INRB historical daily series:** 31 files, 15,726 source rows staged with raw values, source CSV hashes, immutable upstream commit and provenance classifications; none is promoted automatically.

**National confirmed cases/deaths:** 316 original PDF-banner to INRB comparison candidates. Initial outcomes: 253 agreement candidates, 7 explicit differences, 14 possible one-day date alignments, 11 ambiguous PDF readings, 1 without a banner candidate, 30 without a same-date upstream value. See `docs/INRB_RECONCILIATION_RESULTS_20261108.md`.

**Health-zone cumulative cases/deaths:** 13,274 INRB candidate observations examined against parsed primary-source Table II rows. Outcomes:
- 3,988 same-value comparisons, still review-only;
- 46 differences;
- 174 ambiguous multiple PDF-row matches;
- 9,065 lacking a same-date directly parsed PDF Table II cell;
- 1 invalid upstream date.

Of the 46 differences, a subsequent date-neighbourhood review identifies **39 possible adjacent-day matches, one matching multiple adjacent dates, and six persistent differences**. These offsets are only leads; they never change the original reporting date.

**Source-page recovery for unparsed cells:** Of 9,065 missing direct matches, the original-PDF full-page search locates the same health-zone name on at least one same-date PDF page in **8,084 cases**; **583** have no same-date archived SitRep and **398** have no zone-name occurrence in extracted text. Page-name appearance is **not** proof of a reported numeric cell.

**Provincial table assessment:** 158 reports evaluated, yielding 854 province/metric review candidates. There are 96 matching Table I vs Table II provincial value comparisons; 692 with only one provincial source parsed; 66 without extracted provincial totals. By document: 22 without a parsed table snapshot, 67 without provincial rows, 67 with incomplete province crosschecks, and just 2 whose extracted provincial totals all agree across both tables. This is a major historical-format limitation, not a source-inventory integrity failure.

## Key real source discrepancy: SitRep 169

The original PDF (report date 30 October 2026) explicitly reports **10,414 confirmed cases and 5,372 confirmed deaths**, and describes an Ituri retrospective death harmonisation from **3,436 to 3,750** (+314). INRB's national death series records **5,058** for the same date: exactly 314 fewer. The PDF and INRB series therefore reflect differing revision states. See `docs/SITREP169_SOURCE_ADJUDICATION.md` for six visually checked Table II cell discrepancies. Do not merge the series without explicit revision provenance.

## Permanent evidence and review outputs

1. Full original-text and raster extraction, plus pinned national INRB comparison: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-source-extract-evidence-42474203980
2. Separate scanned-source custody for 007–009 (original PDFs, 37 page renderings and hashes): https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-scanned-sources-007-009-c00b8843
3. Historical health-zone concordance, unmatched PDF source candidates, date-triage ledger: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-historical-zone-review-42476718553
4. Historical province-versus-table consistency and complete report coverage audit: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-provincial-audit-42477293508

Source-page recovery leads remain reproducible via `locate_historical_zone_pages.py` and GitHub Actions run 42477117520; the outputs are currently in a retention-limited workflow artifact and should be archived in a follow-up evidence release.

## Remaining acceptance gates — NOT COMPLETE

1. Recover the **22** documents lacking a parsed table snapshot and **67** without extractable province rows, using format-specific parsing or carefully labelled manual visual transcriptions.
2. Resolve or explicitly retain the **174** duplicate-row ambiguities and all national/cell discrepancies; matching another date is not an automatic correction.
3. Extract and verify *all content and relevant table cells* from the **37 scanned pages** of SitReps 007–009, preserving original layout and OCR uncertainty; only then merge into the main audit corpus.
4. Implement cell-level, page-linked human or independently cross-checked adjudication of all historical high-value measurements; a successful pipeline is not a certificate of historical table fidelity.
5. Archive the latest zone page-locator outputs durably and continue versioning new corrections without rewriting evidence.

**Bottom line:** successful reproducible comparison and permanent source custody, but historical Table II recovery and visual cell-level approval remain the research bottleneck. All current health-zone/province comparison results remain **review-only**.
