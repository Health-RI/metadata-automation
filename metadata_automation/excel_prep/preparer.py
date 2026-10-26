"""Turn a plain metadata Excel into one the shaclplay and sempyro commands accept.

Two modes:

- init: update the source in place with the structure, prefixes, sh:node for
  model ranges, (IRI) for other ranges and DASH, and run the checks.
- full: additionally apply the FDP rules (Resource sheet, independent classes
  by IRI with relaxed cardinality and URI DASH, title check) and write a new workbook.

Values that cannot be derived are left empty and listed in the report.

openpyxl drops drawings (text boxes, shapes, images) on save; they are copied back
from the source afterwards. In init mode the source is first copied to a ``.bak`` file.
"""

import os
import shutil
import tempfile
from pathlib import Path

from openpyxl import load_workbook

from metadata_automation.excel_prep.class_sheet import prepare_class_sheet
from metadata_automation.excel_prep.columns import FDP_SHEETS, GENERAL_SHEETS
from metadata_automation.excel_prep.dash import apply_dash_rules
from metadata_automation.excel_prep.drawings import drawing_sheets, restore_drawings
from metadata_automation.excel_prep.gaps import add_property_uris, collect_gaps
from metadata_automation.excel_prep.prefix_check import check_prefixes
from metadata_automation.excel_prep.report import Report
from metadata_automation.excel_prep.structure import (
    add_general_sheets,
    check_duplicates,
    prepare_classes_sheet,
    prepare_prefixes_sheet,
)
from metadata_automation.excel_prep.titles import check_titles
from metadata_automation.excel_prep.workbook import class_sheet_names


def prepare_workbook(
    src: Path, dst: Path | None = None, namespace: str | None = None, init: bool = False, overwrite: bool = False
) -> Report:
    """Prepare ``src`` and return what was done and what is missing.

    An empty class_URI is derived from ``namespace`` when given, and otherwise left empty.

    With ``init``, ``src`` is updated in place and ``dst`` must be None. Otherwise the FDP
    rules are applied too and the result is written to ``dst``, which must differ from ``src``
    and must not exist unless ``overwrite``. Nothing is written when 'classes' has duplicates.
    """
    src = Path(src)
    dst = _output_path(src, dst, init, overwrite)

    wb = load_workbook(src, rich_text=True)
    check_duplicates(wb)
    report = Report()

    if init and drawing_sheets(src):
        backup = src.with_name(src.name + ".bak")
        shutil.copy2(src, backup)
        report.change(src.name, None, None, f"copied to {backup.name} before the in-place update, as it has drawings")

    add_general_sheets(wb, GENERAL_SHEETS if init else GENERAL_SHEETS + FDP_SHEETS, report)
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
        prepare_class_sheet(wb[name], None if untargeted else model, init, report)
    if not untargeted:
        apply_dash_rules(wb, set(model), report)
    if not init:
        check_titles(wb, model, report)
    prepare_prefixes_sheet(wb, report)
    report.prefix_issues = check_prefixes(wb)
    add_property_uris(wb, report)
    collect_gaps(wb, report)

    _save(wb, src, dst, report)
    return report


def _output_path(src: Path, dst: Path | None, init: bool, overwrite: bool) -> Path:
    if init:
        if dst is not None:
            raise ValueError("--init updates the input in place; no output path is accepted.")
        return src
    if dst is None:
        raise ValueError("An output path is required.")
    dst = Path(dst)
    if not dst.exists():
        return dst
    if os.path.samefile(src, dst):
        raise ValueError("Output path must differ from the input path; the source file is left untouched.")
    if not overwrite:
        raise ValueError(f"Output file {dst} already exists; pass --overwrite to replace it.")
    return dst


def _save(wb, src: Path, dst: Path, report: Report) -> None:
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
