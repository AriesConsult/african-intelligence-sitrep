# NATIONAL SITREP PRIMARY-SOURCE READING AUDIT — 8 NOVEMBER 2026

**Purpose:** resolve *what was printed* in original INSP SitReps, without assuming INRB's pinned CSV is independently wrong epidemiologically. This audit supplements, but does not replace, `docs/SITREP169_SOURCE_ADJUDICATION.md`.

**Evidence:** direct visual inspection of original INSP PDF pages 1 and, where noted, page 2. Official hosted URLs match the source URLs in the archived source registry. The original PDF bytes were **not** rehashed from the independent browser capture to establish identity with the separately SHA-verified archived PDFs. Machine-readable observations and the original registry hashes are in `state/verified_original_cover_readings_20261108.json`.

## Source-reading findings

| SitRep | Reporting period | Original confirmed cases | Original confirmed deaths | Important interpretation |
|---|---|---:|---:|---|
| 004 | 19 May | **33** (national total) | **4** | Automated national candidate **30** was *Ituri's provincial subtotal*, not the national total. Official page 1 banner and national table total both show 33. INRB's 51 for that date still requires revision/date-source examination. |
| 086 | 8 Aug | **4,294** | **1,960** | Both cover banner and provincial table agree. INRB's 4,209 / 1,916 reflect a different date or source revision; INRB's report note labels SitRep 086 as 9 Aug (not the original printed reporting date of 8 Aug). |
| 103 | 25 Aug | **5,713** | **2,744** | Both figures confirmed by cover and narrative. INRB's 2,755 deaths for this date remains a source-vintage/revision discrepancy (11 deaths). |
| 150 | 11 Oct by SitRep designation and Table 1 | **9,065 in banner and Table 1**; **9,066 in prose** | **4,381** | Genuine **intra-SitRep conflict**. The printed province totals sum to 9,065; INRB uses 9,066. For an *as-reported tabular* series, 9,065 has stronger within-document support; the 9,066 prose alternative must be preserved, not silently discarded. Cover also labels the date of report as 12 October while the SitRep number, Table 1 and narrative refer to 11 October. |
| 169 | 30 Oct | **10,414** | **5,372** | The source explicitly reports a retrospective **+314** harmonisation of Ituri deaths. INRB lists 5,058 deaths for the same row date. Preserve older and revised source versions separately. |

## Primary original PDF URLs

- 004: https://insp.cd/wp-content/uploads/2026/05/Sitrep_MVE-Ituri_N%C2%B0004-au-20-mai-2026.pdf
- 086: https://insp.cd/wp-content/uploads/2026/08/SITREP_MVEBDB_086_080826.pdf
- 103: https://insp.cd/wp-content/uploads/2026/08/SitRep_MVEBDB_103_25_08_2026.pdf
- 150: https://insp.cd/wp-content/uploads/2026/10/SitRep_MVEBDB_150_11_10_2026.pdf
- 169: https://insp.cd/wp-content/uploads/2026/10/final_draft_SitRep_MVE_RDC_N_169_30-10-2026.pdf

## Decisions

1. Confirm and retain the original printed *as-reported* national values above, with the exact original report identity and original page pointer.
2. **Do not** overwrite the pinned INRB values: they are curator-vintage evidence and sometimes represent a different reporting date, corrected revision or an editorial choice.
3. For SitRep 150, record **two incompatible in-document case totals**; prefer 9,065 only for the explicitly tabular as-reported view, because it agrees with the banner, Table 1 and sum of provincial rows. Do not assert that this proves a correct epidemiological incidence.
4. For SitRep 004, correct the extraction interpretation from province subtotal to national total, rather than invent an epidemic revision.
5. For 086 and 103, resolve the primary PDF reading; keep the **reason INRB differs** open until the INRB historical version and reporting-date lineage are explained.
6. For 169, accept that the source explicitly records a +314 retrospective harmonisation and retain the revision as a dated evidence event.
7. Keep production feed unchanged pending whole-corpus acceptance and scientific source validation.

**Status:** original cover/tabular reading determined for these examples; the full historical series, 114 cumulative decreases, and all historical health-zone cells remain under the separate comprehensive validation gates.
