"""Prepare a class sheet: add the pipeline columns and apply the range rules (sh:node, (IRI), cardinality)."""

import re

from openpyxl.worksheet.worksheet import Worksheet

from metadata_automation.excel_prep.columns import CLASS_SHEET_COLUMNS
from metadata_automation.excel_prep.dash import URI
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

_CARDINALITY = re.compile(r"^(\d+)(?:\.\.(\d+|n|\*))?$")


def prepare_class_sheet(ws: Worksheet, model: dict[str, ModelClass] | None, init: bool, report: Report) -> None:
    """Add pipeline columns and, when ``model`` is given, apply the range rules (FDP ones unless ``init``)."""
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
            _apply_range(ws, row, cols, value, model, init, report)


def _apply_range(
    ws: Worksheet,
    row: int,
    cols: dict[str, int],
    value: str,
    model: dict[str, ModelClass],
    init: bool,
    report: Report,
) -> None:
    """Init only nests model classes; the full run applies the FDP rules. Other non-literal ranges get (IRI)."""
    base, has_iri = split_iri_suffix(value)
    if base in model and init:
        if not has_iri:
            _set_node(ws, row, cols, model[base], report, "class of this model")
    elif base in model:
        _apply_model_range(ws, row, cols, base, has_iri, model[base], report)
    elif not has_iri and curie_prefix(base) and not is_literal(base):
        set_value(ws, row, cols["Range"], f"{base} (IRI)", report, "Range", "range is not a class of this model")


def _apply_model_range(
    ws: Worksheet,
    row: int,
    cols: dict[str, int],
    base: str,
    has_iri: bool,
    cls: ModelClass,
    report: Report,
) -> None:
    """Independent classes are referenced by IRI with optional cardinality and URI DASH; dependent ones are nested.

    A class without a valid SHACL_independent_class flag is treated as dependent.
    """
    if cls.independent:
        reason = f"'{cls.sheet}' is an independent class"
        if not has_iri:
            set_value(ws, row, cols["Range"], f"{base} (IRI)", report, "Range", reason)
        _relax_cardinality(ws, row, cols, cls, report)
        _reference_by_iri(ws, row, cols, report, reason)
        return
    if has_iri:
        report.issue(ws.title, row, "Range", f"'{cls.sheet}' is a dependent class but the range ends in (IRI)")
    else:
        _set_node(ws, row, cols, cls, report, "dependent class")


def _set_node(ws: Worksheet, row: int, cols: dict[str, int], cls: ModelClass, report: Report, reason: str) -> None:
    """Set SHACL_sh:node to the class shape, overwriting a value that differs."""
    expected = f"{cls.class_uri}Shape"
    if cls.class_uri and text(ws, row, cols["SHACL_sh:node"]) != expected:
        set_value(ws, row, cols["SHACL_sh:node"], expected, report, "SHACL_sh:node", reason)


def _reference_by_iri(ws: Worksheet, row: int, cols: dict[str, int], report: Report, reason: str) -> None:
    """Empty SHACL_sh:node and overwrite the DASH values with the URI viewer and editor."""
    if old := text(ws, row, cols["SHACL_sh:node"]):
        ws.cell(row=row, column=cols["SHACL_sh:node"]).value = None
        report.change(ws.title, row, "SHACL_sh:node", f"cleared '{old}' ({reason})")
    for column, value in zip(("SHACL_dash:viewer", "SHACL_dash:editor"), URI, strict=True):
        if text(ws, row, cols[column]) != value:
            set_value(ws, row, cols[column], value, report, column, reason)


def _relax_cardinality(ws: Worksheet, row: int, cols: dict[str, int], cls: ModelClass, report: Report) -> None:
    if "Cardinality" not in cols:
        return
    current = text(ws, row, cols["Cardinality"])
    relaxed = relax_cardinality(current)
    if relaxed is None:
        report.issue(ws.title, row, "Cardinality", f"cannot parse {current!r}")
    elif relaxed != current:
        reason = f"'{cls.sheet}' is an independent class"
        set_value(ws, row, cols["Cardinality"], relaxed, report, "Cardinality", reason)


def relax_cardinality(cardinality: str) -> str | None:
    """Lower the minimum to 0: ``"1..n"`` -> ``"0..n"``, ``"1"`` -> ``"0..1"``. None when unparsable."""
    match = _CARDINALITY.match(cardinality.strip())
    if not match:
        return None
    low, high = match.group(1), match.group(2)
    if int(low) == 0:
        return cardinality
    return f"0..{high or low}"
