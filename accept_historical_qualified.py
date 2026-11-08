#!/usr/bin/env python3
"""Qualified BDBV 2026 historical release acceptance gate.

Accepts preservation and explicitly bounded *descriptive use* of pinned curated
records, not epidemiological truth or reconstructed incident series. Source-PDF
verbatim readings are a separate verified view. Fails closed on wrong versions,
lost rows, unlisted scans, invalid values, and unexpected status codes.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path

EXPECTED_COMMIT="c00b8843e6ebae8f0cd846bc43cb564a3893bfd9"
VERIFIED_KLASSES={"CURATED_AND_VERBATIM_PDF_CONCORDANT","CURATED_AND_VERBATIM_PDF_DIFFERENT_RETAIN_BOTH"}
VALID_KLASSES={"CURATED_ONLY_SOURCE_PDF_REVIEW_PENDING",*VERIFIED_KLASSES}
VALID_EVIDENCE={
 "PDF_MACHINE_VALIDATED_CONCORDANCE_VISUAL_QA_PENDING",
 "PDF_CANDIDATE_CONCORDANCE_REVIEW_PENDING",
 "PDF_INRB_DIFFERENCE_PENDING_ADJUDICATION",
 "AMBIGUOUS_PDF_ROW_MATCH",
 "PDF_EVIDENCE_UNRESOLVED",
 "INRB_VINTAGE_ONLY_NO_CELL_LINK",
 "AMBIGUOUS_MULTIPLE_CONCORDANCE_RECORDS",
 "SINGLE_SOURCE_NUMERIC_CANDIDATE",
 "INVALID_SOURCE_DATE","EXPLICIT_ND","NONNUMERIC_OR_MISSING",
 "UNALLOCATED_GEOGRAPHY","CONFLICTING_DUPLICATE_SOURCE_ROWS",
 "REPEATED_IDENTICAL_SOURCE_ROW"
}
RESTRICTED_EVIDENCE={"PDF_INRB_DIFFERENCE_PENDING_ADJUDICATION",
                     "AMBIGUOUS_PDF_ROW_MATCH",
                     "AMBIGUOUS_MULTIPLE_CONCORDANCE_RECORDS"}
NUMERIC_STATUS="SINGLE_SOURCE_NUMERIC_CANDIDATE"
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def acceptance(two_views,aligned,alignment_summary,verified_csv,revision_csv,scanned_index,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    source=json.loads(Path(alignment_summary).read_text(encoding="utf-8"))
    scanned=json.loads(Path(scanned_index).read_text(encoding="utf-8"))
    blocked_dates={r["report_date"] for r in scanned["source_records"]}
    if {r["report_number"] for r in scanned["source_records"]}!={7,8,9}:
        raise ValueError("Unreviewed scanned exclusion registry changed")
    if source["source_inrb_commit"]!=EXPECTED_COMMIT:raise ValueError("Historical upstream revision has changed")
    verified=list(csv.DictReader(Path(verified_csv).open(encoding="utf-8-sig",newline="")))
    if len(verified)!=17:raise ValueError("Unexpected verified source-cell count")
    verified_by_key={}
    for r in verified:
        if r["verbatim_transcription_verified"]!="True":raise ValueError("Unverified source-cell admitted")
        key=(r["report_date"],r["metric_id"],r["geography"].casefold())
        if key in verified_by_key:raise ValueError("Nonunique verified original PDF value")
        verified_by_key[key]=r
    decreases=set()
    with Path(revision_csv).open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            decreases.add((r["current_date"],r["metric_id"],r["geography_raw"]))
    if len(decreases)!=114:raise ValueError("Unexpected historical cumulative decrease register")
    with gzip.open(two_views,"rt",encoding="utf-8") as f:
        view=[json.loads(x) for x in f if x.strip()]
    by_key=defaultdict(list)
    for x in view:by_key[(x["date"],x["metric_id"],x["geography_raw"])].append(x)
    counts=Counter();tiers=Counter();exclusions=Counter();by_metric=defaultdict(Counter)
    out_path=out/"historical_qualified_release.csv"
    excluded_path=out/"historical_exclusions.csv"
    fields=["date","metric_id","geography_raw","source_value_raw","curated_value",
      "original_pdf_verified_value","curated_revision_commit","curated_csv_provenance_json",
      "pdf_sha256","pdf_report_number","pdf_page","original_pdf_review_source",
      "source_evidence_class","curated_extraction_status","acceptance_tier",
      "permitted_use","excluded_from_derived_incidence","curated_value_eligible_for_qualified_descriptive_use",
      "scanned_report_exclusion_applies","decreasing_cumulative_step","exclusion_reason",
      "production_feed_modified","independent_epidemiological_validation"]
    with gzip.open(aligned,"rt",encoding="utf-8") as records,          out_path.open("w",encoding="utf-8",newline="") as fo,          excluded_path.open("w",encoding="utf-8",newline="") as fx:
        writer=csv.DictWriter(fo,fieldnames=fields);writer.writeheader()
        ew=csv.DictWriter(fx,fieldnames=fields);ew.writeheader()
        for line in records:
            row=json.loads(line)
            key=(row["date"],row["metric_id"],row["geography_raw"])
            possible=by_key.get(key,[])
            # Match exact upstream source-row identities, not just date/zone.
            source_refs=json.dumps(row.get("source_records") or [],sort_keys=True,ensure_ascii=False)
            candidates=[x for x in possible if json.dumps(x.get("curated_source_rows") or [],sort_keys=True,ensure_ascii=False)==source_refs]
            if len(candidates)!=1:raise ValueError("Curated-to-two-view source-row identity is not one-to-one")
            x=candidates[0]
            if x["curated_inrb_commit"]!=EXPECTED_COMMIT or row["inrb_commit"]!=EXPECTED_COMMIT:
                raise ValueError("Mixed historic source revisions")
            vstatus=row["status"];evclass=row["evidence_class"]
            if evclass not in VALID_EVIDENCE:raise ValueError("Unexpected evidence class "+str(evclass))
            if x["two_view_consistency"] not in VALID_KLASSES:raise ValueError("Unexpected two-view classification")
            if row["date"] in blocked_dates:
                # A same-date source can exist in the 158 original PDFs;
                # retain it only if verified to an original non-scanned PDF.
                verified_non_scan=bool(x.get("verbatim_pdf_value_verified")) and x.get("direct_pdf_report_number") not in (7,8,9)
                scanned_risk=not verified_non_scan
            else:scanned_risk=False
            decreasing=key in decreases
            verified_pdf=x.get("direct_pdf_as_reported")
            has_verified=bool(x.get("verbatim_pdf_value_verified"))
            if has_verified:
                covered=(row["date"],row["metric_id"],row["geography_raw"].casefold())
                if covered not in verified_by_key or int(verified_by_key[covered]["verbatim_source_value"])!=verified_pdf:
                    raise ValueError("Visual PDF review linkage is not verified")
            reasons=[]
            if scanned_risk:reasons.append("SCANNED_SOURCE_DATE_UNVERIFIED_NO_DIRECT_NONSCANNED_SOURCE")
            if vstatus!=NUMERIC_STATUS or type(row.get("decision_value")) not in (int,float):
                reasons.append("CURATED_VALUE_NOT_NUMERIC_OR_NOT_SINGLE_SOURCE")
            if evclass in RESTRICTED_EVIDENCE:reasons.append("AMBIGUOUS_OR_DISCORDANT_PDF_CANDIDATE")
            if decreasing:reasons.append("CUMULATIVE_DOWNWARD_REVISION_UNADJUDICATED")
            if has_verified and verified_pdf!=row.get("decision_value"):
                reasons.append("VERIFIED_VERBATIM_PDF_DIFFERS_FROM_CURATED_VINTAGE")
            if reasons:
                tier="RESTRICTED_EVIDENCE_ONLY"
                allowed="source_audit_and_discrepancy_review_only"
                accepted=False
            elif has_verified:
                tier="A_PDF_VERBATIM_CONCORDANT"
                allowed="qualified_as_reported_descriptive_only"
                accepted=True
            elif evclass in ("PDF_MACHINE_VALIDATED_CONCORDANCE_VISUAL_QA_PENDING",
                             "PDF_CANDIDATE_CONCORDANCE_REVIEW_PENDING"):
                tier="B_DUAL_TRANSCRIPTION_CONCORDANCE"
                allowed="clearly_labelled_provisional_descriptive_only"
                accepted=True
            else:
                tier="C_PINNED_CURATED_INRB_ONLY"
                allowed="clearly_labelled_provisional_descriptive_only"
                accepted=True
            record={
             "date":row["date"],"metric_id":row["metric_id"],
             "geography_raw":row["geography_raw"],
             "source_value_raw":row.get("source_value_raw"),
             "curated_value":row.get("decision_value"),
             "original_pdf_verified_value":verified_pdf,
             "curated_revision_commit":EXPECTED_COMMIT,
             "curated_csv_provenance_json":source_refs,
             "pdf_sha256":x.get("direct_pdf_sha256") or "",
             "pdf_report_number":x.get("direct_pdf_report_number") or "",
             "pdf_page":x.get("direct_pdf_page") or "",
             "original_pdf_review_source":x.get("direct_pdf_review_document") or "",
             "source_evidence_class":evclass,"curated_extraction_status":vstatus,
             "acceptance_tier":tier,"permitted_use":allowed,
             "excluded_from_derived_incidence":"TRUE",
             "curated_value_eligible_for_qualified_descriptive_use":"TRUE" if accepted else "FALSE",
             "scanned_report_exclusion_applies":"TRUE" if scanned_risk else "FALSE",
             "decreasing_cumulative_step":"TRUE" if decreasing else "FALSE",
             "exclusion_reason":";".join(reasons),
             "production_feed_modified":"FALSE",
             "independent_epidemiological_validation":"FALSE"}
            writer.writerow(record)
            if reasons:ew.writerow(record)
            counts["total"]+=1;tiers[tier]+=1;by_metric[row["metric_id"]][tier]+=1
            for reason in reasons:exclusions[reason]+=1
    if counts["total"]!=15726 or counts["total"]!=source["records"] or len(view)!=15726:
        raise ValueError("Historical source row cardinality changed")
    if len(by_metric)!=31:raise ValueError("Historical indicator set changed")
    if sum(tiers.values())!=counts["total"]:raise ValueError("Incomplete acceptance tier coverage")
    with (out/"metric_tier_coverage.csv").open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=["metric_id","acceptance_tier","rows"]);wr.writeheader()
        for metric,groups in sorted(by_metric.items()):
            for tier,count in sorted(groups.items()):wr.writerow({"metric_id":metric,"acceptance_tier":tier,"rows":count})
    final={"schema_version":"bdbv-qualified-historical-acceptance-v1",
      "status":"QUALIFIED_DESCRIPTIVE_DATASET_RELEASED_NOT_FULL_SCIENTIFIC_CERTIFICATION",
      "source_repo":"INRB-UMIE/BDBV2026-Data",
      "source_commit":EXPECTED_COMMIT,"observations_retained":counts["total"],
      "indicators":len(by_metric),"reviewed_verbatim_pdf_readings":len(verified),
      "acceptance_tiers":dict(tiers),"restriction_reasons_not_mutually_exclusive":dict(exclusions),
      "scanned_sources_excluded_from_numerical_verification":[7,8,9],
      "cumulative_decreases_flagged":len(decreases),
      "prohibited_uses":["Daily incident count derived by differencing unadjudicated cumulative observations",
         "Treating the provisional 15726 records as independently source verified",
         "Inferring historical date allocation of retrospective corrections",
         "Autoapproval of machine OCR or scanned SitRep 007-009 figures",
         "Replacing archived original PDF values or production analytical feed"],
      "scope_accepted":["Source-backed descriptive inventory", "Qualified exploration of provisional levels with tier labels",
         "Citation of specifically visually verified verbatim PDF readings as reported figures"],
      "separate_narrative_track":"Narrative completeness not a prerequisite for this descriptive numerical release; remains noncertified.",
      "immutable_provenance":{"aligned_input_sha256":digest(aligned),"two_view_input_sha256":digest(two_views),
         "verified_pdf_input_sha256":digest(verified_csv),
         "cumulative_revision_input_sha256":digest(revision_csv),
         "scanned_index_sha256":digest(scanned_index)},
      "production_feed_modified":False,
      "all_historical_epidemiological_values_scientifically_certified":False}
    (out/"historical_acceptance_report.json").write_text(json.dumps(final,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    md=["# BDBV 2026 — QUALIFIED HISTORICAL EVIDENCE ACCEPTANCE",
       "", "**Decision:** Publish a version-pinned, source-linked historical descriptive dataset, not a fully scientifically certified incidence series.",
       "",f"**Original INRB records retained:** {counts['total']:,} across {len(by_metric)} indicators.",
       f"**Individually visually verified original PDF transcriptions:** {len(verified)}.",
       "", "## Acceptance tiers", ""]
    for tier,count in sorted(tiers.items()):md.append(f"- **{tier}:** {count:,} rows")
    md+=["","## Restrictions and exclusions",""]
    for reason,count in sorted(exclusions.items()):md.append(f"- {reason}: {count:,} rows (categories can overlap)")
    md+=["","The three scanned SitReps 007–009 remain in immutable source custody; their OCR text and numerical values are not certified.",
        "All 114 known cumulative declines remain flagged and cannot support unreviewed daily-incidence calculation.",
        "The original and curated historical values remain distinct, including documented SitRep 169 discrepancies.",
        "Narrative completeness remains a separate review track.",
        "No existing production feed was modified; this is a newly qualified research evidence release.",
        "",
        "## Scientific boundary",
        "PDF–INRB numeric agreement, source-page co-occurrence and machine OCR do not independently validate epidemiological correctness. This qualification must accompany every downstream use.",
        ""]
    (out/"HISTORICAL_ACCEPTANCE_REPORT.md").write_text("\n".join(md),encoding="utf-8")
    print(json.dumps({k:v for k,v in final.items() if k!="immutable_provenance"},indent=2))
    return final

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--two-views",type=Path,required=True)
    p.add_argument("--aligned",type=Path,required=True)
    p.add_argument("--alignment-summary",type=Path,required=True)
    p.add_argument("--verified-pdf",type=Path,required=True)
    p.add_argument("--revisions",type=Path,required=True)
    p.add_argument("--scanned-index",type=Path,default=Path("published/scanned_source_index.json"))
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    acceptance(a.two_views,a.aligned,a.alignment_summary,a.verified_pdf,a.revisions,a.scanned_index,a.out)
