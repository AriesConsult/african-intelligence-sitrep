"""Approval CSV header QA: preserve strict approval gating and source provenance."""
from review_approved import read_approvals

HEADER=("report_number,source_sha256,date,page,table_id,row_label,"
        "column_header,raw_value,metric_id,scope,value,unit,reviewed_by,review_note")


def test_blank_line_before_valid_header_is_not_a_failure(tmp_path):
    p=tmp_path/'approved_observations.csv'
    p.write_text("\n"+HEADER+"\n",encoding="utf-8")
    accepted,errors=read_approvals(p,tmp_path)
    assert accepted==[]
    assert errors==[]


def test_blank_lines_and_bom_before_valid_header(tmp_path):
    p=tmp_path/'approved_observations.csv'
    p.write_text("\ufeff\n\n"+HEADER+"\n",encoding="utf-8")
    accepted,errors=read_approvals(p,tmp_path)
    assert accepted==[]
    assert errors==[]


def test_missing_required_header_cannot_approve_anything(tmp_path):
    p=tmp_path/'approved_observations.csv'
    p.write_text("\nreport_number,date,value\n",encoding="utf-8")
    accepted,errors=read_approvals(p,tmp_path)
    assert accepted==[]
    assert len(errors)==1
    assert errors[0]['line']==2
    assert errors[0]['reason']=='manual_approval_csv_header_missing_required_columns'


def test_invalid_row_preserves_physical_line_number(tmp_path):
    p=tmp_path/'approved_observations.csv'
    p.write_text("\n"+HEADER+"\n"+",".join(["invalid"]*14)+"\n",encoding="utf-8")
    accepted,errors=read_approvals(p,tmp_path)
    assert accepted==[]
    assert len(errors)==1
    assert errors[0]['line']==3
