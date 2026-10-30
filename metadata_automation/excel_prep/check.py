"""Check that the technical columns of a metadata Excel are correct and complete.

The check is the plan computed in memory: it passes when the plan is empty, i.e. no edit is pending (correct) and no
required cell is empty (complete).
"""

from collections import defaultdict
from pathlib import Path

from metadata_automation.excel_prep.plan import Plan, default_plan_path

DEFAULT_HINT = "Run `plan-excel` on the Excel, inspect the plan, and apply it with `apply-plan`."
_MAX_ROWS = 40


def format_check(plan: Plan, hint: str = DEFAULT_HINT, source: Path | None = None) -> str:
    """Render the outcome as markdown, for the terminal and the job summary of a workflow."""
    if plan.is_empty:
        passed = f"## Excel check passed\n\nThe technical columns of `{plan.source_name}` are correct and complete.\n"
        return passed + _ignored_note(plan)

    lines = [f"## Excel check failed for `{plan.source_name}`", ""]
    lines.append(f"- {len(plan.edits)} edit(s) pending: the technical columns are not up to date.")
    lines.append(f"- {len(plan.gaps)} required cell(s) empty: the technical columns are not complete.")
    lines += ["", "### Next step", "", hint]
    if source is not None and default_plan_path(source).exists():
        lines += ["", f"A plan `{default_plan_path(source).name}` is already next to the source; apply it first."]

    if plan.edits:
        lines += [
            "",
            "### Pending edits",
            "",
            "| Kind | Sheet | Key | Column | Current | Proposed |",
            "|---|---|---|---|---|---|",
        ]
        for e in plan.edits[:_MAX_ROWS]:
            cells = [e.kind, e.sheet, e.key, e.column, e.old, e.new]
            lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
        if len(plan.edits) > _MAX_ROWS:
            lines.append(f"\n…and {len(plan.edits) - _MAX_ROWS} more.")

    if plan.gaps:
        grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
        for g in plan.gaps:
            grouped[(g.sheet, g.column)].append(g.key)
        lines += ["", "### Required cells to fill in", "", "| Sheet | Column | Rows | Examples |", "|---|---|---|---|"]
        for (sheet, column), keys in list(grouped.items())[:_MAX_ROWS]:
            examples = ", ".join(_cell(k) for k in keys[:3]) + (", …" if len(keys) > 3 else "")
            lines.append(f"| {_cell(sheet)} | {_cell(column)} | {len(keys)} | {examples} |")
    return "\n".join(lines) + "\n" + _ignored_note(plan)


def _ignored_note(plan: Plan) -> str:
    if not plan.ignored_columns:
        return ""
    return f"\nNot checked: {plan.ignored_gaps} required cell(s) in columns matching `{plan.ignored_columns}`.\n"


def _cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
