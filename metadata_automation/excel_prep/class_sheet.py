"""Prepare a class sheet: add the pipeline columns and apply the general range rules (sh:node, (IRI))."""

from openpyxl.worksheet.worksheet import Worksheet

from metadata_automation.excel_prep.columns import CLASS_SHEET_COLUMNS
from metadata_automation.excel_prep.report import Report
from metadata_automation.excel_prep.structure import ModelClass
from metadata_automation.excel_prep.workbook import (
    copy_column_format,
    curie_prefix,
    ensure_columns,
    is_literal,
    property_rows,
    set_value,
    split_iri_suffix,
    text,
)


def prepare_class_sheet(ws: Worksheet, model: dict[str, ModelClass] | None, report: Report) -> None:
    """Add pipeline columns and, when ``model`` is given, apply the range rules."""
    cols, added = ensure_columns(ws, CLASS_SHEET_COLUMNS, report)
    if added:
        for name in added:
            copy_column_format(ws, 1, cols[name])
        report.change(ws.title, None, None, f"added columns {', '.join(added)}")
    if model is None:
        return
    if "Range" not in cols:
        report.issue(ws.title, None, "Range", "column missing")
        return

    for row in property_rows(ws, cols):
        if value := text(ws, row, cols["Range"]):
            _apply_range(ws, row, cols, value, model, report)


def _apply_range(
    ws: Worksheet, row: int, cols: dict[str, int], value: str, model: dict[str, ModelClass], report: Report
) -> None:
    """Model classes are nested through SHACL_sh:node; other non-literal CURIE ranges get (IRI).

    Values without a prefix and full IRIs are left to the prefix check.
    """
    base, has_iri = split_iri_suffix(value)
    if base in model:
        if not has_iri:
            set_node(ws, row, cols, model[base], report, "class of this model")
    elif not has_iri and curie_prefix(base) and not is_literal(base):
        set_value(ws, row, cols["Range"], f"{base} (IRI)", report, "Range", "range is not a class of this model")


def set_node(ws: Worksheet, row: int, cols: dict[str, int], cls: ModelClass, report: Report, reason: str) -> None:
    """Set SHACL_sh:node to the class shape, overwriting a value that differs."""
    expected = f"{cls.class_uri}Shape"
    if cls.class_uri and text(ws, row, cols["SHACL_sh:node"]) != expected:
        set_value(ws, row, cols["SHACL_sh:node"], expected, report, "SHACL_sh:node", reason)
