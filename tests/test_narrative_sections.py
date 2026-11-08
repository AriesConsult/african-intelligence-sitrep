"""All extracted source characters must survive heuristic section staging."""
from stage_narrative_sections import split_document,candidate_heading

def test_numbered_heading_is_candidate_and_document_round_trips():
    doc={"pages":[{"text_sorted":"FOREWORD\n1. COORDINATION\nText one.\n"},
                  {"text_sorted":"Continuation two.\n2. LABORATOIRE\nText three."}]}
    sections,length=split_document(doc)
    joined="".join(s["text"] for s in sections)
    assert joined=="FOREWORD\n1. COORDINATION\nText one.\n\n\f\nContinuation two.\n2. LABORATOIRE\nText three."
    assert len(joined)==length
    assert len(sections)>=3
    assert any(x["heading_candidate"]=="1. COORDINATION" for x in sections)
    assert all(s["approved_for_interpretation"] is False for s in sections)

def test_numeric_table_rows_not_called_sections():
    assert candidate_heading("12 34 56 78") is None
