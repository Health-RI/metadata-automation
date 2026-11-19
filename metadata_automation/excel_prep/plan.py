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

import hashlib
import re
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
_KIND_ORDER = [RENAME_SHEET, ADD_SHEET, ADD_COLUMN, ADD_ROW, SET_CELL]

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
    edits: list[Edit] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    issues: list[IssueRow] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """True when the source needs no edit and no required cell is empty.

        Issues do not count: many only confirm how an answer was read, so a correct source always has some.
        """
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


def compute_plan(src: Path, namespace: str | None = None) -> tuple[Plan, Report]:
    """Plan ``src`` without modifying it. Also returns the preparation report."""
    src = Path(src)
    original = load_workbook(src, rich_text=True)
    prepared = load_workbook(src, rich_text=True)
    report = Report()
    prepare_in_memory(prepared, namespace, report)

    pairs = _sheet_pairs(original, prepared)
    keys = {name: _sheet_keys(name, original[old] if old else None, prepared[name]) for name, old in pairs}
    plan = Plan(src.name, source_hash(src), tool_version(), namespace or "")
    plan.edits = _edits(original, prepared, report, pairs, keys)
    plan.gaps = _gaps(report, keys)
    plan.issues = _issues(report, keys)
    return plan, report


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


@dataclass(frozen=True)
class _SheetKeys:
    """Key and occurrence of each row of a prepared sheet, as the source names it."""

    rows: dict[int, tuple[str, int]]
    added: frozenset[int]


def _sheet_keys(name: str, ws_old, ws_new) -> _SheetKeys:
    """Existing rows are keyed by their source content, so a value the preparation changes cannot change the key.

    Rows the preparation added do not exist in the source and are keyed by their prepared content.
    """
    cols_new = headers(ws_new)
    cols_old = headers(ws_old) if ws_old is not None else {}
    added = frozenset(_added_rows(name, ws_old, ws_new, cols_old, cols_new))
    occ_new = occurrences(ws_new, cols_new)
    occ_old = occurrences(ws_old, cols_old) if ws_old is not None else {}
    rows = {}
    for row in range(2, ws_new.max_row + 1):
        if row in added or row not in occ_old:
            rows[row] = (row_key(ws_new, row, cols_new), occ_new[row])
        else:
            rows[row] = (row_key(ws_old, row, cols_old), occ_old[row])
    return _SheetKeys(rows, added)


def _added_rows(name: str, ws_old, ws_new, cols_old: dict[str, int], cols_new: dict[str, int]) -> set[int]:
    """Rows whose key cell the preparation filled: empty or absent in the source, filled in the prepared copy."""
    key_column = ADDED_ROW_KEYS.get(name)
    if key_column not in cols_new:
        return set()
    old_col = cols_old.get(key_column)
    old_rows = ws_old.max_row if ws_old is not None else 0
    return {
        row
        for row in range(2, ws_new.max_row + 1)
        if text(ws_new, row, cols_new[key_column]) and not (row <= old_rows and text(ws_old, row, old_col))
    }


def _edits(
    original: Workbook,
    prepared: Workbook,
    report: Report,
    pairs: list[tuple[str, str | None]],
    keys: dict[str, _SheetKeys],
) -> list[Edit]:
    reasons = _reasons(report)
    edits: list[Edit] = []
    for name, old_name in pairs:
        ws_new = prepared[name]
        ws_old = original[old_name] if old_name else None
        if old_name is None:
            edits.append(Edit(ADD_SHEET, name, reason=reasons.get((name, None, None), "required sheet")))
        elif old_name != name:
            edits.append(Edit(RENAME_SHEET, name, old=old_name, new=name, reason=f"renamed from '{old_name}'"))
        edits += _sheet_edits(name, ws_old, ws_new, keys[name], reasons)
    return sorted(edits, key=lambda e: _KIND_ORDER.index(e.kind))


