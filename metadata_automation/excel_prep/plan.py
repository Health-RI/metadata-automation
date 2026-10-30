"""Plan the technical columns of a metadata Excel without touching the source.

The preparation runs on an in-memory copy; the plan is the difference between that copy and the source, plus the
required cells that cannot be computed. Rows are identified by sheet and key (the property URI, or the sheet name in
``classes`` and the prefix in ``prefixes``), never by row number, so a plan survives rows being inserted or sorted.

Plan workbook:

- ``Summary``: source name and hash, tool version, counts. ``apply-plan`` refuses a plan made from another source.
- ``Edits``: one row per change, with ``Apply`` (default yes) and the proposed value, both editable.
- ``Gaps``: required cells that cannot be computed, with an empty ``Value to apply`` to fill in.
- ``Issues``: findings that need a decision. Informational.
"""

import fnmatch
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from metadata_automation.excel_prep.preparer import prepare_in_memory
from metadata_automation.excel_prep.report import Cell, Report
from metadata_automation.excel_prep.workbook import headers, text

ADD_SHEET = "add sheet"
RENAME_SHEET = "rename sheet"
ADD_COLUMN = "add column"
ADD_ROW = "add row"
SET_CELL = "set cell"
KIND_ORDER = [RENAME_SHEET, ADD_SHEET, ADD_COLUMN, ADD_ROW, SET_CELL]

# Sheets whose rows are added by the preparation, keyed by this column.
ADDED_ROW_KEYS = {"classes": "sheet_name", "prefixes": "prefix"}

SUMMARY = "Summary"
EDITS = "Edits"
GAPS = "Gaps"
ISSUES = "Issues"
EDIT_COLUMNS = [
    "Apply",
    "Kind",
    "Sheet",
    "Key",
    "Occurrence",
    "Column",
    "Current value",
    "Proposed value",
    "Reason",
    "Row",
]
GAP_COLUMNS = ["Sheet", "Key", "Occurrence", "Column", "Value to apply", "Row"]
ISSUE_COLUMNS = ["Sheet", "Key", "Column", "Message"]


@dataclass(frozen=True)
class Edit:
    """One change to the source. ``old`` and ``new`` are only used by ``set cell``; ``old`` is the expected value."""

    kind: str
    sheet: str
    key: str = ""
    occurrence: int = 1
    column: str = ""
    old: str = ""
    new: str = ""
    reason: str = ""
    row: int | None = None
    apply: bool = True


@dataclass(frozen=True)
class Gap:
    """A required cell that cannot be computed. ``value`` is typed by the technical team."""

    sheet: str
    key: str
    occurrence: int
    column: str
    value: str = ""
    row: int | None = None


@dataclass(frozen=True)
class IssueRow:
    sheet: str
    key: str
    column: str
    message: str


@dataclass
class Plan:
    """What has to change in the source, and what has to be filled in by hand."""

    source_name: str
    source_hash: str
    tool_version: str
    namespace: str = ""
    ignored_columns: str = ""
    ignored_gaps: int = 0
    edits: list[Edit] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    issues: list[IssueRow] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """True when the source needs no edit and no required cell is empty."""
        return not self.edits and not self.gaps


def source_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tool_version() -> str:
    try:
        return version("metadata-automation")
    except PackageNotFoundError:
        return "unknown"


def row_key(ws, row: int, cols: dict[str, int]) -> str:
    """Identify a row by content: sheet name, prefix, property URI or label; the row number as a last resort."""
    for column, prefix in (("sheet_name", ""), ("prefix", ""), ("Property URI", ""), ("Property label", "label: ")):
        if column in cols and (value := text(ws, row, cols[column])):
            return prefix + value
    return f"row {row}"


def occurrences(ws, cols: dict[str, int]) -> dict[int, int]:
    """For each row, how often its key occurred up to and including that row (1-based)."""
    seen: dict[str, int] = {}
    result = {}
    for row in range(2, ws.max_row + 1):
        key = row_key(ws, row, cols)
        seen[key] = seen.get(key, 0) + 1
        result[row] = seen[key]
    return result


def compute_plan(src: Path, namespace: str | None = None, ignore_gaps: Sequence[str] = ()) -> tuple[Plan, Report]:
    """Plan ``src`` without modifying it. Also returns the preparation report.

    Required cells in columns matching one of the ``ignore_gaps`` patterns (e.g. ``SeMPyRO_*``) are not listed as gaps,
    for instance because the artifact that needs them is not generated yet. They are counted in the plan.
    """
    src = Path(src)
    original = load_workbook(src, rich_text=True)
    prepared = load_workbook(src, rich_text=True)
    report = Report()
    prepare_in_memory(prepared, namespace, report)

    plan = Plan(src.name, source_hash(src), tool_version(), namespace or "")
    plan.edits = _edits(original, prepared, report)
    gaps = _gaps(prepared, report)
    plan.gaps = [g for g in gaps if not _ignored(g.column, ignore_gaps)]
    plan.ignored_gaps = len(gaps) - len(plan.gaps)
    plan.ignored_columns = ", ".join(ignore_gaps)
    plan.issues = _issues(prepared, report)
    return plan, report


