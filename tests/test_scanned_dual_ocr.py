"""Different OCR layout outputs must preserve numeric disagreement alerts."""
from audit_scanned_ocr_dual import compare_text

def test_numeric_mismatch_never_reclassified_as_agreement():
    a=compare_text("Ituri cas 9065 décès 4381","Ituri cas 9066 décès 4381")
    assert a["numeric_token_sequences_identical"] is False
    assert a["numerically_agreeing_token_count"]==0

def test_same_tokens_still_not_certified():
    a=compare_text("Cas 4294 Décès 1960","Cas 4294 Décès 1960")
    assert a["numeric_token_sequences_identical"] is True
    assert a["normalized_text_similarity"]==1
