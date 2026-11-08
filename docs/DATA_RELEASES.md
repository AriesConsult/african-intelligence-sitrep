# BDBV 2026 — evidence releases and accepted uses

**Current checkpoint:** 8 November 2026. Historical evidence is **qualified for bounded descriptive research**, not fully certified as a corrected epidemic incidence series. The scraping/archiving process remains separate from historical certification and narrative review.

## Primary release: qualified historical dataset

**[Download the qualified historical release](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-qualified-historical-42498372593)**  
**[Successful acceptance Action](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42498372593)**

| Asset | What it contains |
| --- | --- |
| `historical_qualified_release.csv` | **15,726** source records with metric, date, original geography label, curated value, verified original PDF value where available, source fields, acceptance tier, permitted use and exclusion reason |
| `historical_exclusions.csv` | **1,284** restricted evidence records; preserved, not dropped |
| `metric_tier_coverage.csv` | Coverage by metric and acceptance tier |
| `HISTORICAL_ACCEPTANCE_REPORT.md` | Human-readable acceptance decision |
| `historical_acceptance_report.json` | Machine-readable acceptance totals, frozen commit and SHA-256 hashes of input evidence |

The source dataset is frozen at the pinned INRB commit `c00b8843e6ebae8f0cd846bc43cb564a3893bfd9`.

### Decision table

| Tier | Records | Permitted use |
| --- | ---: | --- |
| A — visually checked PDF-as-reported / INRB concordant and not otherwise restricted | **3** | Qualified as-reported descriptive research |
| B — machine PDF/INRB concordance, pending original-cell fidelity review | **4,222** | Clearly identified **provisional** descriptive research |
| C — curated INRB version, with no original-cell proof | **10,217** | Clearly identified **provisional** descriptive research |
| Restricted | **1,284** | Source audit and discrepancy review only; **not** in the qualified descriptive pool |
| **Total** | **15,726** | All source rows preserved |

These tiers represent **evidentiary status**, not calibrated probabilities. Tier B agreements are not independent epidemiological confirmation. All rows remain excluded from unreviewed daily-incidence calculation by differencing cumulative values.

Reasons for restriction are **not mutually exclusive**: missing/nonnumeric (450), scanned-date source uncertainty (562), ambiguous or discordant source comparison (242), cumulative declines (114), and competing visually verified PDF values (13). This report preserves both sides of discrepancies.

The **17** separately documented original-PDF verbatim readings are available in the [verified source-reading release](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-source-verified-readings-42495579497): 4 agree with the corresponding curated value and 13 do not. Only 3 concordant readings meet all the additional tier-A publication gates. Verifying what a PDF printed is not proof the underlying epidemic figure is correct.

## Historical source custody and revisions

| Archive | Scope |
| --- | --- |
| [Full digital source, embedded-image and pinned INRB evidence](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-source-extract-evidence-42474203980) | **158** original PDF identities; **1,721** digitally processed pages |
| [Scanned original SitReps 007–009](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-scanned-sources-007-009-c00b8843) | **37** scanned pages, archived original bytes and hashes, separate review-only status |
| [Scanned OCR source candidates](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-scanned-ocr-42482358347) | OCR text/word boxes; transcription not verified |
| [Dual OCR discrepancy audit](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-scanned-dual-ocr-42486450511) | 31 of 37 pages had discordant numerical-token sequences |
| [Two-view historical evidence](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-two-historical-evidence-views-42495749569) | As-reported PDF readings distinct from the pinned curated INRB version |
| [Historical exceptions](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-historical-exception-triage-42495214801) | 114 cumulative decreases and 174 ambiguous zone row matches, not silently corrected |
| [Source revision language leads](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-source-revision-leads-42496212722) | Original-page indicators of possible historical corrections; leads only |

The main registry intentionally still distinguishes 158 fully digitally extracted reports from three separately archived, OCR-only scanned reports. The phrase **161 source identities** does not imply 161 fully machine-validated reports.

## Ongoing intake and operation

The operational job [`bdbv-sitrep-pipeline.yml`](../.github/workflows/bdbv-sitrep-pipeline.yml) is separately scheduled at **08:27 EAT daily**, with a Sunday full discovery/backfill. Original-PDF archive and source-change audit workflows operate at **09:10** and **09:55 EAT**, respectively.

- [Verified successful scraper / extraction job, 8 Nov 2026](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42478204067)
- [Source archive job](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42484149332)
- [Source-change control job](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42482128386)

The existing **`published/feed.json`** is a **separate** bounded operational product: 27 validated machine observations across five indicators according to the 8 November audit. It has **not** been replaced by or bulk populated from this historical descriptive release. A green Action does not imply coverage of every historical health zone.

GitHub schedule delivery can be delayed. For operational monitoring always consult the newest run status and `published/ingestion_audit.json`, `published/publication_qa.json` and `published/source_archive_index.json`.

## Narrative evidence is a separate, not-yet-certified track

| Evidence release | Function |
| --- | --- |
| [Full narrative page audit](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-narrative-coverage-42481834054) | Complete digitally extractable PDF page text and coverage register |
| [Lossless candidate narrative segments](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-narrative-sections-42482331705) | 4,744 mechanical section segments from 158 reports; headings unverified |
| [INRB operational narrative sources](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-inrb-narrative-source-42482757259) | 54 French/English response data files, 3,116 rows, pinned upstream version |
| [INRB-to-PDF narrative page leads](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-narrative-comparison-42482905395) | Literal French passage locators and unmatched/paraphrased cases |
| [Scanned report narrative candidates](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-scanned-narrative-sections-42482633789) | Separately labelled OCR-only segments from SitReps 007–009 |

**Caution:** A keyword match or mechanically segmented excerpt is not a verified narrative section; a no-match with INRB does not show the original report lacked the information. Automated page text may omit image-backed words and preserve imperfect reading order.

## Re-running acceptance and improving later

The [qualified acceptance Action](../.github/workflows/bdbv-qualified-historical-acceptance.yml) is driven by **specific frozen input releases**, and fails closed if observed source version, indicator set, count or verified-cell cardinality differs. It produces a **new tagged release**, rather than rewriting the existing one. For an improved dataset, update the explicit input references, review and test the change, issue a new release tag, and record supersession in the acceptance report.

Do **not** infer new daily cases from unreconciled changes to cumulative totals, merge nonunique health-zone identities, interpret `ND` as 0, substitute OCR numbers for printed PDF cells, or claim that INRB and our transcriptions are independent epidemiological samples.

For the authoritative distinction between *verified original PDF transcription* and *validated epidemiological measurement*, see [scientific evidence certification gate](SCIENTIFIC_CERTIFICATION_EVIDENCE_GATE_20261108.md).

**Maintenance priority:** keep the scraper, original-source archives and future source-revision checks running. Revisit historical and narrative questions as controlled, evidence-linked updates without destabilising ingestion.
