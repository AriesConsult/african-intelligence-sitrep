# BDBV SitRep-derived automated bulletins

**Operational as of 9 November 2026.** The initial generator workflow [run 42530772370](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42530772370) completed successfully, generating **129 daily**, **26 ISO-weekly** and **7 calendar-monthly** bulletins, each in English and French (**324 HTML pages for 162 reporting periods**).

## Source and research controls

The scripts read the [qualified historical evidence release](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-qualified-historical-42498372593), pinned to INRB Git commit `c00b8843e6ebae8f0cd846bc43cb564a3893bfd9`, and append newly observed INRB GitHub source rows from a separately pinned current revision. The generated texts are deterministic translations and numeric digests; no AI narrative generation, fabricated explanations or invented incident dates are involved.

- Tier A/B/C eligible historical records can be used for **qualified, clearly described source snapshots** only.
- All 1,284 restricted historical observations, including the three scanned-only source dates (007–009), remain excluded from numeric bulletin values.
- Net positive weekly changes are differences in cumulative reports **not onset-date incidence**. Negative changes or unqualified intervals are not plotted as positive events or converted into negative cases.
- Contact-tracing sums represent **only those health zones reporting numeric values on the same date**. Counts, missing values and geographic coverage remain separate; do not infer a national contact follow-up rate without validated numerator and denominator.
- The published catalogue records `publication_mode=automated_unreviewed_no_ai`; these are algorithmically checked **source bulletins**, not expert-reviewed outbreak narratives.
- Reporting dates are data dates, not automatically the dates of first notification or publication. Latest valid source figures may predate the current day.
- Both original source revisions and all historical excluded records remain available for later correction and new, explicitly versioned bulletins.

## Generated site files

The GitHub Release contains `BDBV_BULLETINS_SITE_UPLOAD.zip`. Extract it into the One.com site root, preserving:

- `public_html/bdvd2026/bulletins/daily/YYYY-MM-DD-en.html` and `-fr.html`
- `public_html/bdvd2026/bulletins/weekly/YYYY-MM-DD-en.html` and `-fr.html`
- `public_html/bdvd2026/bulletins/monthly/YYYY-MM-DD-en.html` and `-fr.html`
- `public_html/bdvd2026/assets/data/bulletins_public.json` — powers the existing dashboard Bulletin tab.
- `public_html/bdvd2026/assets/data/contact_tracing_public.json` — date-stamped same-day zone-sum contact indicators for the Contact tracing tab.
- `public_html/bdvd2026/assets/data/weekly_national_public.json` — labelled weekly net cumulative changes, not epidemiological incidence.

The canonical dashboard remains `/bdvd2026/dashboard.php`. Its CSS is integrated with `/assets/css/african-intelligence.css`.

## Regular generation

[Workflow: BDBV automated daily weekly monthly source bulletins](../.github/workflows/bdbv-bulletins.yml)

- Daily at **07:25 UTC / 10:25 Nairobi time**, after the source discovery (08:27 EAT), archive (09:10 EAT) and change-control (09:55 EAT) workflows. GitHub Actions can start late; there is no guarantee all four jobs use the same upstream update.
- A manual `workflow_dispatch` run can regenerate the full history at any time.
- Pin the precise latest INRB upstream revision, stage its 31 source CSVs, and compute bulletins with `generate_bdbv_bulletins.py`.
- Validate links, output manifest, existence of weekly/contact data assets, and tests before creating a source-and-generator-hash named GitHub Release.
- Identical source + generator hashes are not re-released automatically. The subsequent run will release updated output when new source or generator changes.
- An Actions artifact also retains the ZIP for 90 days; the Release is the durable archival source.

### Site auto-sync (deliberately not enabled by default)

The GitHub workflow has an optional FTPS upload step, **disabled until the site owner opts in and configures credentials**. Set the following as GitHub repository **Actions secrets**:

`BDBV_FTPS_HOST`, `BDBV_FTPS_USER`, `BDBV_FTPS_PASSWORD`.

Set these as **Actions variables**: `BDBV_FTPS_PUBLIC_HTML` (remote root, e.g. `public_html` as appropriate for One.com account), and `BDBV_BULLETIN_DEPLOY_ENABLED=true`.

Check the One.com hostname, remote root, FTPS TLS support and permissions before enabling. The workflow syncs only the bulletin subfolder and the bulletin/contact/weekly public asset directory and never deletes other site files. **Do not copy passwords or .key files into the GitHub repository.** If FTPS is not configured, manually upload the Release ZIP; the rest of the daily generation pipeline continues.

## Remaining analytical work

The existing exploratory dashboard `R_t` calculation is independent and uses the current live national series; the bulletin generator does not fabricate or back-calculate Bayesian transmission estimates. Statistical (R_t) and true weekly incidence will require a dedicated validated, versioned epidemiological model release. Contact-tracing totals remain geographically incomplete until source coverage is verified.

**Edition references:** [successful backfill run](https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42530772370) · [initial bulletin GitHub Release](https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-rulebased-bulletins-c00b8843e6eb-897fa8e99a64).

