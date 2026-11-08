# SITREP 169 — DIRECT SOURCE ADJUDICATION OF INRB DISCREPANCIES

**Review date:** 8 November 2026  
**Primary source:** https://insp.cd/wp-content/uploads/2026/10/final_draft_SitRep_MVE_RDC_N_169_30-10-2026.pdf  
**Original PDF SHA-256:** `8e2cd47248423d71341536e26671abfeb08364094334d2cee548dcb457532fa5`  
**Report date:** 30 October 2026. **Publication:** 31 October 2026.  
**Review method:** visual inspection of original PDF cover (printed page 1) and historical Table II continuation (printed page 3), with comparison against pinned INRB daily CSVs at commit `c00b8843e6ebae8f0cd846bc43cb564a3893bfd9`. No PDF- or INRB-derived value is automatically inserted into the public analytical feed by this note.

## National cumulative deaths: a documented retrospective adjustment

The INSP SitRep 169 cover explicitly records **10,414 cumulative confirmed cases** and **5,372 cumulative confirmed deaths** (CFR 51.6%). The same page describes an Ituri data harmonisation on **29 October**: the provincial death total was revised from **3,436 to 3,750**, a change of **+314**. The printed SitRep's national total is therefore **5,372**.

The pinned INRB `insp_sitrep__national_cumulative_confirmed_deaths__daily.csv` gives **5,058** for 2026-10-30. The PDF–CSV difference is **+314**, precisely the adjustment described on the PDF cover. **Interpretation:** strong evidence of a differing revision state, not a plausible small transcription error; the reason INRB still reports the earlier value requires confirmation against its digitisation notes and later revisions. We must retain both records and their respective provenance.

**Important:** A dated source value and a subsequently harmonised value are two distinct evidence events, not an invitation to silently change historical cells.

## Six previously persistent health-zone disagreements — PDF visually verified

Original printed page 3, Table II continuation:

| Zone | Metric | Printed primary PDF | INRB daily CSV (same date) | Adjudication |
|---|---|---:|---:|---|
| Nyankunde | Cumulative confirmed cases | 154 | 139 | PDF printed value verified |
| Nyankunde | Cumulative confirmed deaths | 57 | 43 | PDF printed value verified |
| Rimba | Cumulative confirmed deaths | 12 | 6 | PDF printed value verified |
| Rwampara | Cumulative confirmed cases | 1,267 | 1,202 | PDF printed value verified |
| Tchomia | Cumulative confirmed cases | 87 | 86 | PDF printed value verified |
| Tchomia | Cumulative confirmed deaths | 36 | 27 | PDF printed value verified |

These are original primary-source *reported values*, visually checked in the PDF. The INRB alternatives remain valid as records of its own curated series, but **must not replace** the specific SitRep 169 printed values. The reason for every zone-level difference is not individually established; retrospective harmonisation may explain some or all, but this must not be assumed without the specific source notes.

**Additional zone difference in SitRep 169:** Mutwanga confirmed deaths, printed PDF = **14**, INRB = **11**. The earlier automated triage classified this as an adjacent-date candidate rather than one of the six persistent differences. Its original PDF value is likewise visible on printed page 3, but the time-reference discrepancy still needs adjudication.

## Decision

- Status: `PRIMARY_PDF_PRINTED_VALUES_VISUALLY_CONFIRMED`.
- Do **not** automatically mark all INRB comparisons exact concordance.
- Do **not** modify `published/feed.json` or source archive bytes.
- Preserve INRB rows, upstream commit hash and PDF page, table, row identifiers in the reconciliation ledger.
- National and provincial reconciliation must allow explicit revision events; cumulative metrics are not automatically monotone across corrected reporting editions.
- All remaining historical reports require the same source-to-cell fidelity review before machine approval.

See `docs/INRB_RECONCILIATION_RESULTS_20261108.md` and the permanent source evidence releases.