def _ignored(column: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(column, pattern) for pattern in patterns)


def _reason(message: str) -> str:
    """``"'a' -> 'b' (why)"`` -> ``"why"``; other messages are kept."""
    if message.endswith(")") and " (" in message:
        return message[message.rindex(" (") + 2 : -1]
    return message


def _reasons(report: Report) -> dict[tuple[str, int | None, str | None], str]:
    return {(f.cell.sheet, f.cell.row, f.cell.column): _reason(f.message) for f in report.changes}


def _sheet_pairs(original: Workbook, prepared: Workbook) -> list[tuple[str, str | None]]:
    """Each prepared sheet with the name it had in the source, None when it is new."""
    pairs = []
    for name in prepared.sheetnames:
        if name in original.sheetnames:
            pairs.append((name, name))
            continue
        old = next((t for t in original.sheetnames if t.lower() == name.lower() and t not in prepared.sheetnames), None)
        pairs.append((name, old))
    return pairs


def _edits(original: Workbook, prepared: Workbook, report: Report) -> list[Edit]:
    reasons = _reasons(report)
    edits: list[Edit] = []
    for name, old_name in _sheet_pairs(original, prepared):
        ws_new = prepared[name]
        ws_old = original[old_name] if old_name else None
        if old_name is None:
            edits.append(Edit(ADD_SHEET, name, reason=reasons.get((name, None, None), "required sheet")))
        elif old_name != name:
            edits.append(Edit(RENAME_SHEET, name, old=old_name, new=name, reason=f"renamed from '{old_name}'"))
        edits += _sheet_edits(name, ws_old, ws_new, reasons)
    return sorted(edits, key=lambda e: KIND_ORDER.index(e.kind))


def _sheet_edits(name: str, ws_old, ws_new, reasons: dict) -> list[Edit]:
    edits: list[Edit] = []
    cols_new = headers(ws_new)
    cols_old = headers(ws_old) if ws_old is not None else {}
    for column in cols_new:
        if column not in cols_old:
            edits.append(Edit(ADD_COLUMN, name, column=column, reason="pipeline column"))

    key_column = ADDED_ROW_KEYS.get(name)
    old_rows = {row_key(ws_old, r, cols_old): r for r in range(2, ws_old.max_row + 1)} if ws_old is not None else {}
    occ = occurrences(ws_new, cols_new)
    for row in range(2, ws_new.max_row + 1):
        key = row_key(ws_new, row, cols_new)
        added = bool(key_column) and key_column in cols_new and key not in old_rows
        if added:
            if not text(ws_new, row, cols_new[key_column]):
                continue
            edits.append(
                Edit(
                    ADD_ROW,
                    name,
                    key,
                    1,
                    key_column,
                    new=text(ws_new, row, cols_new[key_column]),
                    reason=reasons.get((name, row, key_column), "added row"),
                    row=row,
                )
            )
        for column, col in cols_new.items():
            if added and column == key_column:
                continue
            new = text(ws_new, row, col)
            old = "" if added or column not in cols_old else text(ws_old, row, cols_old[column])
            if new != old:
                reason = reasons.get((name, row, column), "computed value")
                edits.append(Edit(SET_CELL, name, key, occ[row], column, old, new, reason, row))
    return edits


def _gaps(prepared: Workbook, report: Report) -> list[Gap]:
    gaps = []
    for gap in report.gaps:
        ws = prepared[gap.sheet]
        cols = headers(ws)
        gaps.append(Gap(gap.sheet, row_key(ws, gap.row, cols), occurrences(ws, cols)[gap.row], gap.column, row=gap.row))
    return gaps


def _issues(prepared: Workbook, report: Report) -> list[IssueRow]:
    rows = []
    for finding in [*report.issues, *report.prefix_issues]:
        cell: Cell = finding.cell
        key = ""
        if cell.row and cell.sheet in prepared.sheetnames:
            ws = prepared[cell.sheet]
            key = row_key(ws, cell.row, headers(ws))
        rows.append(IssueRow(cell.sheet, key, cell.column or "", finding.message))
    return rows


