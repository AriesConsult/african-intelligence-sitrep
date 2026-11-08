"""French INRB operational narratives use day-month-year dates and uncertain pillars."""
from stage_inrb_operational_narratives import parse_date, category

def test_day_month_year_not_iso_or_us_month_day():
    assert parse_date("05-11-2026")=="2026-11-05"
    assert parse_date("2026-11-05") is None
    assert parse_date("31-02-2026") is None

def test_response_pillars_and_geography_explicit():
    prefix="data/public_health_response/processed/public_health_response__"
    assert category(prefix+"national_epidemiological_coordination_fr__daily.csv")==("national","epidemiological_coordination","fr")
    assert category(prefix+"provincial_epidemiological_security_en__daily.csv")==("province","epidemiological_security","en")
    assert category(prefix+"epidemiological_laboratory_fr__daily.csv")==("health_zone","epidemiological_laboratory","fr")
