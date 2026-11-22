"""Regression: SitRep PDF revisions must remain auditable without duplicate dashboard cards."""
import json

import audit_source_to_extraction as audit
import reprocess_tables as reprocess


def test_revision_aware_table_index_and_backward_compatibility(tmp_path, monkeypatch):
    queue = tmp_path / "review_queue"
    published = tmp_path / "published"
    queue.mkdir()
    published.mkdir()
    sha_old = "a" * 64
    sha_new = "b" * 64
    for suffix, sha in (("old", sha_old), ("new", sha_new)):
        (queue / f"report_020_{suffix}.json").write_text(
            json.dumps({"report_number": 20, "source_sha256": sha}),
            encoding="utf-8",
        )
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"documents": {}, "latest_by_report": {}}), encoding="utf-8")

    def fake_extract(item):
        return {
            "report_number": 20,
            "source_sha256": item["source_sha256"],
            "date": "2026-06-02",
            "status": "REVIEW_REQUIRED",
            "tables": {},
            "tables_available": 0,
            "tables_machine_validated": 0,
            "quality_flags": [],
            "source_url": "https://example.org/source.pdf",
        }

    monkeypatch.setattr(reprocess, "extract_five_tables", fake_extract)
    monkeypatch.setattr(reprocess, "update_feed", lambda *args, **kwargs: {"observations": []})
    reprocess.reprocess(queue, published, registry, published / "feed.json")
    idx = json.loads((published / "table_index.json").read_text(encoding="utf-8"))
    assert len(idx["reports"]) == 1  # Existing dashboard contract unchanged
    assert len(idx["all_reports"]) == 2
    assert set(audit.table_records_by_identity(idx)) == {(20, sha_old), (20, sha_new)}
    assert len(audit.table_records_by_identity({"reports": idx["reports"]})) == 1
