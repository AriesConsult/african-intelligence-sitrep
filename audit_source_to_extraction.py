#!/usr/bin/env python3
"""Audit the catalogued SitRep collection without upgrading extraction to verification.

This audits committed artifacts, NOT original PDF bytes or source-discovery completeness.
Missing candidate pages are coverage signals, not proof of missing text.
"""
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLISHED = ROOT / "published"

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    registry = read(ROOT / "state/registry.json")
    archive = read(PUBLISHED / "source_archive_index.json")
    table_index = read(PUBLISHED / "table_index.json")
    narrative_index = read(PUBLISHED / "narrative_index.json")
    table_by_id = {(r["report_number"], r["sha256"]): r for r in table_index["reports"]}
    narrative_by_id = {(r["report_number"], r["source_sha256"]): r for r in narrative_index["reports"]}
    archive_by_id = archive.get("archived", {})
    report_rows = []
    all_errors = []
    counters = Counter()
    latest = registry.get("latest_by_report", {})
    for key, d in sorted(registry["documents"].items(), key=lambda item: item[1]["report_number"]):
        num, sha = d["report_number"], d["sha256"]
        prefix = f"{num:03d}_{sha[:12]}"
        errors = []
        def problem(reason):
            errors.append(reason)
            all_errors.append({"report_number": num, "reason": reason})
        if key != f"{num:03d}:{sha}":
            problem("registry_identity_mismatch")
        ar = archive_by_id.get(key)
        if not ar:
            problem("archive_inventory_missing")
        elif ar.get("source_sha256") != sha or ar.get("report_number") != num or not ar.get("archive_member"):
            problem("archive_identity_mismatch")
        ti = table_by_id.get((num, sha))
        ni = narrative_by_id.get((num, sha))
        if not ti: problem("table_index_missing")
        if not ni: problem("narrative_index_missing")
        qpath = ROOT / "review_queue" / f"report_{prefix}.json"
        npath = PUBLISHED / "narrative_candidates" / f"{prefix}.json"
        tpath = PUBLISHED / "tables" / f"{prefix}.json"
        pages = d.get("pages") or 0
        raw_tables = 0
        raw_pages = set()
        if not qpath.is_file():
            problem("raw_table_queue_missing")
        else:
            try:
                q = read(qpath)
                if (q.get("report_number"), q.get("sha256")) != (num, sha):
                    problem("raw_queue_identity_mismatch")
                raw = q.get("tables", [])
                raw_tables = len(raw)
                raw_pages = {t["page"] for t in raw if isinstance(t.get("page"), int)}
                if any(p < 1 or p > pages for p in raw_pages):
                    problem("raw_table_page_out_of_range")
            except (OSError, ValueError, KeyError, TypeError):
                problem("raw_table_queue_unreadable")
        narrative_pages = set()
        examined = 0
        candidate_count = 0
        truncated_count = 0
        if not npath.is_file():
            problem("narrative_snapshot_missing")
        else:
            try:
                ns = read(npath)
                if (ns.get("report_number"), ns.get("source_sha256")) != (num, sha):
                    problem("narrative_snapshot_identity_mismatch")
                if ns.get("pages") != pages:
                    problem("narrative_snapshot_page_count_mismatch")
                candidates = ns.get("candidates", [])
                candidate_count = len(candidates)
                examined = ns.get("narrative_blocks_examined") or 0
                truncated_count = sum(bool(c.get("excerpt_truncated")) for c in candidates)
                narrative_pages = {c["page"] for c in candidates if isinstance(c.get("page"), int)}
                if len(candidates) != ns.get("candidates_count"):
                    problem("narrative_candidate_count_mismatch")
                if any(p < 1 or p > pages for p in narrative_pages):
                    problem("narrative_candidate_page_out_of_range")
                if ni and ni.get("candidate_count") != candidate_count:
                    problem("narrative_index_count_mismatch")
            except (OSError, ValueError, KeyError, TypeError):
                problem("narrative_snapshot_unreadable")
        if ti and ti.get("snapshot_path"):
            if not tpath.is_file():
                problem("table_snapshot_missing")
            else:
                try:
                    ts = read(tpath)
                    if ts.get("sha256", ts.get("source_sha256")) != sha:
                        problem("table_snapshot_hash_mismatch")
                except (OSError, ValueError):
                    problem("table_snapshot_unreadable")
        candidate_page_gaps = max(0, pages - len(narrative_pages))
        raw_page_gaps = max(0, pages - len(raw_pages))
        counters.update({"source_pages": pages, "raw_table_detections": raw_tables,
                         "raw_table_pages": len(raw_pages), "narrative_candidate_pages": len(narrative_pages),
                         "narrative_blocks_examined": examined, "narrative_candidates": candidate_count,
                         "truncated_excerpts": truncated_count,
                         "pages_without_narrative_candidates": candidate_page_gaps,
                         "pages_without_table_detections": raw_page_gaps})
        report_rows.append({"report_number": num, "report_date": d.get("report_date"),
            "sha256": sha, "source_pages": pages, "source_provider": d.get("provider"),
            "archive_indexed": bool(ar), "raw_table_detections": raw_tables,
            "pages_with_raw_table_detections": len(raw_pages),
            "pages_without_narrative_candidates": candidate_page_gaps,
            "pages_with_narrative_candidates": len(narrative_pages),
            "candidate_blocks": candidate_count, "examined_narrative_blocks": examined,
            "truncated_candidate_excerpts": truncated_count,
            "tables_machine_validated": ti.get("tables_machine_validated") if ti else None,
            "errors": errors, "status": "INVENTORY_ERROR" if errors else "ARTIFACTS_CROSS_REFERENCED_NOT_FIDELITY_VERIFIED"})
    num_set = {r["report_number"] for r in report_rows}
    numbered_gaps = sorted(set(range(1, max(num_set) + 1)) - num_set)
    counters["reports"] = len(report_rows)
    counters["reports_with_narrative_candidate_page_gaps"] = sum(r["pages_without_narrative_candidates"] > 0 for r in report_rows)
    counters["reports_with_truncated_excerpts"] = sum(r["truncated_candidate_excerpts"] > 0 for r in report_rows)
    counters["reports_with_zero_machine_validated_tables"] = sum(not r["tables_machine_validated"] for r in report_rows)
    counters["reports_with_artifact_errors"] = sum(bool(r["errors"]) for r in report_rows)
    result = {
       "schema_version": "bdbv-source-to-extraction-audit-v1",
       "generated_at": datetime.now(timezone.utc).isoformat(),
       "scope": "All catalogued report/hash identities and committed extraction artifacts",
       "status": "INVENTORY_INCONSISTENT" if all_errors else "ARTIFACT_INVENTORY_CONSISTENT_EXTRACTION_FIDELITY_UNVERIFIED",
       "counters": dict(counters),
       "numbering_gaps_unconfirmed_publications": numbered_gaps,
       "artifact_errors": all_errors,
       "not_verified": [
          "Whether all officially published SitReps have been discovered",
          "Independent SHA-256 rehashing and PDF open/read test of every archived release member",
          "Full page text, figures, captions, headers, footnotes and annex transcription fidelity",
          "Accuracy of each table cell against the original PDF page",
          "Candidate pages and truncated excerpts are not full-text page coverage",
          "Machine-validated table counts are not a source-ingestion completeness measure"],
       "reports": report_rows,
    }
    PUBLISHED.mkdir(parents=True, exist_ok=True)
    (PUBLISHED / "source_to_extraction_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    with (PUBLISHED / "source_to_extraction_audit.csv").open("w", encoding="utf-8", newline="") as f:
        fields = [k for k in report_rows[0] if k != "errors"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r[k] for k in fields} for r in report_rows)
    print(json.dumps({k: v for k, v in result.items() if k != "reports"}, ensure_ascii=False, indent=2))
    if all_errors:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
