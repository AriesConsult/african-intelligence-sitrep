# BDBV 2026 — Analytical methods, data lineage, and prompt inventory

**Current production architecture reviewed 11 November 2026.** This is a maintainable entry point for research and editorial improvement. Exact active One.com prompts must be exported from the production prompt manager and added through controlled revision; no prompt text has been reconstructed or invented.

## Authoritative boundary

**GitHub is the evidence and source-publication tier.** `run_pipeline.py` discovers originals, `archive_originals.py` preserves identical SHA-256 bytes, `reprocess_tables.py` extracts tables and their dated source references, `verify_publication.py` enforces numerical reconciliation, `generate_bdbv_bulletins.py` builds deterministic bilingual source-only bulletins and dashboard JSON, and `build_bdbv_assessments.py` builds ISO-week and calendar-month evidence packs. The source-bulletin workflow records a SHA-256 manifest and releases `BDBV_BULLETINS_SITE_UPLOAD.zip`.

**One.com is the source-import, editorial and public-dashboard tier.** The authenticated `bdbv_source_sync` webcron route imports only permitted source files over HTTPS; no GitHub job requires One.com SFTP credentials. Site-native prompts and AI analysis operate separately. Editorial approval and evidence-fingerprint checks are not implied by successful import.

See [operations](OPERATIONS_HANDOVER.md), [bulletin architecture](BULLETINS.md), [source quality gates](QUALITY_GATES.md), [historical release](DATA_RELEASES.md).

## Primary data and source identities

- Primary originals: Institut National de Santé Publique (INSP) Ebola SitReps, discovered through official publications and the INRB-UMIE GitHub mirror, `INRB-UMIE/BDBV2026-Data`. Each source identity contains report number, reporting date, source URL and full PDF SHA-256. Publication dates can differ from reporting dates.
- Curated national, provincial and health-zone metrics: pinned INRB GitHub `data/insp_sitrep/processed/insp_sitrep__<metric>__daily.csv` files. Historical qualified records are pinned to Git commit `c00b8843e6ebae8f0cd846bc43cb564a3893bfd9`. Post-historical candidates are separately pinned and remain `new_inrb_unverified` pending source verification.
- Numerically accepted operational information: `published/tables/NNN_<sha12>.json`, `published/table_index.json`, `published/feed.json`, `published/ingestion_audit.json`, `published/publication_qa.json`. The GitHub source-only bundle's `contact_tracing_public.json` uses only `MACHINE_VALIDATED` original SitRep Table 4 snapshots.
- Historical evidence tiers: A = documented original-PDF reading and curated concordance; B = machine PDF/INRB concordance pending visual QA; C = pinned INRB-curated-only provisional use; restricted = source ambiguities, source revisions, missingness and other exclusion rules. Tier A/B/C are **qualified descriptive evidence**, not independent epidemiological validation. Scanned SitReps 007–009 are source-archived but unverified OCR numerical values are excluded.
- Narrative material: `published/narrative_candidates/` and narrative index. Topic matches and `REVIEW_REQUIRED` excerpts are **leads**, not independently confirmed events. Avoid publishing names or contact information unnecessarily.

## Calculation register and limitations

| Indicator | Calculation | Conditions / interpretation |
| --- | --- | --- |
| Crude cumulative case-fatality ratio (CFR) | `100 * cumulative_confirmed_deaths / cumulative_confirmed_cases` | Same source date/geography and consistent definitions; crude cumulative surveillance ratio, sensitive to delays and ascertainment; not an infection-fatality ratio |
| Contact follow-up coverage | `100 * contacts_seen / contacts_to_follow` | Same reported Table 4 date and geography; positive denominator; `seen <= to_follow`; printed percent recomputed within accepted tolerance; zero denominator gives undefined, never 0% |
| Reported cumulative case change | `C(t2) - C(t1)` | Comparable snapshots with dates and source qualifications; `net reported change`, **not** onset-date incidence |
| Reported cumulative death change | `D(t2) - D(t1)` | Same constraints; revisions, incomplete reporting and missing intervals cannot be converted into mortality events |
| Crude CFR change | `CFR(t2) - CFR(t1)` percentage points | Comparability of the two cumulative numerators/denominators required |
| Provincial / zone descriptive sum | Sum of available, explicitly reported zone values | **Not** an official provincial total unless full coverage and reconciliation are demonstrated; missing zones and unallocated values must remain visible |
| Weekly reporting-interval bars | Differences between qualified, dated cumulative observations grouped by ISO Monday–Sunday week | Suppress downward or incompatible differences; show gaps explicitly; neither true epidemiological week incidence nor onset-date counts |
| Apparent Rₜ (public dashboard) | Site-native exploratory procedure on revision-sensitive reported cumulative observations | **Not a validated Rₜ series**; do not state model assumptions, formula, posterior calibration or transmission implications without auditing the live `rt` JavaScript and inputs |
| Daily, weekly, monthly source completeness | Count observed eligible reporting dates vs expected period dates; list gaps | A missing date is missing, not zero. ISO weeks may cross months; monthly pack records partial weeks |

