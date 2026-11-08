# INRB–PDF RECONCILIATION — FIRST REPRODUCIBLE RESULTS

**Run:** https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42474203980  
**Status:** All jobs succeeded. Reconciled observations remain **REVIEW ONLY**, never auto-approved.  
**INRB pinned commit:** `c00b8843e6ebae8f0cd846bc43cb564a3893bfd9`.  
**Source:** INSP original SitRep PDFs; parallel manual INRB transcription is not an independent primary epidemic measurement.

## National banner results

Using archived, SHA-256-verified originals and the first-page coordinate-aware extraction, the workflow tested **316** cases/deaths candidates (two national cumulative indicators × 158 documents).

| Outcome | Comparisons |
|---|---:|
| Candidate agrees with same-date INRB value, awaiting visual QA | **253** |
| Difference requiring source review | **7** |
| One-day reporting-date alignment possible, unapproved | **14** |
| Ambiguous PDF number candidate | **11** |
| No PDF banner candidate | **1** |
| No INRB value on matching registry date | **30** |

The comparison is **not** evidence of 253 human-reviewed, research-grade observations. No INRB value enters the approved African Intelligence feed from this comparison.

### Seven differences to adjudicate

| SitRep | Registry report date | Indicator | Extracted PDF candidate | INRB value | Reading priority |
|---|---|---|---:|---:|---|
| 004 | 2026-05-19 | Cumulative confirmed cases | 30 | 51 | Verify original early-layout banner and reference date |
| 086 | 2026-08-08 | Cumulative confirmed cases | 4,294 | 4,209 | Compare cover/reporting-period differences |
| 086 | 2026-08-08 | Cumulative confirmed deaths | 1,960 | 1,916 | Compare cover/reporting-period differences |
| 103 | 2026-08-25 | Cumulative confirmed deaths | 2,744 | 2,755 | Verify PDF and transcription revision |
| 150 | 2026-10-11 | Cumulative confirmed cases | 9,065 | 9,066 | Inspect source number and historical revision |
| 168 | 2026-10-29 | Cumulative confirmed deaths | 14 | 5,026 | **Likely incorrect panel/number candidate**; do not substitute upstream value without source check |
| 169 | 2026-10-30 | Cumulative confirmed deaths | 32 | 5,058 | **Likely incorrect panel/number candidate**; do not substitute upstream value without source check |

Fourteen one-day-alignment flags arise in reports 020, 050, 114–116, 118 and 141 (both cases and deaths). Date alignment is a **hypothesis**, not a correction.

## Complete INRB indicator staging

The separate staged collection includes:
- **31** daily CSV metric files, pinned by Git commit and source file hash.
- **15,726** original CSV rows retained in a compressed observation candidate ledger.
- **15,361** numeric values that remain unverified.
- **361** ND / not-reported values, preserved separately from zero.
- **2** unparseable values and **2** other blank/not-applicable values.
- **1** invalid upstream CSV date: `2026-06-25]` in `cumulative_confirmed_cases`; retain raw value and flag, do not silently correct.
- Three upstream metric files have a different measure column label than their filename; source column name is preserved.

These files contain direct transcriptions *and* curated/derived/carried-forward values. The flags and original INRB documentation must travel with every candidate.

## Source catalogue reconciliation

INRB has **144 PDF files representing 143 report numbers** (including two versions of 012). Our current primary archive has **158 report numbers**. Three historical reports — **007, 008, 009** — appear in INRB but not in our archive, and 18 in ours are absent from INRB's current raw-PDF tree.

The three additional PDFs have been SHA-256 downloaded, opened and visually reviewed at the cover page. Their covers identify the 17th Ebola outbreak and the respective report numbers/dates. They are scanned/image-based and require page-level structural ingestion before joining the 158-document verified corpus. See `docs/INRB_SITREPS_007_009_VISUAL_REVIEW.md`. Do **not** add bare registry rows: archive originals and register extracts/queues in one coherent operation.

## Next work to establish genuinely source-verifiable historical tables

1. Adjudicate seven differences and 14 date flags against source PDF page renderings and INRB transcription notes.
2. Use the pinned INRB candidate ledger to guide recovery of historical province/health-zone rows. Preserve `ND`, row/column headers, names, periods and split-table provenance.
3. Match values to PDF cell coordinates *only after* checking same indicator, time window and geographical grain. Distinguish PDF-reported, INRB-carried-forward, INRB-derived and INRB-external values.
4. For 007–009, preserve scanned pages, apply separately labelled transcription or OCR-assisted review, audit originals and formally onboard the accepted report/hash identities.
5. Preserve the extracted corpus and these review ledgers beyond 90-day Actions retention; do not mistake an Actions artifact for permanent archival.
6. Release approved observations only after documented source-cell fidelity verification.

## Reproducible material

Workflow artifact `bdbv-inrb-reconciliation-42474203980` contains `national_banner_comparison.csv`, `national_banner_comparison.json`, `inrb_source_crosswalk.json`, `staged/inrb_staging_summary.json`, all 31 input source CSVs and `staged/inrb_observation_candidates.jsonl.gz`.
