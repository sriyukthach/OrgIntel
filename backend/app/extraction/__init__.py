"""
Extraction package
"""
from backend.app.extraction.facts import extract_identity_facts, normalize_numeric_amount
from backend.app.extraction.people import extract_people_from_brreg_roles, people_to_facts
from backend.app.extraction.financial import extract_financials_from_regnskap, financials_to_facts
from backend.app.extraction.html_parser import parse_html_document, find_text_excerpt_around_keyword
