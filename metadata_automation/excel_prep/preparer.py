"""Turn a plain metadata Excel into one the shaclplay and sempyro commands accept.

Everything is derived from the workbook itself. Values that cannot be derived
are left empty and listed in the report. Existing values are never overwritten,
so running the preparation again on its own output only fills new gaps.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from metadata_automation.excel_prep.dash import DESCRIPTION_PROPERTY, expected_dash
from metadata_automation.excel_prep.prefix_check import check_prefixes, namespace_map, used_prefixes
from metadata_automation.excel_prep.report import Cell, Report
from metadata_automation.excel_prep.workbook import (
    NON_CLASS_SHEETS,
    class_sheet_names,
    copy_column_format,
    curie_prefix,
    data_rows,
    ensure_columns,
    headers,
    parse_bool,
    property_rows,
    split_iri_suffix,
    text,
)

BASE_COLUMNS = [
    "Property label",
    "Definition",
    "Property URI",
    "Controlled vocabulary (if applicable)",
    "Usage note",
    "Range",
    "Cardinality",
]
CLASS_SHEET_COLUMNS = [
    "SHACL_sh:node",
    "SHACL_dash:viewer",
    "SHACL_dash:editor",
    "SHACL_pattern",
    "SHACL_default_value",
    "SHACL_sh:uniqueLang",
    "SeMPyRO_rdf_term",
    "SeMPyRO_rdf_type",
    "SeMPyRO_range",
]
CLASSES_COLUMNS = [
    "sheet_name",
    "description",
    "class_URI",
    "SHACL_target_ontology_name",
    "SHACL_independent_class",
    "SeMPyRO_inherits_from",
    "SeMPyRO_import_classes",
    "SeMPyRO_annotations_ontology",
    "SeMPyRO_annotations_IRI",
    "SeMPyRO_add_rdf_model",
]
PREFIXES_COLUMNS = ["prefix", "namespace"]

REQUIRED_CLASSES_COLUMNS = [
    "class_URI",
    "SHACL_target_ontology_name",
    "SHACL_independent_class",
    "SeMPyRO_annotations_ontology",
    "SeMPyRO_annotations_IRI",
]
OPTIONAL_CLASSES_COLUMNS = ["description", "SeMPyRO_inherits_from", "SeMPyRO_import_classes", "SeMPyRO_add_rdf_model"]
REQUIRED_PROPERTY_COLUMNS = ["SeMPyRO_rdf_term", "SeMPyRO_rdf_type", "SeMPyRO_range"]
OPTIONAL_PROPERTY_COLUMNS = [
    "SHACL_dash:viewer",
    "SHACL_dash:editor",
    "SHACL_pattern",
    "SHACL_default_value",
    "SHACL_sh:uniqueLang",
]

LITERAL_PREFIXES = ("xsd", "rdfs")
TITLE_PROPERTY = "dct:title"
GENERAL_SHEETS = ["prefixes", "classes", "Resource"]

_CARDINALITY = re.compile(r"^(\d+)(?:\.\.(\d+|n|\*))?$")


@dataclass
class ModelClass:
    """A class of this metadata model, as configured in the 'classes' sheet."""

    sheet: str
    class_uri: str
    independent: bool | None


def prepare_workbook(src: Path, dst: Path, namespace: str = "hri") -> Report:
    """Write a prepared copy of ``src`` to ``dst`` and return what was done and what is missing."""
    src, dst = Path(src), Path(dst)
    if dst.resolve() == src.resolve():
        raise ValueError("Output path must differ from the input path; the source file is left untouched.")

    wb = load_workbook(src)
    report = Report()

    _add_general_sheets(wb, report)
    model = _prepare_classes_sheet(wb, namespace, report)
    # Without every target class known, a range cannot be told apart from an out-of-model one.
    untargeted = [n for n in class_sheet_names(wb) if n not in {c.sheet for c in model.values()}]
    if untargeted:
        report.issue(
            "classes", None, "SHACL_target_ontology_name", "range rules skipped until filled in for every class"
        )
    for name in class_sheet_names(wb):
        _prepare_class_sheet(wb[name], model if not untargeted else None, report)
    if not untargeted:
        _apply_dash_rules(wb, report)
    _check_titles(wb, model, report)
    _prepare_prefixes_sheet(wb, report)
    report.prefix_issues = check_prefixes(wb)
    _collect_gaps(wb, report)

    dst.parent.mkdir(parents=True, exist_ok=True)
    wb.save(dst)
    return report


def _add_general_sheets(wb: Workbook, report: Report) -> None:
    """Create missing prefixes, classes and Resource sheets after Info / User Guide."""
    index = max((wb.sheetnames.index(n) + 1 for n in ("Info", "User Guide") if n in wb.sheetnames), default=0)
    columns = {"prefixes": PREFIXES_COLUMNS, "classes": CLASSES_COLUMNS, "Resource": BASE_COLUMNS}
    for name in GENERAL_SHEETS:
        if name in wb.sheetnames:
            index = wb.sheetnames.index(name) + 1
            continue
        ws = wb.create_sheet(name, index)
        for col, header in enumerate(columns[name], start=1):
            ws.cell(row=1, column=col, value=header)
        report.change(name, None, None, "added sheet")
        index += 1


def _prepare_classes_sheet(wb: Workbook, namespace: str, report: Report) -> dict[str, ModelClass]:
    """Add missing columns and rows, derive class_URI, and return the model classes by target name."""
    ws = wb["classes"]
    cols, added = ensure_columns(ws, CLASSES_COLUMNS)
    if added:
        report.change("classes", None, None, f"added columns {', '.join(added)}")

    sheets = class_sheet_names(wb)
    rows = _class_rows(ws, cols, sheets, report)

    model: dict[str, ModelClass] = {}
    for name in sheets:
        row = rows[name]
        target = text(ws, row, cols["SHACL_target_ontology_name"])
        class_uri = text(ws, row, cols["class_URI"])
        if not class_uri and curie_prefix(target):
            class_uri = f"{namespace}:{target.split(':', 1)[1]}"
            ws.cell(row=row, column=cols["class_URI"], value=class_uri)
            report.change("classes", row, "class_URI", f"set to '{class_uri}'")

        raw_independent = ws.cell(row=row, column=cols["SHACL_independent_class"]).value
        independent = parse_bool(raw_independent)
        if independent is None and text(ws, row, cols["SHACL_independent_class"]):
            report.issue("classes", row, "SHACL_independent_class", f"expected TRUE or FALSE, got {raw_independent!r}")

        if not target:
            continue
        if target in model:
            report.issue(
                "classes", row, "SHACL_target_ontology_name", f"'{target}' also used by '{model[target].sheet}'"
            )
            continue
        model[target] = ModelClass(name, class_uri, independent)
    return model


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


def _prepare_class_sheet(ws: Worksheet, model: dict[str, ModelClass] | None, report: Report) -> None:
    """Add pipeline columns and, when ``model`` is given, apply the range rules."""
    cols, added = ensure_columns(ws, CLASS_SHEET_COLUMNS)
    if added:
        for name in added:
            copy_column_format(ws, 1, cols[name])
        report.change(ws.title, None, None, f"added columns {', '.join(added)}")
    if model is None:
        return
    if "Range" not in cols:
        report.issue(ws.title, None, "Range", "column missing")
        return

    for row in property_rows(ws, cols):
        value = text(ws, row, cols["Range"])
        if not value:
            continue
        base, has_iri = split_iri_suffix(value)
        if base in model:
            _apply_model_range(ws, row, cols, base, has_iri, model[base], report)
        elif not has_iri and curie_prefix(base) and curie_prefix(base) not in LITERAL_PREFIXES:
            _set(ws, row, cols["Range"], f"{base} (IRI)", report, "Range", "range is not a class of this model")


def _apply_model_range(
    ws: Worksheet,
    row: int,
    cols: dict[str, int],
    base: str,
    has_iri: bool,
    cls: ModelClass,
    report: Report,
) -> None:
    """Independent classes are referenced by IRI with optional cardinality; dependent ones are nested."""
    if cls.independent is None:
        return
    if cls.independent:
        if not has_iri:
            _set(ws, row, cols["Range"], f"{base} (IRI)", report, "Range", f"'{cls.sheet}' is an independent class")
        _relax_cardinality(ws, row, cols, cls, report)
        return
    if has_iri:
        report.issue(ws.title, row, "Range", f"'{cls.sheet}' is a dependent class but the range ends in (IRI)")
    elif cls.class_uri and not text(ws, row, cols["SHACL_sh:node"]):
        _set(ws, row, cols["SHACL_sh:node"], f"{cls.class_uri}Shape", report, "SHACL_sh:node", "dependent class")


def _relax_cardinality(ws: Worksheet, row: int, cols: dict[str, int], cls: ModelClass, report: Report) -> None:
    if "Cardinality" not in cols:
        return
    current = text(ws, row, cols["Cardinality"])
    relaxed = relax_cardinality(current)
    if relaxed is None:
        report.issue(ws.title, row, "Cardinality", f"cannot parse {current!r}")
    elif relaxed != current:
        _set(ws, row, cols["Cardinality"], relaxed, report, "Cardinality", f"'{cls.sheet}' is an independent class")


def relax_cardinality(cardinality: str) -> str | None:
    """Lower the minimum to 0: ``"1..n"`` -> ``"0..n"``, ``"1"`` -> ``"0..1"``. None when unparsable."""
    match = _CARDINALITY.match(cardinality.strip())
    if not match:
        return None
    low, high = match.group(1), match.group(2)
    if int(low) == 0:
        return cardinality
    return f"0..{high or low}"


def _set(ws: Worksheet, row: int, col: int, value: str, report: Report, column: str, reason: str) -> None:
    old = text(ws, row, col)
    ws.cell(row=row, column=col, value=value)
    change = f"'{old}' -> '{value}'" if old else f"set to '{value}'"
    report.change(ws.title, row, column, f"{change} ({reason})")


def _apply_dash_rules(wb: Workbook, report: Report) -> None:
    """Fill empty viewer/editor cells with the expected value; report existing values that differ."""
    namespaces = namespace_map(wb)
    description_iri = _expand(DESCRIPTION_PROPERTY, namespaces)
    for name in class_sheet_names(wb):
        ws = wb[name]
        cols = headers(ws)
        for row in property_rows(ws, cols):
            uri = text(ws, row, cols.get("Property URI"))
            is_description = uri == DESCRIPTION_PROPERTY or bool(
                description_iri and _expand(uri, namespaces) == description_iri
            )
            expected = expected_dash(
                text(ws, row, cols.get("Range")), text(ws, row, cols["SHACL_sh:node"]), is_description
            )
            if expected is None:
                continue
            for column, value in zip(("SHACL_dash:viewer", "SHACL_dash:editor"), expected, strict=True):
                current = text(ws, row, cols[column])
                if not current:
                    _set(ws, row, cols[column], value, report, column, "derived from range")
                elif current != value:
                    report.issue(name, row, column, f"expected '{value}', found '{current}'")


def _check_titles(wb: Workbook, model: dict[str, ModelClass], report: Report) -> None:
    """Independent classes are listed on their own in the FDP, so they need a title."""
    namespaces = namespace_map(wb)
    title_iri = _expand(TITLE_PROPERTY, namespaces)
    for cls in model.values():
        if not cls.independent:
            continue
        ws = wb[cls.sheet]
        cols = headers(ws)
        uris = [text(ws, r, cols.get("Property URI")) for r in property_rows(ws, cols)]
        if not any(u == TITLE_PROPERTY or (title_iri and _expand(u, namespaces) == title_iri) for u in uris):
            report.issue(cls.sheet, None, "Property URI", f"independent class has no {TITLE_PROPERTY} property")


def _expand(curie: str, namespaces: dict[str, str]) -> str | None:
    prefix = curie_prefix(curie)
    if prefix and namespaces.get(prefix):
        return namespaces[prefix] + curie.split(":", 1)[1]
    return None


def _prepare_prefixes_sheet(wb: Workbook, report: Report) -> None:
    ws = wb["prefixes"]
    cols, added = ensure_columns(ws, PREFIXES_COLUMNS)
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


def _collect_gaps(wb: Workbook, report: Report) -> None:
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
