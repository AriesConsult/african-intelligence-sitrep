#!/usr/bin/env python3
"""Diagnose shape and persistence of historical INRB cumulative decreases.

This is a revision *triage* engine, not a mechanism that back-allocates deaths,
invents negative incidence, or certifies a historical corrected epidemic series.
"""
import argparse,csv,gzip,json
from collections import Counter,defaultdict
from datetime import date
from pathlib import Path

def diagnose(series_path,flags_path,registry_path,out):
    registry=json.loads(Path(registry_path).read_text(encoding="utf-8"))
    by_date=defaultdict(list)
    for x in registry["documents"].values():by_date[x["report_date"]].append({
        "report_number":x["report_number"],"source_pdf_sha256":x["sha256"]})
    groups=defaultdict(list)
    with gzip.open(series_path,"rt",encoding="utf-8") as f:
        for line in f:
            r=json.loads(line)
            if r.get("status")!="SINGLE_SOURCE_NUMERIC_CANDIDATE":continue
            if not isinstance(r.get("value"),int):continue
            dims=json.dumps(r.get("extra_columns_raw") or {},sort_keys=True,ensure_ascii=False)
            groups[(r["metric_id"],r["geography_raw"],dims)].append(r)
    for group in groups.values():group.sort(key=lambda x:x["date"])
    report=[];counts=Counter();metric_counts=defaultdict(Counter)
    with Path(flags_path).open(encoding="utf-8",newline="") as f:
        for flag in csv.DictReader(f):
            metric=flag["metric_id"];geo=flag["geography_raw"];prev=flag["previous_date"];current=flag["current_date"]
            matches=[(k,v) for k,v in groups.items() if k[0]==metric and k[1]==geo and
                    any(x["date"]==current and x["value"]==int(flag["current_value"]) for x in v)]
            if len(matches)!=1:
                label="AMBIGUOUS_DIMENSION_OR_MISSING_SERIES"
                following=[];gap=None
            else:
                series=matches[0][1]
                position=next(i for i,x in enumerate(series) if x["date"]==current and x["value"]==int(flag["current_value"]))
                following=series[position+1:position+4]
                gap=(date.fromisoformat(current)-date.fromisoformat(prev)).days
                previous_value=int(flag["previous_value"])
                if not following:label="END_OF_AVAILABLE_SERIES_NO_FOLLOWUP"
                elif any(x["value"]>=previous_value for x in following):
                    label="EARLY_REBOUND_TO_PRIOR_CUMULATIVE_LEVEL"
                elif len(following)>=3:
                    label="PERSISTENT_LOWER_SERIES_ACROSS_THREE_OBSERVATIONS"
                else:label="NO_REBOUND_IN_LIMITED_FOLLOWUP"
            current_docs=by_date.get(current,[])
            previous_docs=by_date.get(prev,[])
            counts[label]+=1;metric_counts[metric][label]+=1
            report.append({"metric_id":metric,"geography_raw":geo,"previous_date":prev,
               "previous_value":int(flag["previous_value"]),"current_date":current,
               "current_value":int(flag["current_value"]),"delta":int(flag["delta"]),
               "reporting_gap_days":gap,"following_observations":[{"date":x["date"],"value":x["value"]} for x in following],
               "previous_source_pdf_ids":previous_docs,"current_source_pdf_ids":current_docs,
               "classification":label,
               "explanation_confirmed_in_original_pdf":False,
               "accepted_revised_incidence":False})
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with (out/"cumulative_decline_followup.jsonl").open("w",encoding="utf-8") as f:
        for item in report:f.write(json.dumps(item,ensure_ascii=False)+"\n")
    summary={"schema_version":"bdbv-cumulative-revision-diagnostic-v1",
       "flags_evaluated":len(report),"classification_counts":dict(counts),
       "metric_classifications":{k:dict(v) for k,v in sorted(metric_counts.items())},
       "status":"REVISION_BEHAVIOUR_CLASSIFIED_SOURCE_CAUSATION_UNVERIFIED",
       "limitations":["A rebound is not proof of error or retrospective correction.",
          "A persistent downward shift is not proof of corrected incidence or reporting completeness.",
          "INRB curated cumulative series may carry values forward or incorporate data not in archived PDFs.",
          "All original source values and possible reporting gaps retained. No data values were altered."]}
    (out/"cumulative_decline_followup_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="metric_classifications"},indent=2))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--series",type=Path,required=True)
    p.add_argument("--flags",type=Path,required=True)
    p.add_argument("--registry",type=Path,default=Path("state/registry.json"))
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();diagnose(a.series,a.flags,a.registry,a.out)
