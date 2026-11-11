"""Regression against actual archived row structure of SitRep 178 (08 Nov 2026).

PDF digest: d58582670841f28df2e9b8a00453c8f9fb3706c3efbef6a4526e74481faad580.
pdfplumber-lines produces one numbers row followed by a label row, with
additional blank separator rows. Nothing may be machine-validated unless all
provincial rates and national totals reconcile.
"""
from sitrep_tables import table_4


def source_grid():
    head = ["", "Province", "", "Contacts sous suivi", "", "",
            "Contacts vus", "", "", "Taux de suivi", ""]
    blank = [""]*11
    rows = [blank[:], head]
    for label, d, n, rate in [
        ("Ituri","16 447","13 738","83,5%"),
        ("Haut-Uélé","1 370","1 145","83,6%"),
        ("Nord-Kivu","19 029","14 583","76,6%"),
        ("Tshopo","1228","612","49,8%"),
        ("Bas-Uélé","267","263","98,5%"),
        ("Sud-Ubangi","112","103","92,0%"),
        ("Nord-Ubangi","0","0","NA"),
        ("Total","38 453","30 444","79,2%"),
    ]:
        numbers = blank[:]
        numbers[3],numbers[6],numbers[9] = d,n,rate
        label_row = blank[:]
        label_row[1] = label
        rows += [numbers,label_row,blank[:]]
    return {"tables":[{
        "page":5,"table_id":"p5-t11","extractor":"pdfplumber-lines",
        "title_context":"Tableau 4. Situation du suivi des contacts par province, au 8 novembre 2026",
        "rows":rows
    }]}


def test_split_rows_validate():
    result=table_4(source_grid(),{})
    assert result["status"]=="MACHINE_VALIDATED",result["flags"]
    assert result["national"]["contacts_to_follow"]==38453
    assert result["national"]["contacts_seen"]==30444
    assert result["national"]["contact_follow_up_rate"]==79.2
    assert len(result["rows"])==7
    assert sum(x["contacts_to_follow"] for x in result["rows"])==38453
    assert sum(x["contacts_seen"] for x in result["rows"])==30444
    assert result["rows"][-1]["contact_follow_up_rate"] is None


def test_wrong_national_total_rejected():
    document=source_grid()
    document["tables"][0]["rows"][-3][3]="38 454"
    result=table_4(document,{})
    assert result["status"]=="REVIEW_REQUIRED"


def test_missing_numeric_row_rejected():
    document=source_grid()
    document["tables"][0]["rows"][2][3]=""
    result=table_4(document,{})
    assert result["status"]=="REVIEW_REQUIRED"


def test_nonadjacent_rows_not_combined():
    document=source_grid()
    document["tables"][0]["rows"][2],document["tables"][0]["rows"][3]=document["tables"][0]["rows"][3],document["tables"][0]["rows"][2]
    result=table_4(document,{})
    assert result["status"]=="REVIEW_REQUIRED"
