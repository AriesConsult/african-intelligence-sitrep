"""Tests for INRB comparison: source coordinates, ambiguity and missing values."""
from reconcile_inrb import banner_candidates,choose

def page(lines):
 return {'text_blocks':[{'lines':[{'spans':[{'text':text,'bbox':[x,y,x+50,y+12]}]} for text,x,y in lines]}]}

def test_early_layout_values_above_header():
 p=page([('8',90,120),('4',245,120),
         ('Cas Confirmés',90,150),('Décès',245,150),('confirmés',245,165)])
 assert choose(banner_candidates(p,'national_cumulative_confirmed_cases'))['pdf_value']==8
 assert choose(banner_candidates(p,'national_cumulative_confirmed_deaths'))['pdf_value']==4

def test_late_layout_values_below_banner():
 p=page([('CUMUL DES',75,200),('CAS',75,215),('10803',75,232),
         ('CUMUL DES',175,200),('DÉCÈS',175,215),('CONFIRMÉS',175,227),('5267',175,240)])
 assert choose(banner_candidates(p,'national_cumulative_confirmed_cases'))['pdf_value']==10803
 assert choose(banner_candidates(p,'national_cumulative_confirmed_deaths'))['pdf_value']==5267

def test_no_number_is_never_imputed():
 p=page([('Cumul des cas confirmés',50,200),('ND',50,222)])
 assert choose(banner_candidates(p,'national_cumulative_confirmed_cases'))['pdf_value'] is None

def test_conflicting_close_numbers_stay_ambiguous():
 sample=[{'value':100,'score':0.25},{'value':101,'score':0.30}]
 result=choose(sample)
 assert result['status']=='AMBIGUOUS_PDF_BANNER_CANDIDATE'
 assert result['pdf_value'] is None
