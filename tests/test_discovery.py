import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from discovery import number_from_string, source_from_insp_url,extract_insp_links
from extraction import classify_table,extract_pdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO


def test_number():
    assert number_from_string('SitRep_MVE_174_2026.pdf') == 174
    assert number_from_string('SITREP_MVEBDB_159_20_10_2026.pdf') == 159
    assert number_from_string('random.pdf') is None

def test_avoid_2025():
    assert source_from_insp_url('https://insp.cd/wp-content/uploads/2025/10/SitRep_MVE_040_2025.pdf') is None
    assert source_from_insp_url('https://insp.cd/wp-content/uploads/2026/11/SitRep_MVEBDB_174_04_11_2026.pdf').number == 174

def test_page_discovery():
    html='<a href="https://insp.cd/wp-content/uploads/2026/11/SitRep_MVEBDB_174_04_11_2026.pdf">download</a>'
    assert extract_insp_links(html)[0].number==174

def test_table_classification():
    assert 'contact_tracing' in classify_table('Tableau 4. Synthèse du suivi des contacts contacts à suivre, contacts vus')

def test_pdf_extract_with_generated_fixture():
    bio=BytesIO();doc=SimpleDocTemplate(bio,pagesize=A4)
    story=[Paragraph('Rapport de Situation de la 17ème Epidémie de la maladie à Virus EBOLA / RDC',getSampleStyleSheet()['Normal']),
           Paragraph('SitRep N°174/MVE-BDBV/04/11/2026',getSampleStyleSheet()['Normal']),
           Spacer(1,30),Paragraph('Tableau 4. Synthèse du suivi des contacts',getSampleStyleSheet()['Heading3'])]
    table=Table([['Province','Contacts à suivre','Contacts vus','Taux de suivi'],['Ituri','600','500','83.3%'],['Total','600','500','83.3%']],colWidths=[130,110,100,100]);
    table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.8,colors.grey)]));story.append(table);doc.build(story)
    record=extract_pdf(bio.getvalue(),url='test.pdf',expected_number=174)
    assert record['publication_status']=='NOT_PUBLISHED'
    assert record['report_number']==174
    assert record['n_pages']==1
    assert record['tables']
    assert any('contact_tracing' in t['indicator_families'] for t in record['tables'])
    assert any(t['review_status']=='unverified' for t in record['tables'])

def test_candidate_french_number_and_denominator_safety():
    from candidates import parsed_numeric
    assert parsed_numeric('37 364') == ('37364','count')
    assert parsed_numeric('82,7%') == ('82.7','percent')
    assert parsed_numeric('30 882') == ('30882','count')
    assert parsed_numeric('30 882/37 364') == ('','')
    assert parsed_numeric('ND') == ('','')
