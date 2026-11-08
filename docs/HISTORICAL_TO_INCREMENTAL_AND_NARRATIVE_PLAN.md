# BDBV 2026 — HISTORICAL DATASET ACCEPTANCE BEFORE FUTURE INGESTION

> **STATUS UPDATE — 8 November 2026:** This document captures an earlier implementation/review checkpoint. The subsequent [qualified historical evidence release](DATA_RELEASES.md) is now published (15,726 rows; 14,442 permitted for labelled descriptive use; 1,284 restricted). The [main README](../README.md) and [operations runbook](OPERATIONS_HANDOVER.md) describe the current ongoing scraper. Numerical source-cell and narrative-fidelity review remain separate and are not silently certified.


**Decision date:** 8 November 2026. **Scope:** African Intelligence's full SitRep evidence corpus.

## Sequence (binding research workflow)

**Phase A — coherent, most-complete defensible historical data (first).** Use version-pinned INRB curated values and our checksum-verified original INSP SitReps. Archive as separate layers:
- `source_pdf_as_reported`: original numerical values with PDF hash, page, table, raw cell, reporting date and extraction/review status;
- `inrb_curated_at_commit`: INRB's transcribed, carried-forward, calculated or externally supplied values *as present in a particular Git revision* (not necessarily the latest retrospective estimate);
- `historical_best_supported`: proposed reconciled view, choosing among documented vintage/revision candidates with reviewer decision and uncertainty/status. Never use later cumulative counts to invent earlier daily incidence;
- `revision_ledger`: when and why reported values change, including SitRep source/release date and impact at national, provincial, zone grain.

The first `inrb_curated_at_commit` layer is operational: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-historical-assembly-42479820408 (15,726 source rows; 31 metric files; 114 cumulative-decrease review flags). It is **not** already a certified `historical_best_supported` dataset.

Pass acceptance gates:
1. Resolve or explicitly classify all source mismatches, invalid dates and source revisions without overwriting evidence.
2. Reconcile national to provincial to health-zone values where all underlying parts are available, preserving `ND`, `NA`, unallocated deaths and source-level mismatches.
3. Document where original historical PDF cell reconstruction is unnecessary because revised source evidence explicitly supersedes it, while retaining the as-reported PDF when surveillance chronology matters.
4. Provide report × date × geography × indicator coverage matrix with statuses `DIRECT_VERIFIED`, `CURATED_UPSTREAM_ONLY`, `DERIVED_WITH_LINEAGE`, `UNRESOLVED`, `NOT_REPORTED`. Report completeness by metric and geographic grain; never confuse source presence with observation coverage.
5. Fully integrate the scanned SitReps 007–009 after page-level transcription/review and re-audit the source count.
6. Pin the accepted dataset release to source PDF SHA-256s, INRB commit IDs, code revision and a reproducible validation report.

**Phase B — future SitRep incremental ingestion (second).**
- Discover new or revised official PDFs; check report date and source PDF SHA.
- Archive unchanged original bytes before extracting.
- Version separately if a report with the same number changes.
- Apply the historical schema/extraction rules; compare against preceding accepted data and current INRB revisions, flag changes, do not auto-correct.
- Fail closed on missingness, invalid dates, different case/death definitions, geography aliases, unexpected table formats or retrospective adjustments.
- Produce explicit review queue and preserve the previous accepted historical snapshot if a new run fails. Do not use GitHub Actions success as a scientific certification.

**Phase C — narrative completeness audit (third).**
- Source benchmark is **the entire text of every report page**, including scanned/graphic text when verified, *not* the narrative-candidate index or keyword hit count.
- Establish section inventory per report from original headings and document layout (coordination; surveillance; border points; laboratories; case management; IPC and burials; vaccination; community engagement; logistics; security; psychosocial protection; and any other named original pillar). Do not assume one universal fixed section layout.
- For each section, capture full text in reading order, report/hash, section heading, page range, text-block location and source boundaries. Adjacent page continuations must join correctly; captions and footnotes must not be silently dropped.
- Compare to complete original PDF page text and INRB operational-narrative vectors *as secondary extraction evidence*; distinguish missing section, genuinely not reported, extraction omission, duplicate section, repeated boilerplate and truncated excerpt.
- Existing lexical narrative candidates are research discovery leads only, not a coverage certificate. The 2,151 previously truncated candidate excerpts are a specific audit priority; their original full-page text is preserved in the source archive and should be reconstructed for any substantive use.
- Publish a report × section × text-block/source-page completeness matrix and documented exception register before considering narrative trends, events or coding.

## State of implementation at this decision

- Historical long-form provisional candidate layer: implemented, successful and permanently released.
- National and zone concordance, provincial audits, scanned-source custody, review files: working, but individual historic PDF table-cell verification incomplete.
- Fully adjudicated `historical_best_supported` dataset: **not yet complete**.
- Automated incremental future intake on accepted historical schema: **to be adapted after Phase A**.
- Independently verified narrative section completeness: **not yet performed**.

**Research constraint:** no automated upstream value, keyword candidate or late cumulative count gets promoted as a certified daily observation or independently verified incident without adequate source evidence.