def _sheet_edits(name: str, ws_old, ws_new, keys: _SheetKeys, reasons: dict) -> list[Edit]:
    edits: list[Edit] = []
    cols_new = headers(ws_new)
    cols_old = headers(ws_old) if ws_old is not None else {}
    for column in cols_new:
        if column not in cols_old:
            edits.append(Edit(ADD_COLUMN, name, column=column, reason="pipeline column"))

    key_column = ADDED_ROW_KEYS.get(name)
    for row in range(2, ws_new.max_row + 1):
        key, occurrence = keys.rows[row]
        added = row in keys.added
        if added:
            edits.append(
                Edit(
                    ADD_ROW,
                    name,
                    key=key,
                    column=key_column,
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
                edits.append(Edit(SET_CELL, name, key, occurrence, column, old, new, reason, row))
    return edits


def _gaps(report: Report, keys: dict[str, _SheetKeys]) -> list[Gap]:
    gaps = []
    for gap in report.gaps:
        key, occurrence = keys[gap.sheet].rows[gap.row]
        gaps.append(Gap(gap.sheet, key, occurrence, gap.column, row=gap.row))
    return gaps


def _issues(report: Report, keys: dict[str, _SheetKeys]) -> list[IssueRow]:
    rows = []
    for finding in [*report.issues, *report.prefix_issues]:
        cell: Cell = finding.cell
        key = ""
        if cell.row and cell.sheet in keys:
            key = keys[cell.sheet].rows.get(cell.row, (f"row {cell.row}", 1))[0]
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
    """Read a plan workbook, including the edits and values a person changed.

    Every cell a person may have edited is validated; all problems are raised together, each with its sheet and row.
    """
    wb = load_workbook(Path(path))
    for name in (SUMMARY, EDITS, GAPS, ISSUES):
        if name not in wb.sheetnames:
            raise ValueError(f"{path} is not a plan: sheet '{name}' is missing.")
    errors = _Errors()
    summary = _read_summary(wb[SUMMARY], errors)
    edits = [_read_edit(row, values, errors) for row, values in _rows(wb[EDITS], EDIT_COLUMNS)]
    gaps = [_read_gap(row, values, errors) for row, values in _rows(wb[GAPS], GAP_COLUMNS)]
    issues = [
        IssueRow(*(_cell_text(values[c]) for c in ISSUE_COLUMNS)) for _, values in _rows(wb[ISSUES], ISSUE_COLUMNS)
    ]
    _check_unique(
        EDITS, [(r, (e.sheet, e.key, e.occurrence, e.column)) for r, e in edits if e.kind == SET_CELL], errors
    )
    _check_unique(GAPS, [(r, (g.sheet, g.key, g.occurrence, g.column)) for r, g in gaps], errors)
    if errors.messages:
        raise ValueError(f"{path} is not a valid plan:\n" + "\n".join(f"  - {m}" for m in errors.messages))
    plan = Plan(*summary)
    plan.edits = [e for _, e in edits]
    plan.gaps = [g for _, g in gaps]
    plan.issues = issues
    return plan


class _Errors:
    """Collects the problems of a plan, so a person can fix them all in one pass."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def check(self, where: str, column: str, parse, value, default=None):
        """``parse(value)``, or ``default`` with the problem recorded."""
        try:
            return parse(value)
        except ValueError as e:
            self.messages.append(f"{where}, {column}: {e}")
            return default


def _read_summary(ws, errors: _Errors) -> tuple[str, str, str, str]:
    """Source name, hash, tool version and namespace, found by label so the order of the rows does not matter."""
    summary = {_cell_text(r[0].value): r[1].value for r in ws.iter_rows(max_col=2) if r[0].value}
    source = _cell_text(summary.get("Source file"))
    digest = _cell_text(summary.get("Source SHA-256")).lower()
    if not source:
        errors.messages.append(f"{SUMMARY}: 'Source file' is missing.")
    if not _SHA256.fullmatch(digest):
        errors.messages.append(f"{SUMMARY}: 'Source SHA-256' must be 64 hexadecimal characters, got {digest!r}.")
    tool = _cell_text(summary.get("Tool")).removeprefix("metadata-automation ")
    return source, digest, tool, _cell_text(summary.get("Namespace"))


def _read_edit(row: int, values: dict, errors: _Errors) -> tuple[int, Edit]:
    where = f"{EDITS} row {row}"
    kind = errors.check(where, "Kind", _kind, values["Kind"], default=SET_CELL)
    edit = Edit(
        kind=kind,
        sheet=errors.check(where, "Sheet", _required, values["Sheet"], default=""),
        key=_cell_text(values["Key"]),
        occurrence=errors.check(where, "Occurrence", _occurrence, values["Occurrence"], default=1),
        column=_cell_text(values["Column"]),
        old=_cell_text(values["Current value"]),
        new=_cell_text(values["Proposed value"]),
        reason=_cell_text(values["Reason"]),
        row=errors.check(where, "Row", _row_number, values["Row"]),
        apply=errors.check(where, "Apply", _apply, values["Apply"], default=False),
    )
    if kind in _NEEDS_KEY and not edit.key:
        errors.messages.append(f"{where}, Key: required for '{kind}'.")
    if kind in _NEEDS_COLUMN and not edit.column:
        errors.messages.append(f"{where}, Column: required for '{kind}'.")
    return row, edit


def _read_gap(row: int, values: dict, errors: _Errors) -> tuple[int, Gap]:
    where = f"{GAPS} row {row}"
    gap = Gap(
        sheet=errors.check(where, "Sheet", _required, values["Sheet"], default=""),
        key=errors.check(where, "Key", _required, values["Key"], default=""),
        occurrence=errors.check(where, "Occurrence", _occurrence, values["Occurrence"], default=1),
        column=errors.check(where, "Column", _required, values["Column"], default=""),
        value=_cell_text(values["Value to apply"]),
        row=errors.check(where, "Row", _row_number, values["Row"]),
    )
    return row, gap


def _check_unique(sheet: str, entries: list[tuple[int, tuple]], errors: _Errors) -> None:
    """Two rows for the same cell would be applied in an arbitrary order."""
    first: dict[tuple, int] = {}
    for row, identity in entries:
        if identity in first:
            errors.messages.append(f"{sheet} row {row}: same cell as row {first[identity]}.")
        else:
            first[identity] = row


_YES = frozenset({"yes", "y", "true", "1"})
_NO = frozenset({"no", "n", "false", "0"})
_NEEDS_KEY = frozenset({ADD_ROW, SET_CELL})
_NEEDS_COLUMN = frozenset({ADD_COLUMN, ADD_ROW, SET_CELL})
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FIRST_DATA_ROW = 2


def _cell_text(value) -> str:
    """A cell as text: whole numbers without ``.0``, so a numeric key or value reads as typed."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _required(value) -> str:
    if not (result := _cell_text(value)):
        raise ValueError("required.")
    return result


def _kind(value) -> str:
    if (kind := _cell_text(value).lower()) not in _KIND_ORDER:
        raise ValueError(f"expected one of {', '.join(_KIND_ORDER)}, got {_cell_text(value)!r}.")
    return kind


def _apply(value) -> bool:
    if isinstance(value, bool):
        return value
    answer = _cell_text(value).lower()
    if answer in _YES:
        return True
    if answer in _NO:
        return False
    raise ValueError(f"expected yes or no, got {_cell_text(value)!r}.")


def _whole_number(value, minimum: int) -> int:
    text_value = _cell_text(value)
    if isinstance(value, bool) or not text_value.isdigit() or int(text_value) < minimum:
        raise ValueError(f"expected a whole number of at least {minimum}, got {text_value!r}.")
    return int(text_value)


def _occurrence(value) -> int:
    """Blank means the first occurrence."""
    return 1 if _cell_text(value) == "" else _whole_number(value, 1)


def _row_number(value) -> int | None:
    """Blank means unknown; row 1 holds the headers."""
    return None if _cell_text(value) == "" else _whole_number(value, _FIRST_DATA_ROW)


def _rows(ws, columns: list[str]) -> list[tuple[int, dict]]:
    """Non-blank rows of a plan sheet with their row number, as raw cell values by column."""
    cols = headers(ws)
    missing = [c for c in columns if c not in cols]
    if missing:
        raise ValueError(f"Sheet '{ws.title}' of the plan lacks the columns {', '.join(missing)}.")
    rows = []
    for r in range(_FIRST_DATA_ROW, ws.max_row + 1):
        values = {c: ws.cell(row=r, column=cols[c]).value for c in columns}
        if any(_cell_text(v) for v in values.values()):
            rows.append((r, values))
    return rows


def default_plan_path(src: Path) -> Path:
    """The plan lives next to the source as ``{name}-plan.xlsx``."""
    src = Path(src)
    return src.with_name(f"{src.stem}-plan.xlsx")
