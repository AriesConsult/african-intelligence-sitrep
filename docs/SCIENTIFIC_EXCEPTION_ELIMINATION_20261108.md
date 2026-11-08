# BDBV 2026 — SCIENTIFIC EXCEPTION ELIMINATION PASS

**Date:** 8 November 2026. **Objective:** move from a technically recoverable corpus to an auditable, scientific source-linked historical series. **Decision:** preserve raw sources, original and amended INSP values and the frozen INRB vintage independently; never force-close a discrepancy because it is numerically convenient.

## Verified concrete progress

### National original-source reading

Direct PDF page inspection now documents the original printed national figures in SitReps **004, 086, 103, 150 and 169**, with hashes and source URLs in `state/verified_original_cover_readings_20261108.json` and methods in `docs/NATIONAL_SITREP_SOURCE_ADJUDICATION_20261108.md`.

Particularly instructive:

- SitRep 004: the machine national reader selected **30**, which is Ituri's province subtotal; the actual **national figure is 33**. Its official first-page table and graphic agree.
- SitRep 086: the original printed figures are **4,294 cases and 1,960 deaths**. INRB's different figures must remain a separate date/vintage issue. Its digitisation note says 9 August despite the PDF giving 8 August as reporting date.
- SitRep 103: original printed **5,713 cases and 2,744 deaths**. INRB's **2,755 deaths** for the nominal matching date is not proof that the PDF transcription was wrong.
- SitRep 150: original **9,065 cases** on its banner AND provincial totals Table 1 (confirmed by printed province sum), versus **9,066** in its own narrative, and **9,066** in INRB. It also has conflicting report-date metadata. Explicit **primary-document inconsistency**; for an *as-reported tabular view* keep 9,065 with the conflicting 9,066 prose retained.
- SitRep 169: original cumulative deaths **5,372**, including the source's documented retrospective **+314** Ituri harmonisation, versus INRB's **5,058**. Seven previously disputed health-zone PDF cells were visually checked. Preserve historical version and dated correction.

**The original-PDF figure being visually checked does not itself certify that the underlying case surveillance was accurate.**

### 114 cumulative declines — all mechanically classified, none silently adjusted

- **55** rebound to or above the prior cumulative level within the next three observed source records;
- **50** remain below the prior level across at least three further observations;
- **5** show no rebound in the limited available follow-up;
- **4** have no following source observation.
- Separately, 84 decreases occur between consecutive reporting dates, 30 across gaps.

These are **behavioural classes, not epidemiological revision causes**. Original source timeline and candidate PDF identities are preserved. No negative case incidence is inferred.

Reproducible evidence: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-cumulative-diagnostics-42485577428

### Ambiguous health-zone cells — all 174 structurally analysed

- **113** are numerically identical but occur in **distinct PDF rows**. That does *not* make them the same source observation; preserve both source-row identities.
- **59** have differing PDF candidate values for the same normalised zone name;
- **2** involve same-zone naming collisions across provinces.

This distinguishes harmless-looking numeric repeats from real contradictory source-cell alternatives, without inferring data equality from spelling alone.

Reproducible evidence: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-zone-ambiguity-42485037633

### PDF dispute register

The review-only decision ledger contains **367 total source review/temporal exception entries**, including 114 cumulative declines, 174 ambiguous zone matches, original PDF–INRB health-zone differences and national-banner exceptions. It records the visually checked source figures separately from machine candidates and upstream curated numbers. SitRep 169 has seven zone-cell reading decisions and one documented national correction; additional national cover readings were checked directly.

Current audited register: https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-historical-adjudication-42486288754

### Targeted visual page pack

Only **32 distinct PDF pages** in **26 archived original SitReps** are required to address the presently identified primary-source national/zone row issues in the decision and ambiguity registers (the packet does not cover all possible historical extraction gaps). Images are rendered from exact SHA-matched original archived PDFs and each carries its outstanding question. They remain unreviewed until original-page examination.

https://github.com/AriesConsult/african-intelligence-sitrep/releases/tag/bdbv-original-exception-pages-42485388947

### Scanned SitReps 007–009

All **37** pages are original-PDF hash preserved, visually documented as source identities, and transcribed provisionally by French/English Tesseract OCR (10,306 words). Original scanned images, OCR text, confidence/geometry and narrative section candidates remain preserved separately. The complete second-layout OCR page check runs in `bdbv-dual-scanned-ocr.yml`; its output is a **prioritisation tool**, not verified PDF table-cell transcription.

### Narrative completeness

The original digitally extractable material from 158 PDFs remains losslessly preserved and reconstructed into 4,744 provisional full-text section segments. The 37 scanned pages are integrated as **178 OCR-only segment candidates**; thus all 161 report identities have recoverable source text or labelled OCR. However, inferred section boundaries are not visually certified. INRB's 54 bilingual response CSVs (3,116 rows) have been pinned and compared; unlocated paraphrases or English translations are not automatically treated as source omissions.

## Remaining requirements for unrestricted historical inference

1. Resolve the *reasons* for the 114 cumulative decreases where original SitRep changes or correction notes are not yet traceable, retaining revision events and unallocated adjustments.
2. Review the 59 conflicting-value zone row cases, two province collisions and remaining nationally ambiguous machine readings on the 32-page visual packet. Source-row identical numbers are not interchangeable without verified geographic/period meaning.
3. Inspect sensitive numerical content on the 37 scanned pages and approve transcriptions individually where they are needed for historical analysis.
4. Conduct an explicit source-to-section QA of narrative boundaries, continuation, OCR and INRB paraphrases using the original page text and visual source. Matching content is not equivalent to correct section attribution.
5. Release a `historical_best_supported` analytical series only after individual decisions carry a source ID, period, geography, revision state, confidence and adjudication status. Keep it distinct from the frozen INRB-vintage review CSV.

**Conclusion:** the previously unstructured exceptions have been reduced to traceable, prioritised evidence questions; they have **not all been scientifically eliminated**. It would be wrong to remove the final source-adjudication caveat from a research publication at this point.
