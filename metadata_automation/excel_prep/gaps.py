"""Finish the report: name the property of each finding and list the cells left empty."""

from dataclasses import replace

from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from metadata_automation.excel_prep.columns import (
    OPTIONAL_CLASSES_COLUMNS,
    OPTIONAL_PROPERTY_COLUMNS,
    REQUIRED_CLASSES_COLUMNS,
    REQUIRED_PROPERTY_COLUMNS,
)
from metadata_automation.excel_prep.report import Cell, Finding, Report
from metadata_automation.excel_prep.workbook import (
    class_sheet_names,
    data_rows,
    headers,
    property_rows,
    property_uri,
    text,
)


def add_property_uris(wb: Workbook, report: Report) -> None:
    """Name the property of each class sheet row in the changes and issues."""

    def annotate(findings: list[Finding]) -> list[Finding]:
        return [replace(f, property_uri=property_uri(wb, f.cell.sheet, f.cell.row)) for f in findings]

    report.changes = annotate(report.changes)
    report.issues = annotate(report.issues)
    report.prefix_issues = annotate(report.prefix_issues)


def collect_gaps(wb: Workbook, report: Report) -> None:
    """List the empty required and optional cells."""
    ws = wb["classes"]
    cols = headers(ws)
    for row in data_rows(ws, cols, ("sheet_name",)):
        _gaps(ws, row, cols, REQUIRED_CLASSES_COLUMNS, report.gaps)
        _gaps(ws, row, cols, OPTIONAL_CLASSES_COLUMNS, report.optional_gaps)

    for name in class_sheet_names(wb):
        ws = wb[name]
        cols = headers(ws)
        for row in property_rows(ws, cols):
            _gaps(ws, row, cols, REQUIRED_PROPERTY_COLUMNS, report.gaps)
            _gaps(ws, row, cols, OPTIONAL_PROPERTY_COLUMNS, report.optional_gaps)

    ws = wb["prefixes"]
    cols = headers(ws)
    for row in data_rows(ws, cols, ("prefix",)):
        _gaps(ws, row, cols, ["namespace"], report.gaps)


def _gaps(ws: Worksheet, row: int, cols: dict[str, int], columns: list[str], into: list[Cell]) -> None:
    into.extend(Cell(ws.title, row, c) for c in columns if not text(ws, row, cols.get(c)))