## Original SitRep Table 4 and textual situation digests (9 November update)

**Correction to the first bulletin release:** The initial contact feed relied on five obsolete INRB contact CSVs ending in May. The source repository already holds `published/tables/<sitrep>_<sha>.json` with the original SitRep **Table 4**, including national and provincial `contacts_seen`, `contacts_to_follow` and follow-up percentage. The generator now reads only `MACHINE_VALIDATED` Table 4 snapshots after verifying source PDF hash identity, recomputing the percentage and rejecting inconsistent denominators. Five dates currently pass this strict gate, including 30 October and 3–5 November. For 3 November (SitRep 173), 33,281 of 39,667 contacts were seen (83.9%). Missing/review-required Table 4 dates remain missing, not zero or carried forward. This is a nationally reported figure for its particular reporting day; it should not be equated with new contacts listed.

**Text narratives:** The initial numeric-only bulletins have been replaced with rule-based *source-text digests*: themed short French-language passages, each cited to its hash-pinned original SitRep number, page and public PDF URL. The source index currently covers 158 reports. These selections are **not yet expert-reviewed interpretive summaries**: each excerpt is tagged `REVIEW_REQUIRED`; source-text completion, longer paragraphs and subtle relations still require an editorial verification pass. English headings do not constitute English translation of the cited French excerpts, which remain in the source language to avoid unverified translation.

Deployment requires **both** the new GitHub-generated bilingual HTML archive with the updated `contact_tracing_public.json` asset and the [matching dashboard contact-tracing patch](/) for displaying Table 4 in `dashboard.php`. The previous website HTML pages need replacing in place; without this, old numeric-only bulletins remain visible. The GitHub workflow archives a new release when the generator, original Table 4 index or narrative index changes, even if the pinned INRB source SHA is unchanged.

## 9 November — Expanded five-table numerical annex and historical table-number transition

The bulletin generator now publishes all successfully parsed numeric fields in **all five original SitRep tables**, nationally, provincially and by health zone, with the source page, PDF link and comparison to the last validated reporting snapshot. The fields include PoE/PoC traveller counts, screening, handwashing, sensitisation, reporting completeness, cross-border alerts, contact-tracing coverage, cases, deaths and surveillance alerts. A ratio change is reported as percentage points; a count difference is a change in reported counts, **not an onset-date incidence**. No unvalidated tables are silently promoted: sections instead explain the non-publication.

**Critical historical schema change:** Earlier SitReps often printed PoE/PoC under **Table 4**, whereas the November layout has contacts in **Table 4** and PoE/PoC in **Table 5**. `sitrep_tables.py` now detects this by table contents; SitRep 160 (21 October) is a regression test. The bulletin workflow reprocesses the archived original extraction queue in a local working copy without modifying the live PHP dashboard data feed.

Verified successful workflow run: https://github.com/AriesConsult/african-intelligence-sitrep/actions/runs/42580268382. This run produced 162 EN/FR editions, read **130 original table snapshots** and still found only **five eligible machine-validated Table 4 contact-report dates**. Most historical contact monitoring still needs original-PDF layout-specific extraction and reconciliation; a wider source table catalogue does not certify complete longitudinal Table 4 coverage. For the newest source archive, SitReps 176/177 also require completed source custody before the separate main ingestion gate can pass.

Latest bilingual source bulletin bundle: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-rulebased-bulletins-c00b8843e6eb-1df597269eeb. The production website is not automatically updated until FTPS is explicitly configured or the ZIP is manually uploaded.


## 9 November — Annex HTML delta-rendering correction

The original five-table annex renderer appended trusted `<small>(+change)</small>` markup to a numeric string and then HTML-escaped the *entire* cell. Browsers therefore displayed the literal tag text, for example `10,803 <small>(+271)</small>`, instead of a styled change indicator. The generator now HTML-escapes the numeric value and the delta text separately, while retaining the trusted `<small>` element. The change applies to English and French daily, weekly and monthly pages, including percentage-point deltas, without changing any source value, acceptance tier, date, or table validation status.

A regression test checks markup, percentage-point labels and the existing `annex-scroll` container. **Previously uploaded static bulletin HTML pages do not change automatically.** The bulletin workflow must generate a new GitHub Release ZIP, and that ZIP must be deployed through the configured FTPS sync or manually uploaded to One.com. The workflow's release hash includes the generator, so this code correction changes the release identity even when upstream source observations are unchanged.


## 9 November — Prevent repeated narrative excerpts across topics

The rule-based source-text digest may classify one source passage under multiple topics. The generator now selects each normalized short excerpt **at most once per bulletin**, choosing the next distinct eligible candidate when possible and omitting a topic if it has no distinct passage. This avoids presenting one source paragraph as separate evidence under Surveillance, IPC, Logistics or Service continuity. All selected excerpts retain their original SitRep citation and `REVIEW_REQUIRED` status; this is **not** expert thematic verification. Existing static bulletin pages require regeneration and deployment of the new release ZIP. The original SitRep evidence and archived candidate classifications are unchanged.
