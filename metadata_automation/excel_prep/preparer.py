"""Turn a plain metadata Excel into one the shaclplay and sempyro commands accept.

Adds the structure, prefixes, sh:node for model ranges, (IRI) for other ranges and DASH, and runs the checks. The
source is either updated in place or the result is written to a new workbook. Values that cannot be derived are left
empty and listed in the report. The FDP variant of a workbook is derived separately, see ``fdp.py``.

openpyxl drops drawings (text boxes, shapes, images) on save; they are copied back from the source afterwards.
In place, the source is first copied to a ``.bak`` file when it has drawings.
"""

import os
import shutil
import tempfile
from pathlib import Path

from openpyxl import load_workbook

from metadata_automation.excel_prep.class_sheet import prepare_class_sheet
from metadata_automation.excel_prep.columns import GENERAL_SHEETS
from metadata_automation.excel_prep.dash import apply_dash_rules
from metadata_automation.excel_prep.drawings import drawing_sheets, restore_drawings
from metadata_automation.excel_prep.gaps import add_property_uris, collect_gaps
from metadata_automation.excel_prep.prefix_check import check_prefixes
from metadata_automation.excel_prep.report import Report
from metadata_automation.excel_prep.structure import (
    ModelClass,
    add_general_sheets,
    check_duplicates,
    normalize_sheet_names,
    prepare_classes_sheet,
    prepare_prefixes_sheet,
)
from metadata_automation.excel_prep.workbook import class_sheet_names


def prepare_workbook(
    src: Path, dst: Path | None = None, namespace: str | None = None, overwrite: bool = False
) -> Report:
    """Prepare ``src`` and return what was done and what is missing.

    An empty class_URI is derived from ``namespace`` when given, and otherwise left empty.

    Without ``dst``, ``src`` is updated in place. Otherwise the result is written to ``dst``, which must differ from
    ``src`` and must not exist unless ``overwrite``. Nothing is written when 'classes' has duplicates.
    """
    src = Path(src)
    dst = resolve_output(src, dst, overwrite)

    wb = load_workbook(src, rich_text=True)
    report = Report()
    prepare_in_memory(wb, namespace, report)

    if dst == src and drawing_sheets(src):
        backup = src.with_name(src.name + ".bak")
        shutil.copy2(src, backup)
        report.change(src.name, None, None, f"copied to {backup.name} before the in-place update, as it has drawings")

    save_workbook(wb, src, dst, report)
    return report


def prepare_in_memory(
    wb, namespace: str | None, report: Report, extra_sheets: tuple[str, ...] | list[str] = ()
) -> tuple[dict[str, ModelClass], list[str]]:
    """Apply the general steps to ``wb``, plus the ``extra_sheets`` to add. Returns the model and untargeted classes."""
    normalize_sheet_names(wb, report)
    check_duplicates(wb)

    add_general_sheets(wb, GENERAL_SHEETS + list(extra_sheets), report)
    model, untargeted = prepare_classes_sheet(wb, namespace, report)
    # Without every target class known, a range cannot be told apart from an out-of-model one.
    if untargeted:
        report.issue(
            "classes",
            None,
            "SHACL_target_ontology_name",
            f"range rules skipped until filled in for every class; empty for {', '.join(untargeted)}",
        )
    for name in class_sheet_names(wb):
        prepare_class_sheet(wb[name], None if untargeted else model, report)
    if not untargeted:
        apply_dash_rules(wb, set(model), report)
    prepare_prefixes_sheet(wb, report)
    report.prefix_issues = check_prefixes(wb)
    add_property_uris(wb, report)
    collect_gaps(wb, report)
    return model, untargeted


def resolve_output(src: Path, dst: Path | None, overwrite: bool) -> Path:
    """Where to write: ``src`` itself without ``dst``, else ``dst`` after checking it may be written."""
    if dst is None:
        return src
    dst = Path(dst)
    if not dst.exists():
        return dst
    if os.path.samefile(src, dst):
        raise ValueError("Output path must differ from the input path; the source file is left untouched.")
    if not overwrite:
        raise ValueError(f"Output file {dst} already exists; pass --overwrite to replace it.")
    return dst


def save_workbook(wb, src: Path, dst: Path, report: Report) -> None:
    """Save with the drawings of ``src`` through a temporary file, so a failed save leaves ``dst`` intact."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=dst.suffix, dir=dst.parent)
    os.close(fd)
    try:
        wb.save(tmp)
        for sheet in restore_drawings(src, Path(tmp)):
            report.issue(sheet, None, None, "drawings (text boxes, shapes, images) could not be kept")
        _set_mode(Path(tmp), dst)
        os.replace(tmp, dst)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _set_mode(tmp: Path, dst: Path) -> None:
    """Give ``tmp`` the mode of an existing ``dst``, or that of a new file, instead of mkstemp's 0600."""
    if dst.exists():
        shutil.copymode(dst, tmp)
        return
    umask = os.umask(0)
    os.umask(umask)
    tmp.chmod(0o666 & ~umask)
