"""DASH viewer and editor for each property, derived from its range."""

from openpyxl.workbook import Workbook

from metadata_automation.excel_prep.prefix_check import namespace_map, same_term
from metadata_automation.excel_prep.report import Report
from metadata_automation.excel_prep.workbook import (
    class_sheet_names,
    headers,
    is_literal,
    property_rows,
    set_value,
    split_iri_suffix,
    text,
)

URI = ("dash:URIViewer", "dash:URIEditor")
LABEL = ("dash:LabelViewer", "dash:URIEditor")
DETAILS = ("dash:DetailsViewer", "dash:BlankNodeEditor")
DATE_TIME = ("dash:LiteralViewer", "dash:DateTimePickerEditor")
TEXT_AREA = ("dash:LiteralViewer", "dash:TextAreaEditor")
TEXT_FIELD = ("dash:LiteralViewer", "dash:TextFieldEditor")

DESCRIPTION_PROPERTY = "dct:description"
GENERIC_RESOURCE = "rdfs:Resource"
VOCAB_COLUMN = "Controlled vocabulary (if applicable)"
NO_VOCAB = {"na", "n/a", "none", "nan", "-"}


def has_vocab(value: str) -> bool:
    """A controlled vocabulary cell is meaningful unless empty or a placeholder such as NA."""
    return bool(value) and value.lower() not in NO_VOCAB


def expected_dash(
    range_: str, node: str, is_description: bool, model_classes: set[str], vocab: bool = False
) -> tuple[str, str] | None:
    """Return ``(viewer, editor)`` for a prepared range, or None when no rule applies.

    Rules, in order: a range ending in (IRI) is a URI, shown by its label when it is
    an outside class (not a model class or rdfs:Resource) with a controlled vocabulary; a range with a
    node shape links to another class of the model; xsd:dateTime gets a date picker;
    dct:description gets a text area; any other literal gets a text field.
    """
    base, has_iri = split_iri_suffix(range_)
    if has_iri:
        outside = base not in model_classes and base != GENERIC_RESOURCE
        return LABEL if outside and vocab else URI
    range_ = base
    if node:
        return DETAILS
    if range_ == "xsd:dateTime":
        return DATE_TIME
    if is_literal(range_):
        return TEXT_AREA if is_description else TEXT_FIELD
    return None


def apply_dash_rules(wb: Workbook, model_classes: set[str], report: Report) -> None:
    """Fill empty viewer/editor cells with the expected value; report existing values that differ."""
    namespaces = namespace_map(wb)
    for name in class_sheet_names(wb):
        ws = wb[name]
        cols = headers(ws)
        for row in property_rows(ws, cols):
            is_description = same_term(text(ws, row, cols.get("Property URI")), DESCRIPTION_PROPERTY, namespaces)
            expected = expected_dash(
                text(ws, row, cols.get("Range")),
                text(ws, row, cols["SHACL_sh:node"]),
                is_description,
                model_classes,
                has_vocab(text(ws, row, cols.get(VOCAB_COLUMN))),
            )
            if expected is None:
                continue
            for column, value in zip(("SHACL_dash:viewer", "SHACL_dash:editor"), expected, strict=True):
                current = text(ws, row, cols[column])
                if not current:
                    set_value(ws, row, cols[column], value, report, column, "derived from range")
                elif current != value:
                    report.issue(name, row, column, f"expected '{value}', found '{current}'")