Table 4 schema changed over the outbreak: some earlier reports label PoE/PoC as Table 4, while recent reports use Table 4 for contact tracing and Table 5 for PoE/PoC. Identify the meaning by printed title/content rather than table number alone. SitRep 178 (8 Nov) required a strict adjacent split-row extraction rule; its 30,444/38,453 = 79.2% and SitRep 179's 27,012/33,900 = 79.7% have since passed machine validation. Such checks do **not** certify unrelated historical tables or the causal meaning of a change.

## Evidence packs and publication

`bdvd2026/assets/data/analysis_inputs/daily_evidence.json` contains qualified/provisional source observations, source references and limited review-only narrative metadata. `weekly_evidence_packs.json` aggregates completed ISO weeks with explicit missing days; `monthly_evidence_packs.json` groups calendar month evidence and ISO-week subsets, noting partial weeks. These data structures are distinct from editorially accepted prose. The deterministic source archive, approved AI assessments, and user-visible dashboard are separate publication states.

## Prompt inventory — do not confuse different execution paths

| Prompt / code location | Role | Verified current text? |
| --- | --- | --- |
| `build_bdbv_assessments.py` constant `SYSTEM` | Optional **GitHub-side**, English-only structured review draft; requires `--draft-ai`; **not active One.com publication** | **Yes, exact constant available in source** |
| `admin_ai_prompts.php` → `bdbv_daily_v1` | One.com daily editorial analytical draft | **No; export active text and revision metadata** |
| `admin_ai_prompts.php` → weekly prompt | One.com weekly analytical draft | **No; exact active identifier and text to be verified** |
| `admin_ai_prompts.php` → `bdbv_monthly_v1` | One.com monthly analytical draft | **No; export active text and revision metadata** |

The reported One.com default model was `gemini-2.5-flash-lite` at the last site configuration check; verify live provider/model per prompt before publishing any future specification. The optional GitHub `SYSTEM` prompt, reproduced **by reference to its exact source constant rather than as an invented One.com equivalent**, requires evidence-only analysis, reporting-date citations, cautious cumulative differencing, explicit qualification and provisionality, no unsupported causal or forecasting claims, and `REVIEW_REQUIRED` status for drafts. Its structured response fields are `headline`, `assessment`, `signals` (each finding, evidence_dates, confidence), `data_limitations` and `editorial_checks`.

### Prompt export and future protocol

Export each One.com prompt **verbatim**, with language, prompt ID, active status, provider/model, generation options, last edit and effective version; redact credentials. Pin a source/evidence-pack fingerprint and prompt version for each AI draft. Retain old versions and use EN/FR historical regression cases to check changes before activation. Factual gates must separately check numerical statements, units, attribution, ambiguity, citations/DOIs, duplicate events and any forecast/Rₜ claim. Human editorial approval is required before automatic publication is considered.

## Priority research improvements

1. Validate data-date versus event-date distributions, reporting delays and revision chronology before claiming incidence/acceleration; qualify zone-level time series.
2. Reconcile additional original SitRep tables and reviewed narrative events without weakening the `MACHINE_VALIDATED` gate.
3. Audit apparent Rₜ and any Bayesian/prospective forecasts in a dedicated model version with diagnostic and prediction-interval checks. Do not promote an exploratory visualization into a validated transmission estimate.
4. Export the **exact** live One.com prompts, compare them against this specification, and test daily/weekly/monthly EN/FR prompts on fixed evidence packs.
5. Verify bibliographic DOIs, venue/server labels, publication dates and claim-to-reference relevance before adding a scientific literature section to an approved bulletin.

**Change control:** update this file when the validated formulas, source classes, source release format, prompt inventory, or website editorial contract changes. Preserve the historical documentation as an audit trail.
