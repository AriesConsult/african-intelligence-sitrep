"""Regression tests for contact Table 4 with pdfplumber merged-header grid.

SitRep 178 (8 November 2026), PDF SHA256:
d58582670841f28df2e9b8a00453c8f9fb3706c3efbef6a4526e74481faad580.
Printed province names sit in column 0 while the centered Province header
sits in column 1; other printed header columns remain aligned.
"""
from sitrep_tables import table_4


def report_178_contact_table():
    def row(name, follow, seen, rate):
        return [name, None, None, follow, "", "", seen, "", "", rate, ""]
    header = ["", "Province", "", "Contacts sous suivi", "", "",
              "Contacts vus", "", "", "Taux de suivi", ""]
    rows = [header,
            row("Ituri", "16 447", "13 738", "83,5%"),
            row("Haut-Uélé", "1 370", "1 145", "83,6%"),
            row("Nord-Kivu", "19 029", "14 583", "76,6%"),
            row("Tshopo", "1228", "612", "49,8%"),
            row("Bas-Uélé", "267", "263", "98,5%"),
            row("Sud-Ubangi", "112", "103", "92,0%"),
            row("Nord-Ubangi", "0", "0", "NA"),
            row("Total", "38 453", "30 444", "79,2%")]
    return {'tables': [{
        'page': 5, 'table_id': 'p5-t11', 'extractor': 'pdfplumber-lines',
        'title_context': 'Tableau 4. Situation du suivi des contacts par province, au 8 novembre 2026',
        'rows': rows,
    }]}


def test_sitrep_178_merged_province_heading_machine_validates():
    t = table_4(report_178_contact_table(), {})
    assert t['status'] == 'MACHINE_VALIDATED', t['flags']
    assert len(t['rows']) == 7
    assert t['national']['contacts_to_follow'] == 38453
    assert t['national']['contacts_seen'] == 30444
    assert t['national']['contact_follow_up_rate'] == 79.2
    assert sum(x['contacts_to_follow'] for x in t['rows']) == 38453
    assert sum(x['contacts_seen'] for x in t['rows']) == 30444
    assert t['rows'][-1]['scope'] == 'Nord-Ubangi'
    assert t['rows'][-1]['contact_follow_up_rate'] is None


def test_sitrep_178_wrong_national_total_stays_blocked():
    doc = report_178_contact_table()
    doc['tables'][0]['rows'][-1][3] = '38 454'
    t = table_4(doc, {})
    assert t['status'] == 'REVIEW_REQUIRED'
    assert any(f['reason'] in ('table4_provincial_sum_mismatch',
                                'table4_invalid_rate_or_denominator') for f in t['flags'])


def test_sitrep_178_nonadjacent_label_does_not_get_promoted():
    doc = report_178_contact_table()
    # Unknown labels must not be accepted by a loose left-column heuristic.
    doc['tables'][0]['rows'][1][0] = 'NOT A PROVINCE'
    t = table_4(doc, {})
    assert t['status'] == 'REVIEW_REQUIRED'
    assert len(t['rows']) == 6
    assert any(f['reason'] == 'table4_provincial_sum_mismatch' for f in t['flags'])
