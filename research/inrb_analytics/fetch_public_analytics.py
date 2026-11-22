#!/usr/bin/env python3
"""Acquire public INRB–UMIE aggregates to immutable, unreviewed quarantine.

No publishing, no SitRep/analysis_inputs writes, no private sources.
All source paths are explicit historical snapshots (not a latest-data claim).
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import pathlib
import urllib.request

BASE = "https://raw.githubusercontent.com/INRB-UMIE/"
SOURCES = {
    "ct_dashboard_meta": ("BDBV2026-Contact_Tracing_Analytics", "outputs/2026-11-21/tables/dashboard_meta.json"),
    "ct_weekly_national": ("BDBV2026-Contact_Tracing_Analytics", "outputs/2026-11-21/tables/weekly_national.csv"),
    "ct_patient_journey": ("BDBV2026-Contact_Tracing_Analytics", "outputs/2026-11-21/tables/dashboard_patient_journey.csv"),
    "ct_sar_sensitivity": ("BDBV2026-Contact_Tracing_Analytics", "outputs/2026-11-21/tables/sar_sensitivity.csv"),
    "ct_serial_setting": ("BDBV2026-Contact_Tracing_Analytics", "outputs/2026-11-21/tables/serial_interval_by_setting.csv"),
    "ct_dispersion": ("BDBV2026-Contact_Tracing_Analytics", "outputs/2026-11-21/tables/offspring_dispersion.csv"),
    "inrb_rt": ("BDBV2026-Epidemic_Dashboard", "Data/inrb_dashboard_Rt_data_20261118.csv"),
}

def inspect_bytes(name, data):
    if len(data) > 15_000_000:
        raise ValueError("Source exceeds 15 MB limit")
    value = data.decode("utf-8-sig")
    if name == "ct_dashboard_meta":
        obj = json.loads(value)
        return {"type": "json", "top_level_keys": list(obj) if isinstance(obj, dict) else [], "rows": None}
    reader = csv.DictReader(io.StringIO(value))
    columns = reader.fieldnames or []
    if not columns or len(columns) != len(set(columns)) or any(not c for c in columns):
        raise ValueError("Missing/duplicate CSV column headings")
    rows = list(reader)
    if not rows:
        raise ValueError("Source has no CSV rows")
    if any(None in r for r in rows):
        raise ValueError("CSV row contains more fields than header")
    return {"type": "csv", "columns": columns, "rows": len(rows),
            "empty_by_column": {c: sum(r.get(c) in ("", None) for r in rows) for c in columns}}

def collect(output, vintage, commits, timeout=20):
    dt.date.fromisoformat(vintage)
    known = {repo for repo, _ in SOURCES.values()}
    for repo, commit in commits.items():
        if repo not in known:
            raise ValueError("Unrecognized source repository: " + repo)
        if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit.lower()):
            raise ValueError("Expected a full 40-character source SHA: " + repo)
    if not commits:
        raise ValueError("No repository commits supplied")
    target = pathlib.Path(output) / vintage
    if target.exists():
        raise FileExistsError("Immutable vintage already exists: " + str(target))
    target.mkdir(parents=True)
    ledger = []
    for name, (repo, path) in SOURCES.items():
        if repo not in commits:
            continue
        commit = commits[repo]
        url = BASE + repo + "/" + commit + "/" + path
        record = {"id": name, "url": url, "repository": repo, "path": path,
                  "commit": commit, "acquisition_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "status": "failed"}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AfricanIntelligence-PublicEvidence/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read(15_000_001)
            structure = inspect_bytes(name, data)
            filename = name + pathlib.Path(path).suffix
            (target / filename).write_bytes(data)
            record.update({"status": "quarantined_unreviewed", "filename": filename,
                           "sha256": hashlib.sha256(data).hexdigest(),
                           "byte_size": len(data), "structure": structure})
        except Exception as exc:
            record["error"] = str(exc)
        ledger.append(record)
    (target / "manifest.json").write_text(json.dumps({
        "schema_version": "ai-inrb-acquisition-v1", "vintage_label": vintage,
        "approval": "NOT_APPROVED_FOR_PUBLICATION", "sources": ledger
    }, indent=2) + "\n", encoding="utf-8")
    return ledger

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Quarantine parent directory (not the website)")
    parser.add_argument("--vintage", required=True, help="Acquisition label YYYY-MM-DD")
    parser.add_argument("--commits-json", required=True, help="JSON mapping source repo names to immutable 40-char commit SHAs")
    args = parser.parse_args()
    commits = json.loads(pathlib.Path(args.commits_json).read_text(encoding="utf-8"))
    results = collect(args.output, args.vintage, commits)
    print(json.dumps({"quarantined": sum(x["status"] == "quarantined_unreviewed" for x in results),
                      "failed": sum(x["status"] == "failed" for x in results)}, indent=2))
    if any(x["status"] == "failed" for x in results):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
