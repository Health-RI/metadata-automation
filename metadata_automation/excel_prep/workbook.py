"""Workbook helpers shared by the preparer and the prefix check."""

import re
from copy import copy

from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

NON_CLASS_SHEETS = ("Info", "User Guide", "prefixes", "classes")
IRI_SUFFIX = "(IRI)"

_CURIE = re.compile(r"^([A-Za-z_][\w.-]*):(?!//)(\S*)$")


def class_sheet_names(wb: Workbook) -> list[str]:
    """Every sheet except the general ones is a class sheet."""
    return [name for name in wb.sheetnames if name not in NON_CLASS_SHEETS]


def headers(ws: Worksheet) -> dict[str, int]:
    """Map stripped header names to 1-based column indices."""
    return {str(c.value).strip(): c.column for c in ws[1] if not is_empty(c.value)}


def ensure_columns(ws: Worksheet, columns: list[str]) -> tuple[dict[str, int], list[str]]:
    """Append missing columns after the last header. Returns the headers and the added names."""
    cols = headers(ws)
    added = []
    for name in columns:
        if name not in cols:
            col = max(cols.values(), default=0) + 1
            ws.cell(row=1, column=col, value=name)
            cols[name] = col
            added.append(name)
    return cols, added


def copy_column_format(ws: Worksheet, src_col: int, dst_col: int) -> None:
    """Copy cell styles and width of ``src_col`` onto ``dst_col``, header row included."""
    for row in range(1, ws.max_row + 1):
        src = ws.cell(row=row, column=src_col)
        if src.has_style:
            ws.cell(row=row, column=dst_col)._style = copy(src._style)
    src_dim = ws.column_dimensions[get_column_letter(src_col)]
    if src_dim.width:
        ws.column_dimensions[get_column_letter(dst_col)].width = src_dim.width


def is_empty(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def text(ws: Worksheet, row: int, col: int | None) -> str:
    """Cell value as a stripped string, empty when missing."""
    if col is None:
        return ""
    value = ws.cell(row=row, column=col).value
    return "" if is_empty(value) else str(value).strip()


def data_rows(ws: Worksheet, cols: dict[str, int], keys: tuple[str, ...]) -> list[int]:
    """Row numbers below the header where any of the ``keys`` columns has a value."""
    key_cols = [cols[k] for k in keys if k in cols]
    return [r for r in range(2, ws.max_row + 1) if any(text(ws, r, c) for c in key_cols)]


def property_rows(ws: Worksheet, cols: dict[str, int]) -> list[int]:
    return data_rows(ws, cols, ("Property label", "Property URI"))


def split_iri_suffix(value: str) -> tuple[str, bool]:
    """Split ``"dct:Standard (IRI)"`` into ``("dct:Standard", True)``."""
    value = value.strip()
    if value.endswith(IRI_SUFFIX):
        return value[: -len(IRI_SUFFIX)].strip(), True
    return value, False


def curie_prefix(value: str) -> str | None:
    """Prefix of a CURIE, or None for full IRIs and values without a prefix."""
    match = _CURIE.match(value.strip())
    return match.group(1) if match else None


def parse_bool(value) -> bool | None:
    """Excel booleans and their text forms; None when empty or unrecognised."""
    if isinstance(value, bool):
        return value
    if is_empty(value):
        return None
    lowered = str(value).strip().lower()
    if lowered in ("true", "1", "yes"):
        return True
    if lowered in ("false", "0", "no"):
        return False
    return None
