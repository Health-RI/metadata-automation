"""DASH viewer and editor for each property, derived from its range."""

from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from metadata_automation.excel_prep.columns import VOCAB_COLUMN
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
from metadata_automation.shaclplay.vocab_mappings import find_vocab_mapping

URI = ("dash:URIViewer", "dash:URIEditor")
LABEL = ("dash:LabelViewer", "dash:URIEditor")
DETAILS = ("dash:DetailsViewer", "dash:BlankNodeEditor")
DATE_TIME = ("dash:LiteralViewer", "dash:DateTimePickerEditor")
TEXT_AREA = ("dash:LiteralViewer", "dash:TextAreaEditor")
TEXT_FIELD = ("dash:LiteralViewer", "dash:TextFieldEditor")

DESCRIPTION_PROPERTY = "dct:description"
GENERIC_RESOURCE = "rdfs:Resource"


def has_vocab(ws: Worksheet, row: int, col: int | None) -> bool:
    """True when the controlled vocabulary cell (text or hyperlink) resolves to a known vocabulary mapping."""
    if col is None:
        return False
    cell = ws.cell(row=row, column=col)
    hyperlink = cell.hyperlink.target if cell.hyperlink else None
    return find_vocab_mapping(text(ws, row, col), hyperlink) is not None


def expected_dash(
    range_: str, node: str, is_description: bool, model_classes: set[str], vocab: bool = False
) -> tuple[str, str] | None:
    """Return ``(viewer, editor)`` for a prepared range, or None when no rule applies.

    Rules, in order: a range ending in (IRI) is a URI, shown by its label when it is
    an outside class (not a model class or rdfs:Resource) with a known controlled vocabulary; a range with a
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
        if VOCAB_COLUMN not in cols:
            report.issue(name, None, VOCAB_COLUMN, "column missing; IRI ranges get dash:URIViewer")
        for row in property_rows(ws, cols):
            is_description = same_term(text(ws, row, cols.get("Property URI")), DESCRIPTION_PROPERTY, namespaces)
            expected = expected_dash(
                text(ws, row, cols.get("Range")),
                text(ws, row, cols["SHACL_sh:node"]),
                is_description,
                model_classes,
                has_vocab(ws, row, cols.get(VOCAB_COLUMN)),
            )
            if expected is None:
                continue
            for column, value in zip(("SHACL_dash:viewer", "SHACL_dash:editor"), expected, strict=True):
                current = text(ws, row, cols[column])
                if not current:
                    set_value(ws, row, cols[column], value, report, column, "derived from range")
                elif current != value:
                    report.issue(name, row, column, f"expected '{value}', found '{current}'")
