"""Scanned historical source admission must reject unexpected PDF bytes."""
from pathlib import Path
import pytest
from stage_scanned_sources import SOURCES, collect

def test_visual_review_registry_has_three_pinned_source_hashes():
    assert set(SOURCES)=={7,8,9}
    assert all(len(r["sha"])==64 and r["pages"]>=1 for r in SOURCES.values())

def test_bad_pdf_never_enters_archive_as_accepted(tmp_path):
    with pytest.raises(ValueError,match="unexpected source bytes"):
        collect(tmp_path,fetch_bytes=lambda number,url:b"%PDF-FAKE SOURCE")
