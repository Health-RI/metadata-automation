"""Add the general sheets, columns and rows, and read the model classes."""

from dataclasses import dataclass

from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from metadata_automation.excel_prep.columns import CLASSES_COLUMNS, PREFIXES_COLUMNS, SHEET_COLUMNS
from metadata_automation.excel_prep.prefix_check import used_prefixes
from metadata_automation.excel_prep.report import Report
from metadata_automation.excel_prep.workbook import (
    NON_CLASS_SHEETS,
    class_sheet_names,
    curie_prefix,
    data_rows,
    ensure_columns,
    parse_bool,
    text,
)


@dataclass
class ModelClass:
    """A class of this metadata model, as configured in the 'classes' sheet."""

    sheet: str
    class_uri: str
    independent: bool | None


def add_general_sheets(wb: Workbook, names: list[str], report: Report) -> None:
    """Create the missing ``names`` sheets after Info / User Guide."""
    index = max((wb.sheetnames.index(n) + 1 for n in ("Info", "User Guide") if n in wb.sheetnames), default=0)
    for name in names:
        if name in wb.sheetnames:
            index = wb.sheetnames.index(name) + 1
            continue
        ws = wb.create_sheet(name, index)
        for col, header in enumerate(SHEET_COLUMNS[name], start=1):
            ws.cell(row=1, column=col, value=header)
        report.change(name, None, None, "added sheet")
        index += 1


def prepare_classes_sheet(
    wb: Workbook, namespace: str | None, report: Report
) -> tuple[dict[str, ModelClass], list[str]]:
    """Add missing columns and rows, and derive class_URI when ``namespace`` is given.

    Returns the model classes and the class sheets with an empty SHACL_target_ontology_name.
    """
    ws = wb["classes"]
    cols, added = ensure_columns(ws, CLASSES_COLUMNS, report)
    if added:
        report.change("classes", None, None, f"added columns {', '.join(added)}")

    sheets = class_sheet_names(wb)
    rows = _class_rows(ws, cols, sheets, report)

    model: dict[str, ModelClass] = {}
    untargeted = []
    for name in sheets:
        row = rows[name]
        target = text(ws, row, cols["SHACL_target_ontology_name"])
        class_uri = text(ws, row, cols["class_URI"])
        if namespace and not class_uri and curie_prefix(target):
            class_uri = f"{namespace}:{target.split(':', 1)[1]}"
            ws.cell(row=row, column=cols["class_URI"], value=class_uri)
            report.change("classes", row, "class_URI", f"set to '{class_uri}'")

        raw_independent = ws.cell(row=row, column=cols["SHACL_independent_class"]).value
        independent = parse_bool(raw_independent)
        if independent is None and text(ws, row, cols["SHACL_independent_class"]):
            report.issue("classes", row, "SHACL_independent_class", f"expected TRUE or FALSE, got {raw_independent!r}")

        if not target:
            untargeted.append(name)
            continue
        if target in model:
            report.issue(
                "classes", row, "SHACL_target_ontology_name", f"'{target}' also used by '{model[target].sheet}'"
            )
            continue
        model[target] = ModelClass(name, class_uri, independent)
    return model, untargeted


def _class_rows(ws: Worksheet, cols: dict[str, int], sheets: list[str], report: Report) -> dict[str, int]:
    """Map class sheets to their 'classes' row, adding rows for missing sheets."""
    rows = {text(ws, r, cols["sheet_name"]): r for r in data_rows(ws, cols, ("sheet_name",))}
    for name, row in rows.items():
        if name not in sheets:
            reason = "is not a class sheet" if name in NON_CLASS_SHEETS else "does not exist"
            report.issue("classes", row, "sheet_name", f"sheet '{name}' {reason}")

    next_row = max(rows.values(), default=1) + 1
    for name in sheets:
        if name not in rows:
            ws.cell(row=next_row, column=cols["sheet_name"], value=name)
            rows[name] = next_row
            report.change("classes", next_row, "sheet_name", f"added row for sheet '{name}'")
            next_row += 1
    return rows


def prepare_prefixes_sheet(wb: Workbook, report: Report) -> None:
    """Add a row, without namespace, for every used prefix that is not registered."""
    ws = wb["prefixes"]
    cols, added = ensure_columns(ws, PREFIXES_COLUMNS, report)
    if added:
        report.change("prefixes", None, None, f"added columns {', '.join(added)}")
    rows = data_rows(ws, cols, ("prefix",))
    registered = {text(ws, r, cols["prefix"]) for r in rows}
    next_row = max(rows, default=1) + 1
    for prefix in sorted(used_prefixes(wb)):
        if prefix not in registered:
            ws.cell(row=next_row, column=cols["prefix"], value=prefix)
            report.change("prefixes", next_row, "prefix", f"added '{prefix}' (namespace unknown)")
            next_row += 1
