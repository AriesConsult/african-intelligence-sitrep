# AFRICAN INTELLIGENCE — BDBV 2026 HISTORICAL CORPUS, INCREMENTAL INTAKE & NARRATIVE AUDIT

> **STATUS UPDATE — 8 November 2026:** This document captures an earlier implementation/review checkpoint. The subsequent [qualified historical evidence release](DATA_RELEASES.md) is now published (15,726 rows; 14,442 permitted for labelled descriptive use; 1,284 restricted). The [main README](../README.md) and [operations runbook](OPERATIONS_HANDOVER.md) describe the current ongoing scraper. Numerical source-cell and narrative-fidelity review remain separate and are not silently certified.


**Evidence checkpoint:** 8 November 2026, Nairobi. **Status:** Operational source and analysis-preparation infrastructure, **not** final source-cell certification of the complete epidemic dataset.

## 1. Coherent historical data

Version-pinned INRB-UMIE revision `c00b8843e6ebae8f0cd846bc43cb564a3893bfd9` is frozen as **31 daily metric files**, containing **15,726 original rows**. Historical assembly yields **15,276 single-source numerical candidates**, 361 explicit `ND` records, 84 unallocated geographical records, four other nonnumeric/missing records, one invalid date, and 114 downward changes in cumulative indicators. All are retained without imputation or invented incident dates.

PDF evidence alignment produces one record per original upstream row, with the INRB value **kept separate** from source-PDF candidates:

- 4,098 PDF candidate matches pending source review;
- 130 concordance candidates against machine-validated Table II rows still pending visual QA;
- 56 PDF–INRB differences pending adjudication;
- 174 ambiguous row matches;
- 9,042 PDF evidence unresolved cases;
- 1,764 INRB-vintage-only records without a direct PDF-cell link;
- 12 ambiguous multiple concordance records;
- Remaining rows preserve ND, missingness and geographical uncertainty.

**No new value was automatically promoted** into the production outbreak feed.

**Analyst-readable output:** a **15,726-row long-form CSV** with provenance, original value and source row, candidate PDF page/table, reported date, evidence class and `approved_for_analysis=FALSE`. This is not a finalized incidence dataset, nor a retrospective correction to every original SitRep figure.

Releases:
- Original frozen historical series: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-historical-assembly-42479820408
- Original PDF evidence alignment: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-historical-aligned-42482026260
- Full CSV and data dictionary: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-historical-review-csv-42482484265
- Source identity and numeral discrepancy records: https://github.com/AriesConsult/african-intelligence-sitrep/blob/main/docs/HISTORICAL_INGESTION_STATUS_20261108.md

## 2. Future SitRep ingestion

The existing daily ingestion workflow continues at 08:27 East Africa Time; immutable original-PDF source archiving runs at 09:10. A separate source-change audit has been implemented for **09:55 EAT daily**, using the 158-record immutable historical source freeze `state/historical_source_freeze_20261108.json`.

The new audit detects:
- newly published source PDF identities;
- revised source PDF bytes for an existing report number;
- missing frozen historical source identities (blocking error);
- absent table/narrative snapshots and unverified original-page fidelity.

Any changes remain review-only and cannot rewrite the accepted historical source hash set. GitHub QA: https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42482128386

The existing pipeline can still publish its *separately machine-validated, explicitly limited* operational metrics; the new INRB historical staging and narrative comparison do **not** alter that feed.

## 3. Narrative source completeness

Original extraction:
- 158 SHA-verified digitally readable PDFs (1,721 pages), approximately 5.63 million original digitally extractable page-text characters;
- 4,569 earlier selected narrative candidate fragments, of which **2,151 are truncated excerpts** (not truncated source PDF text);
- all original digital page text retained in a permanent release, with a per-page hash and document identity;
- 6,351 mechanical heading leads in the narrative coverage audit;
- lossless reconstruction into **4,744 candidate text sections** with **4,586 numbered heading candidates**, retaining all source characters (page separators explicitly retained).

Three additional SitReps 007–009: source PDF hashes independently archived, **37/37 scanned pages OCR-processed**, 10,306 OCR words, and **178 provisional OCR narrative sections**. OCR results are *not* human-verified transcriptions. Thus source materials now cover **161 original report identities**, with different fidelity statuses by report.

Releases:
- Full original-text narrative audit: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-narrative-coverage-42481834054
- Lossless digital narrative section candidate text: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-narrative-sections-42482331705
- Scanned original images: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-scanned-sources-007-009-c00b8843
- Scanned OCR text and word confidence: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-scanned-ocr-42482358347
- Source-linked scanned narrative candidates: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-scanned-narrative-sections-42482633789

## 4. INRB operational narratives — critical completeness qualification

All **54** pinned INRB French/English public-health-response CSVs have been archived, including **3,116 text rows**. The staging flags **44 invalid source dates**, two empty text fields and 241 rows whose valid source dates have no same-date registered machine-text original. These totals measure source rows and must not be confused with distinct events or independent reports; many entries occur in translated EN/FR pairs.

Direct PDF text comparison is necessarily conservative:
- 1,542 English-language records are translated, not directly suitable for verbatim French PDF matching;
- 118 French records have literal 12-word phrase windows located in same-date original PDF pages (not full-section validation);
- 1,211 French records have no such literal match; these may be INRB paraphrases, edited texts, misaligned dates or extraction omissions — **not proven missing narratives**;
- 119 records have no same-date original PDF in the digitally extracted set;
- 81 excerpts are too short for reliable verbatim detection;
- 44 source dates are invalid;
- one source text record is empty.

Some source-pillar labels appear overly broad or mixed, and they are retained without being treated as verified event categories.

Releases:
- INRB operational source CSVs and candidates: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-inrb-narrative-source-42482757259
- French PDF-page source leads and translation exceptions: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-narrative-comparison-42482905395

## 5. Outstanding *scientific* acceptance gates

The project is **not** done merely because the GitHub workflows succeeded.

1. Adjudicate the 114 cumulative decreases and 56 historical PDF–INRB discrepancies, beginning with source revisions; do not use daily differences of corrected cumulative totals as true daily cases without reconstructing revision scope.
2. Validate complete health-zone/province crosswalks, outlying geography labels, period definitions, carried-forward values and unallocated rows against primary evidence.
3. Resolve historical PDF-table extraction gaps using format-specific parsing and selected manual source-page reviews, without rewriting original evidence or inventing ND as zero.
4. For the scanned 007–009 records, perform human QA on OCR rows and table cells, then formally merge into the main source-to-extraction registry and re-audit 161 documents.
5. For narrative sections, human-check section boundaries, page reading order, continuation across pages and table/footnote handling; inspect unmatched INRB narratives without assuming paraphrase absence equals omitted primary-source content.
6. Release an explicitly accepted historical analytic series only when supported by a signed/dated adjudication ledger, reproducible provenance and documented coverage by indicator/geography/time. It must remain separate from this provisional source-preserving archive.

**Do not describe the reviewed source corpus as complete, independently corroborated, error-free or ready for unrestricted epidemiological inference.** Its major advantage is now deterministic reproducibility of the available evidence and explicit identification of what remains unresolved.
