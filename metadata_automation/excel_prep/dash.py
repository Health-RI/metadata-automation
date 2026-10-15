"""DASH viewer and editor for each property, derived from its range."""

from openpyxl.workbook import Workbook

from metadata_automation.excel_prep.prefix_check import expand, namespace_map
from metadata_automation.excel_prep.report import Report
from metadata_automation.excel_prep.workbook import (
    IRI_SUFFIX,
    class_sheet_names,
    headers,
    property_rows,
    set_value,
    text,
)

URI = ("dash:URIViewer", "dash:URIEditor")
DETAILS = ("dash:DetailsViewer", "dash:BlankNodeEditor")
DATE_TIME = ("dash:LiteralViewer", "dash:DateTimePickerEditor")
TEXT_AREA = ("dash:LiteralViewer", "dash:TextAreaEditor")
TEXT_FIELD = ("dash:LiteralViewer", "dash:TextFieldEditor")

DESCRIPTION_PROPERTY = "dct:description"


def expected_dash(range_: str, node: str, is_description: bool) -> tuple[str, str] | None:
    """Return ``(viewer, editor)`` for a prepared range, or None when no rule applies.

    Rules, in order: a range ending in (IRI) is a URI; a range with a node shape
    links to another class of the model; xsd:dateTime gets a date picker;
    dct:description gets a text area; any other literal gets a text field.
    """
    range_ = range_.strip()
    if range_.endswith(IRI_SUFFIX):
        return URI
    if node:
        return DETAILS
    if range_ == "xsd:dateTime":
        return DATE_TIME
    if range_.startswith(("xsd:", "rdfs:Literal")):
        return TEXT_AREA if is_description else TEXT_FIELD
    return None


def apply_dash_rules(wb: Workbook, report: Report) -> None:
    """Fill empty viewer/editor cells with the expected value; report existing values that differ."""
    namespaces = namespace_map(wb)
    description_iri = expand(DESCRIPTION_PROPERTY, namespaces)
    for name in class_sheet_names(wb):
        ws = wb[name]
        cols = headers(ws)
        for row in property_rows(ws, cols):
            uri = text(ws, row, cols.get("Property URI"))
            is_description = uri == DESCRIPTION_PROPERTY or bool(
                description_iri and expand(uri, namespaces) == description_iri
            )
            expected = expected_dash(
                text(ws, row, cols.get("Range")), text(ws, row, cols["SHACL_sh:node"]), is_description
            )
            if expected is None:
                continue
            for column, value in zip(("SHACL_dash:viewer", "SHACL_dash:editor"), expected, strict=True):
                current = text(ws, row, cols[column])
                if not current:
                    set_value(ws, row, cols[column], value, report, column, "derived from range")
                elif current != value:
                    report.issue(name, row, column, f"expected '{value}', found '{current}'")
