# BDBV SITREP INGESTION — QUALITY GATES (v2, 8 November 2026)

> **CURRENT OPERATIONS NOTICE — 11 NOVEMBER 2026.** The live African Intelligence BDBV source pipeline is **GitHub Actions → versioned source-only GitHub Release → authenticated One.com HTTPS pull** via cron-job.org. GitHub does **not** push files over SFTP/FTPS, perform site-native AI generation, or approve AI narratives. This notice supersedes any older instructions below referring to pending importer implementation, manual ZIP installation, FTPS, SFTP, or disabled site synchronization. Historical sections are retained to document architecture decisions, **not** as active deployment instructions. See [current runbook](OPERATIONS_HANDOVER.md) and [bulletin operations](BULLETINS.md).

## G. PRODUCTION EVIDENCE-TO-PUBLICATION BOUNDARY (11 NOVEMBER 2026)

Source-only automated publication and editorial AI publication are different certification tracks. The importer accepts only GitHub-manifested source artifacts, not model output. Current original-PDF Table 4 extractor uses independently verified label/number reconciliation including adjacent split-row layouts (SitRep 178), while the final source table must still reconcile numerators, denominators, rates and provincial sums. Source QA passing is not independent epidemiological validation. One.com assessment prompts, bibliographic DOIs, inferred rates and literature citations require dedicated editorial/scientific review. The full original One.com prompts are not stored in GitHub.

---


The ingestion status **must not be described as fully verified** solely because
a GitHub Actions job finished successfully.

## A. Source identity and auditability
1. For each source, establish a real PDF download, 2026/17th-outbreak cover identity,
   report number, reporting date, publication date if available, source URL and SHA-256.
2. Retain the immutable SHA keyed review extraction. A changed source hash is a
   different revision and must not silently replace published observations.
3. Match registry identities to review-queue identities and indexed snapshots.
   Missing, unreadable or differently hashed records are blocking integrity issues.
4. Preserve source PDFs durably (outside 30-day GitHub workflow artifacts) before
   claiming a permanent reproducibility archive.

## B. Numerical validation
1. Discover and classify the actual table schema *per SitRep*, not only by its
   table number: the meaning and layout of Tables 1–5 change over time.
2. For every candidate metric, retain the raw reported value, date, page, table,
   numerator/denominator if applicable, geographical scope, source hash, and
   reporting window. Values marked ND/NA are **not zero**.
3. Verify row-level arithmetic, internal rate consistency, provincial/national
   reconciliation, and independent comparison against the source PDF for a
   stratified sample across early, middle and late periods.
4. Never silently sum health zones into province totals when there are unallocated
   deaths, missing zones, shifting denominators or partial provincial reporting.
5. Keep INRB national cases/deaths and established forecasts distinct from
   SitRep-derived operational metrics until reconciliation is documented.

## C. Completeness and operational readiness
1. The audit must report total source documents, unique report numbers,
   report-number gaps, extracted-table availability and per-table validation
   coverage. A numbering gap does **not** prove a SitRep was published.
2. Generate and inspect `published/ingestion_audit.json` after every run.
3. Fix extraction layouts and repeat the historical backfill until unresolved
   review items are explicitly enumerated, not hidden by a green workflow badge.
4. The One.com dashboard must clearly label freshness, source, data completeness
   and whether an indicator is machine-validated or human-reviewed.

## D. Narrative intelligence
1. A PDF narrative is extracted from the *same hash-verified PDF* as the tables,
   with source page and block provenance.
2. Topic, event-type and province-mention classifications are **review-only leads**;
   a keyword match does not establish an incident, trend or causal mechanism.
3. Repeated claims across SitReps are not independent events. An editorial event
   register must distinguish new, continuing, worsening, improving and resolved.
4. Do not automatically publish full narrative text, names or contact details on
   the public repository. Full extracted page text is now versioned in GitHub Releases, which are not access-controlled on a public repository. Screen named contacts and sensitive information before any public narrative reuse.
5. Daily/weekly/monthly analytical bulletins require an evidence-linked editorial
   review step. The existing literature section remains separate and unchanged.


## E. Qualified historical evidence acceptance (8 November 2026)

The user-approved **qualified historical descriptive release** is published separately from the core operational feed. It preserves **15,726** pinned INRB-curated source records across **31** metrics, each with an evidence tier and explicit restrictions. **14,442** rows are permitted for qualified descriptive use; **1,284** remain restricted. Descriptive permission is **not** full scientific certification.

1. Tier **A (3)**: original PDF reading visually documented, INRB concordant and no other blocking exclusion. PDF fidelity is not independent epidemiological validation.
2. Tier **B (4,222)**: machine PDF/INRB concordance; provisional descriptive use only.
3. Tier **C (10,217)**: pinned INRB curated, original PDF-cell fidelity unverified; provisional descriptive use only.
4. **Restricted (1,284)**: excluded from qualified descriptive use but preserved in the research audit. Restriction reasons (which overlap): 114 cumulative decreases, 242 ambiguous or discordant PDF readings, 562 scanned-date source uncertainties, 450 nonnumeric/missing or unsuitable source rows, and 13 differences versus visually reviewed original PDF readings.
5. SitReps **007–009** are separately archived, 37 pages, with OCR-only numerical content excluded until visual source verification.
6. All historical values are excluded from blind *daily-incidence derivation by differencing* without a validated reporting-period/revision model.
7. Historical qualification **does not modify the published operational feed**, website dashboard or forecasting models.
8. Revised historical versions require a new source-frozen release and documented reasons, never silent replacement.

See the [qualified release, exclusions and source archive catalogue](DATA_RELEASES.md).

## F. Continuing ingestion and research boundaries

The latest inspected scheduled pipeline run (**8 November 2026**) passed discovery, extraction, narrative classification and the independent publication gate. The associated audit counted 158 original machine-extracted PDF identities, 27 machine-validated operational observations across five indicators and durable source archiving for those 158 original PDFs. The separate 007–009 scans bring source identities to 161, **not** 161 fully source-cell-certified SitReps.

The configured jobs run daily at **08:27 EAT** (intake), **09:10 EAT** (original archive) and **09:55 EAT** (source-change guard), subject to GitHub scheduling delay and independent errors. Check the *latest actual Actions result* rather than assuming schedule guarantees completion. See [operations](OPERATIONS_HANDOVER.md).

Narrative section boundaries, complete reading order and scanned/OCR content remain under a **separate** verification track.

**Bottom line:** the scraper works, the qualified historical descriptive dataset is released, and future source/version checks are operational. This is not a blanket certificate of the complete original historical tables or all narrative content.
