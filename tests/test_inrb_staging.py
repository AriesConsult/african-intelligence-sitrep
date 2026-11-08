"""Preserve INRB raw values, missingness, malformed dates, and provenance."""
from stage_inrb_series import decode_value,candidate_policy

def test_missing_is_never_zero():
 assert decode_value("ND")== (None,"NOT_REPORTED")
 assert decode_value("0")== (0,"NUMERIC_UNVERIFIED")
 assert decode_value("")==(None,"MISSING_OR_NOT_APPLICABLE")

def test_decimal_and_unparseable_values():
 assert decode_value("1 024")== (1024,"NUMERIC_UNVERIFIED")
 assert decode_value("12,5")== (12.5,"NUMERIC_UNVERIFIED")
 assert decode_value("unknown")[1]=="UNPARSEABLE"

def test_cumulative_derivation_not_assumed_direct():
 assert "CARRIED_FORWARD_OR_DERIVED" in candidate_policy("cumulative_confirmed_cases")