def write_plan(plan: Plan, path: Path, overwrite: bool = False) -> None:
    """Write the plan workbook. An existing plan is only replaced with ``overwrite``, as it may have been edited."""
    path = Path(path)
    if path.exists() and not overwrite:
        raise ValueError(f"Plan {path} already exists; it may hold edits. Pass --overwrite to replace it.")
    wb = Workbook()
    summary = wb.active
    summary.title = SUMMARY
    for label, value in [
        ("Source file", plan.source_name),
        ("Source SHA-256", plan.source_hash),
        ("Tool", f"metadata-automation {plan.tool_version}"),
        ("Namespace", plan.namespace),
        ("Edits", len(plan.edits)),
        ("Required gaps", len(plan.gaps)),
        ("Ignored gap columns", plan.ignored_columns),
        ("Ignored gaps", plan.ignored_gaps),
        ("Issues", len(plan.issues)),
    ]:
        summary.append([label, value])
    summary.append([])
    summary.append(
        ["Set Apply to no to skip an edit, or change a proposed value. Fill Value to apply on the Gaps sheet."]
    )

    _sheet(wb, EDITS, EDIT_COLUMNS, [_edit_row(e) for e in plan.edits])
    _sheet(wb, GAPS, GAP_COLUMNS, [[g.sheet, g.key, g.occurrence, g.column, g.value or None, g.row] for g in plan.gaps])
    _sheet(wb, ISSUES, ISSUE_COLUMNS, [[i.sheet, i.key, i.column, i.message] for i in plan.issues])
    for ws in wb.worksheets:
        for col in range(1, ws.max_column + 1):
            width = max((len(str(c.value)) for c in ws[get_column_letter(col)] if c.value is not None), default=8)
            ws.column_dimensions[get_column_letter(col)].width = min(max(width + 2, 10), 60)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def _edit_row(e: Edit) -> list:
    return ["yes" if e.apply else "no", e.kind, e.sheet, e.key, e.occurrence, e.column, e.old, e.new, e.reason, e.row]


def _sheet(wb: Workbook, title: str, columns: list[str], rows: list[list]) -> None:
    ws = wb.create_sheet(title)
    ws.append(columns)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    for row in rows:
        ws.append(row)


def read_plan(path: Path) -> Plan:
    """Read a plan workbook, including the edits and values a person changed."""
    wb = load_workbook(Path(path))
    for name in (SUMMARY, EDITS, GAPS, ISSUES):
        if name not in wb.sheetnames:
            raise ValueError(f"{path} is not a plan: sheet '{name}' is missing.")
    summary = {str(r[0].value): r[1].value for r in wb[SUMMARY].iter_rows(min_row=1, max_row=9) if r[0].value}
    tool = str(summary.get("Tool", "")).removeprefix("metadata-automation ")
    plan = Plan(
        str(summary.get("Source file", "")),
        str(summary.get("Source SHA-256", "")),
        tool,
        str(summary.get("Namespace") or ""),
        str(summary.get("Ignored gap columns") or ""),
        int(summary.get("Ignored gaps") or 0),
    )
    for row in _rows(wb[EDITS], EDIT_COLUMNS):
        plan.edits.append(
            Edit(
                kind=row["Kind"],
                sheet=row["Sheet"],
                key=row["Key"],
                occurrence=int(row["Occurrence"] or 1),
                column=row["Column"],
                old=row["Current value"],
                new=row["Proposed value"],
                reason=row["Reason"],
                row=row["Row"] or None,
                apply=str(row["Apply"]).strip().lower() in ("yes", "y", "true", "1"),
            )
        )
    for row in _rows(wb[GAPS], GAP_COLUMNS):
        plan.gaps.append(
            Gap(
                row["Sheet"],
                row["Key"],
                int(row["Occurrence"] or 1),
                row["Column"],
                row["Value to apply"],
                row["Row"] or None,
            )
        )
    for row in _rows(wb[ISSUES], ISSUE_COLUMNS):
        plan.issues.append(IssueRow(row["Sheet"], row["Key"], row["Column"], row["Message"]))
    return plan


def _rows(ws, columns: list[str]) -> list[dict[str, str]]:
    """Rows of a plan sheet as dicts of stripped strings; numbers stay numbers."""
    cols = headers(ws)
    missing = [c for c in columns if c not in cols]
    if missing:
        raise ValueError(f"Sheet '{ws.title}' of the plan lacks the columns {', '.join(missing)}.")
    rows = []
    for r in range(2, ws.max_row + 1):
        values = {c: ws.cell(row=r, column=cols[c]).value for c in columns}
        if all(v in (None, "") for v in values.values()):
            continue
        rows.append(
            {
                c: ("" if v is None else (v if isinstance(v, int) and not isinstance(v, bool) else str(v).strip()))
                for c, v in values.items()
            }
        )
    return rows


def default_plan_path(src: Path) -> Path:
    """The plan lives next to the source as ``{name}-plan.xlsx``."""
    src = Path(src)
    return src.with_name(f"{src.stem}-plan.xlsx")
