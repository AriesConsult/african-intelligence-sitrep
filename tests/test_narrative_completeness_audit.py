"""Full narrative page audit must preserve original text despite truncated candidates."""
import gzip,hashlib,json
from audit_narrative_completeness import audit

def test_truncated_candidate_does_not_truncate_full_page(tmp_path):
    full=tmp_path/"full";(full/"full_pages").mkdir(parents=True)
    pub=tmp_path/"pub";(pub/"narrative_candidates").mkdir(parents=True)
    sha="a"*64;text="1. COORDINATION\nThis is a considerably longer source passage about the outbreak."
    pg={"page":1,"text_sorted":text,"text_sha256":hashlib.sha256(text.encode()).hexdigest(),"image_locations":[]}
    with gzip.open(full/"full_pages/001.json.gz","wt",encoding="utf-8") as f:
        json.dump({"source_sha256":sha,"report_number":1,"report_date":"2026-05-14","pages":[pg]},f)
    file=full/"full_pages/001.json.gz"
    (full/"page_extraction_audit.json").write_text(json.dumps({
        "status":"ALL_ARCHIVED_PDFS_EXTRACTED_FIDELITY_REVIEW_PENDING",
        "records":[{"report_number":1,"source_sha256":sha,
        "extraction_file":"full_pages/001.json.gz",
        "compressed_sha256":hashlib.sha256(file.read_bytes()).hexdigest()}]}))
    snap={"report_number":1,"source_sha256":sha,
          "candidates":[{"page":1,"excerpt":"This is a...", "excerpt_truncated":True}]}
    (pub/"narrative_candidates/001_aaaa.json").write_text(json.dumps(snap))
    (pub/"narrative_index.json").write_text(json.dumps({
        "reports":[{"report_number":1,"source_sha256":sha,"snapshot_path":"narrative_candidates/001_aaaa.json"}]}))
    scan=tmp_path/"scan.json";scan.write_text('{"source_records":[]}')
    result=audit(full,pub,scan,tmp_path/"out")
    assert result["truncated_previous_candidate_excerpts"]==1
    assert result["full_text_pages"]==1
    with gzip.open(tmp_path/"out/full_narrative_page_evidence.jsonl.gz","rt") as f:
        row=json.loads(f.readline())
    assert row["full_text"]==text
    assert result["status"].endswith("UNVERIFIED")
