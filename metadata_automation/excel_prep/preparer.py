"""Turn a plain metadata Excel into one the shaclplay and sempyro commands accept.

Two modes:

- init: update the source in place with the structure, prefixes, sh:node for
  model ranges and DASH, and run the checks.
- full: additionally apply the FDP rules (Resource sheet, (IRI) ranges,
  relaxed cardinality, title check) and write a new workbook.

Values that cannot be derived are left empty and listed in the report.
"""

from pathlib import Path

from openpyxl import load_workbook

from metadata_automation.excel_prep.columns import FDP_SHEETS, GENERAL_SHEETS
from metadata_automation.excel_prep.dash import apply_dash_rules
from metadata_automation.excel_prep.gaps import add_property_uris, collect_gaps
from metadata_automation.excel_prep.prefix_check import check_prefixes
from metadata_automation.excel_prep.ranges import prepare_class_sheet
from metadata_automation.excel_prep.report import Report
from metadata_automation.excel_prep.structure import add_general_sheets, prepare_classes_sheet, prepare_prefixes_sheet
from metadata_automation.excel_prep.titles import check_titles
from metadata_automation.excel_prep.workbook import class_sheet_names


def prepare_workbook(src: Path, dst: Path | None = None, namespace: str | None = None, init: bool = False) -> Report:
    """Prepare ``src`` and return what was done and what is missing.

    An empty class_URI is derived from ``namespace`` when given, and otherwise left empty.

    With ``init``, ``src`` is updated in place and ``dst`` must be None. Otherwise the FDP
    rules are applied too and the result is written to ``dst``, which must differ from ``src``.
    """
    src = Path(src)
    dst = _output_path(src, dst, init)

    wb = load_workbook(src)
    report = Report()

    add_general_sheets(wb, GENERAL_SHEETS if init else GENERAL_SHEETS + FDP_SHEETS, report)
    model = prepare_classes_sheet(wb, namespace, report)
    # Without every target class known, a range cannot be told apart from an out-of-model one.
    untargeted = [n for n in class_sheet_names(wb) if n not in {c.sheet for c in model.values()}]
    if untargeted:
        report.issue(
            "classes", None, "SHACL_target_ontology_name", "range rules skipped until filled in for every class"
        )
    for name in class_sheet_names(wb):
        prepare_class_sheet(wb[name], None if untargeted else model, init, report)
    if not untargeted:
        apply_dash_rules(wb, report)
    if not init:
        check_titles(wb, model, report)
    prepare_prefixes_sheet(wb, report)
    report.prefix_issues = check_prefixes(wb)
    add_property_uris(wb, report)
    collect_gaps(wb, report)

    dst.parent.mkdir(parents=True, exist_ok=True)
    wb.save(dst)
    return report


def _output_path(src: Path, dst: Path | None, init: bool) -> Path:
    if init:
        if dst is not None:
            raise ValueError("--init updates the input in place; no output path is accepted.")
        return src
    if dst is None:
        raise ValueError("An output path is required.")
    if Path(dst).resolve() == src.resolve():
        raise ValueError("Output path must differ from the input path; the source file is left untouched.")
    return Path(dst)
