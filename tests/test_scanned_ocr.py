"""Scanned OCR words retain confidence and do not claim validation."""
import pytest
from recover_scanned_sitreps_ocr import parse_tsv

def test_parse_tsv_preserves_word_boxes():
    raw="level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    raw+="5\t1\t1\t1\t1\t1\t10\t20\t30\t15\t87.2\tIturi\n"
    raw+="5\t1\t1\t1\t1\t2\t45\t20\t10\t15\t-1\t\n"
    result=parse_tsv(raw)
    assert len(result)==1
    assert result[0]["word"]=="Ituri"
    assert result[0]["confidence"]==87.2
    assert result[0]["left"]==10
