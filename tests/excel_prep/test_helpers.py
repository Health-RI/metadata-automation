"""Small pure helpers."""

import pytest

from metadata_automation.excel_prep.class_sheet import relax_cardinality
from metadata_automation.excel_prep.dash import LABEL, URI, expected_dash, has_vocab
from metadata_automation.excel_prep.report import compress_rows
from metadata_automation.excel_prep.workbook import is_literal


@pytest.mark.parametrize(
    "given, expected",
    [("1", "0..1"), ("1..1", "0..1"), ("1..n", "0..n"), ("2..5", "0..5"), ("0..n", "0..n"), ("0..1", "0..1")],
)
def test_relax_cardinality(given, expected):
    assert relax_cardinality(given) == expected


def test_relax_cardinality_unparsable():
    assert relax_cardinality("one or more") is None


def test_compress_rows():
    assert compress_rows([7, 2, 3, 4, 9, 10]) == "2-4, 7, 9-10"


@pytest.mark.parametrize(
    "range_, expected",
    [("rdfs:Literal", True), ("xsd:string", True), ("rdfs:Resource", False), ("rdfs:Class", False)],
)
def test_is_literal(range_, expected):
    assert is_literal(range_) is expected


@pytest.mark.parametrize(
    "value, expected",
    [("", False), ("NA", False), ("n/a", False), ("-", False), ("http://example.org/vocab", True), ("GeoNames", True)],
)
def test_has_vocab(value, expected):
    assert has_vocab(value) is expected


@pytest.mark.parametrize(
    "range_, vocab, expected",
    [
        ("dct:LicenseDocument (IRI)", True, LABEL),
        ("dct:LicenseDocument (IRI)", False, URI),
        ("rdfs:Resource (IRI)", True, URI),
        ("dcat:Dataset (IRI)", True, URI),
    ],
)
def test_expected_dash_label_viewer_needs_vocab(range_, vocab, expected):
    assert expected_dash(range_, "", False, {"dcat:Dataset"}, vocab) == expected
