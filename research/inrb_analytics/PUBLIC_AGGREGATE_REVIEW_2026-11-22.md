# Public INRB–UMIE analytical review — 22 November 2026

**Status:** descriptive displays from institutional public aggregates; no independent case-level reproduction or epidemiological impact attribution.

## Pinned source inventory

Public producer: [INRB–UMIE Contact Tracing Analytics](https://github.com/INRB-UMIE/BDBV2026-Contact_Tracing_Analytics) at commit `4d7fd1720d3d15af76b589165c250140ac0c979b`. Upstream **reporting/data cut: 2026-11-21**; onset end 2026-10-26; last full week 2026-11-09; distinct from GitHub commit date.

| Filename (under `outputs/2026-11-21/tables/`) | Git blob SHA | Evidence |
|---|---|---|
| `dashboard_meta.json` | `ce396e6aed6182d1bb9fa68c3bb4587b34519051` | Defines distinct data and onset coverage |
| `dashboard_patient_journey.csv` | `d43f47c35bd9fc710e1200bc638576e8079fe8b3` | Onset to milestone delays, per-step n and IQR |
| `sar_sensitivity.csv` | `67c04668410942ef4f8dd2f56e0c2ee6a491b45f` | Main and strict SAR plus other sensitivity definitions |
| `dashboard_fu21_by_month.csv` | `39d6e2a509bb50036027d961de161a8b614e9293` | Completed 21-day follow-up by month |
| `weekly_national.csv` | `c40557e0bdca799000a87e8866621a55e141fbb2` | Cases previously listed as contacts, source-specific weekly case denominator |

## Observations directly transcribed from public aggregates

* **Main SAR**: 276 / 20,672 eligible source–contact pairs = 1.335% (source Wilson 95% CI 1.187–1.501%).
* **Strict linelist-only SAR**: 144 / 20,672 = 0.697% (source Wilson 95% CI 0.592–0.819%). This is **definition sensitivity**, not a temporal change.
* **Onset to notification**: median 4 days, IQR 2–7, n=8,692. Onset to specimen taken median 7 days, IQR 3–12, n=8,661; onset to lab-result median 7 days, IQR 4–13, n=8,674. Different case groups; never subtract their medians to estimate step transitions.
* **21-day follow-up completed**: 5,488 / 25,120 eligible contacts across the displayed April–October monthly rows. This reconciles with `dashboard_meta.json`. This is **not** the INSP daily contact-seen / contacts-to-follow statistic.
* Previously registered contacts are reported against weekly new cases in the **INRB analytical extract**; not directly interchangeable with WHO retrospective recognition proportions or contact follow-up percentages.

The source README defines the SAR denominator as source–contact pairs from confirmed/probable sources, with contact first follow-up or registration no later than 21 days before the data cut. Main outcome additionally includes contact-tracing confirmed/validated status unless the linelist overrides it as not-a-case. Alternative definitions and source-person linkage issues materially affect interpretation.

## Rt caution

The public INRB `inrb_dashboard_Rt_data_20261118.csv` includes national and province values and **last national estimate date 2026-11-05**, despite its 18 November filename. It should not be presented as an Rt estimate for 18 November. No direct overlay with African Intelligence apparent Rt is approved until onset/report-date incidence, methods, generation interval and historical revisions are aligned.

## Safe scope / status

The isolated utility under `research/inrb_analytics/` remains acquisition-only, operating on explicitly pinned upstream commits and writing to non-public quarantine. Website publication is a distinct step: a manually reviewed JSON snapshot is staged within the existing `bdvd2026/` module, **never** within SitRep `published/`, bulletin inputs or approved publication archives.

**Unresolved:** independent input-level reproducibility impossible without restricted line lists; historical revision-vintage reconstruction not done; clinical age–sex outcome aggregates not confirmed publicly available; no spatial model/risk overlay. Keep `Age, Sex & Outcomes` evidence register qualified and do not infer missing or suppressed cells.

Review performed from public GitHub file bytes and source README through authenticated GitHub access, with internal arithmetic checks; no institutional endorsement or external validation inferred.
