# BDBV SITREP INGESTION — QUALITY GATES (v1, 7 November 2026)

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
   the public repository. Original full extracted page text in workflow artifacts
   is temporary; establish access-controlled durable storage before relying on it
   for monthly bulletins.
5. Daily/weekly/monthly analytical bulletins require an evidence-linked editorial
   review step. The existing literature section remains separate and unchanged.

**Current status (baseline before these upgrades are rerun):** 158 catalogued
report numbers, 15 accepted operational observations, only one report with all
five tables machine-validated. This baseline is not an acceptance certificate.
