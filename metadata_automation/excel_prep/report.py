"""Report of changes, issues and unfilled cells from Excel preparation."""

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Cell:
    """A location in the workbook. ``row`` and ``column`` are optional for sheet-level findings."""

    sheet: str
    row: int | None = None
    column: str | None = None

    def __str__(self) -> str:
        parts = [self.sheet]
        if self.column:
            parts.append(self.column)
        if self.row:
            parts.append(f"row {self.row}")
        return " / ".join(parts)


@dataclass(frozen=True)
class Finding:
    """A change made or an issue found at a location."""

    cell: Cell
    message: str


@dataclass
class Report:
    """Collects everything the modeler should know about a preparation run."""

    changes: list[Finding] = field(default_factory=list)
    issues: list[Finding] = field(default_factory=list)
    prefix_issues: list[Finding] = field(default_factory=list)
    gaps: list[Cell] = field(default_factory=list)
    optional_gaps: list[Cell] = field(default_factory=list)

    def change(self, sheet: str, row: int | None, column: str | None, message: str) -> None:
        self.changes.append(Finding(Cell(sheet, row, column), message))

    def issue(self, sheet: str, row: int | None, column: str | None, message: str) -> None:
        self.issues.append(Finding(Cell(sheet, row, column), message))

    def format(self) -> str:
        """Render the report as plain text."""
        lines = []
        lines += _format_findings("Changes made", self.changes)
        lines += _format_findings("Issues", self.issues)
        lines += _format_findings("Prefix check", self.prefix_issues)
        lines += _format_gaps("Required cells to fill in", self.gaps)
        lines += _format_optional(self.optional_gaps)
        return "\n".join(lines)


def _format_findings(title: str, findings: list[Finding]) -> list[str]:
    lines = [f"{title} ({len(findings)}):"]
    if not findings:
        return lines + ["  none", ""]
    lines += [f"  - {f.cell}: {f.message}" for f in findings]
    return lines + [""]


def _format_gaps(title: str, gaps: list[Cell]) -> list[str]:
    lines = [f"{title} ({len(gaps)}):"]
    if not gaps:
        return lines + ["  none", ""]
    grouped: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for gap in gaps:
        grouped[gap.sheet][gap.column].append(gap.row)
    for sheet, columns in grouped.items():
        lines.append(f"  {sheet}:")
        for column, rows in columns.items():
            label = "row" if len(rows) == 1 else "rows"
            lines.append(f"    - {column}: {label} {compress_rows(rows)}")
    return lines + [""]


def _format_optional(gaps: list[Cell]) -> list[str]:
    lines = [f"Optional cells left empty ({len(gaps)}):"]
    if not gaps:
        return lines + ["  none", ""]
    sheets: dict[str, set[str]] = defaultdict(set)
    counts: dict[str, int] = defaultdict(int)
    for gap in gaps:
        sheets[gap.column].add(gap.sheet)
        counts[gap.column] += 1
    for column, count in counts.items():
        lines.append(f"  - {column}: {count} rows in {len(sheets[column])} sheets")
    return lines + [""]


def compress_rows(rows: list[int]) -> str:
    """Render row numbers as ranges, e.g. ``[2, 3, 4, 7]`` -> ``"2-4, 7"``."""
    rows = sorted(set(rows))
    ranges = []
    start = prev = rows[0]
    for row in rows[1:]:
        if row != prev + 1:
            ranges.append((start, prev))
            start = row
        prev = row
    ranges.append((start, prev))
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in ranges)
