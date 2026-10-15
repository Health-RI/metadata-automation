"""Prefix consistency check."""

import pytest
from openpyxl import Workbook

from metadata_automation.excel_prep.prefix_check import check_prefixes, same_term


class TestPrefixCheck:
    @pytest.fixture
    def findings(self):
        wb = Workbook()
        prefixes = wb.active
        prefixes.title = "prefixes"
        for row in [
            ("prefix", "namespace"),
            ("dct", "http://purl.org/dc/terms/"),
            ("dcterms", "http://purl.org/dc/terms/"),
            ("xsd", "http://www.w3.org/2001/XMLSchema#"),
            ("xsd", "http://example.org/xsd#"),
            ("DCAT", "http://www.w3.org/ns/dcat#"),
        ]:
            prefixes.append(row)
        sheet = wb.create_sheet("Thing")
        for row in [
            ("Property label", "Property URI", "Range"),
            ("legislation", "dcat:legislation", "eli:LegalResource (IRI)"),
            ("page", "http://purl.org/dc/terms/page ", "rdfs:Resource  (IRI)"),
            ("name", "dct:name", "Literal"),
        ]:
            sheet.append(row)
        return [f"{f.cell} | {f.message}" for f in check_prefixes(wb)]

    @pytest.mark.parametrize(
        "expected",
        [
            "'xsd' registered in rows 4, 5 with conflicting namespaces",
            "namespace http://purl.org/dc/terms/ registered under several prefixes: dct, dcterms",
            "prefix spelled in different cases: DCAT, dcat",
            "'eli' has no registered namespace, used in: Thing / Range / row 2 (dcat:legislation)",
            "'dcat' has no registered namespace",
            "Thing / Range / row 3 | stray whitespace in 'rdfs:Resource  (IRI)'",
            "Thing / Property URI / row 3 | stray whitespace",
            "full IRI 'http://purl.org/dc/terms/page', use CURIE 'dct:page'",
            "Thing / Range / row 4 | no prefix in 'Literal'",
        ],
    )
    def test_finds(self, findings, expected):
        assert any(expected in f for f in findings), findings


@pytest.mark.parametrize(
    "value, namespaces, expected",
    [
        ("dct:title", {}, True),
        ("dcterms:title", {"dct": "http://purl.org/dc/terms/", "dcterms": "http://purl.org/dc/terms/"}, True),
        ("dcterms:title", {"dcterms": "http://purl.org/dc/terms/"}, False),
        ("dct:description", {"dct": "http://purl.org/dc/terms/"}, False),
    ],
)
def test_same_term(value, namespaces, expected):
    assert same_term(value, "dct:title", namespaces) is expected
