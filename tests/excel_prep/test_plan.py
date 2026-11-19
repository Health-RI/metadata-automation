"""Planning the technical columns: the source is untouched, the plan lists what would change."""

import shutil

import pytest
from openpyxl import Workbook, load_workbook
from prep_helpers import CLASS_ANSWERS, answer_classes, fill_reported_gaps, sha

from metadata_automation.cli import plan_excel
from metadata_automation.excel_prep import plan as plan_module
from metadata_automation.excel_prep.plan import (
    ADD_COLUMN,
    ADD_ROW,
    ADD_SHEET,
    RENAME_SHEET,
    SET_CELL,
    Edit,
    Gap,
    IssueRow,
    Plan,
    compute_plan,
    default_plan_path,
    read_plan,
    row_key,
    write_plan,
)
from metadata_automation.excel_prep.preparer import prepare_in_memory, prepare_workbook
from metadata_automation.excel_prep.workbook import headers


@pytest.fixture
def source(plain_small, tmp_path):
    path = tmp_path / "model.xlsx"
    shutil.copy(plain_small, path)
    return path


@pytest.fixture
def prepared(source):
    """The source after the class questions are answered and prepared, so most rules apply."""
    prepare_workbook(source)
    answer_classes(source, {k: v for k, v in CLASS_ANSWERS.items() if k != "Resource"})
    prepare_workbook(source)
    return source


PLAN_HASH = "a" * 64


@pytest.fixture
def plan_file(tmp_path):
    """Edits rows 2-5: add sheet, two set cell, add column. Gaps row 2."""
    plan = Plan("model.xlsx", PLAN_HASH, "1.1.0")
    plan.edits = [
        Edit(ADD_SHEET, "classes", reason="required sheet"),
        Edit(SET_CELL, "Catalog", "dct:title", 1, "SHACL_sh:node", "a", "b", "why", 5),
        Edit(SET_CELL, "Catalog", "dct:publisher", 1, "Range", "x", "y", "why", 6),
        Edit(ADD_COLUMN, "Catalog", column="SeMPyRO_range", reason="pipeline column"),
    ]
    plan.gaps = [Gap("Catalog", "dct:title", 1, "SeMPyRO_rdf_term", row=5)]
    path = tmp_path / "plan.xlsx"
    write_plan(plan, path)
    return path


def _edit_plan(path, change):
    """Edit a plan workbook as a person would."""
    wb = load_workbook(path)
    change(wb)
    wb.save(path)


class TestComputePlan:
    def test_source_is_not_modified(self, source):
        before = sha(source)
        compute_plan(source)
        assert sha(source) == before

    def test_summary_identifies_the_source(self, source):
        plan, _ = compute_plan(source)
        assert plan.source_name == "model.xlsx"
        assert plan.source_hash == sha(source)

    def test_structural_edits_for_a_plain_workbook(self, source):
        plan, _ = compute_plan(source)
        kinds = {e.kind for e in plan.edits}
        assert {ADD_SHEET, ADD_COLUMN, ADD_ROW} <= kinds
        assert {e.sheet for e in plan.edits if e.kind == ADD_SHEET} == {"prefixes", "classes"}
        assert {e.key for e in plan.edits if e.kind == ADD_ROW and e.sheet == "classes"} == {
            "Catalog",
            "Dataset",
            "Agent",
            "Distribution",
        }
        added = {e.column for e in plan.edits if e.kind == ADD_COLUMN and e.sheet == "Catalog"}
        assert {"SHACL_sh:node", "SeMPyRO_range"} <= added

    def test_added_row_carries_its_key_value(self, source):
        plan, _ = compute_plan(source)
        row = next(e for e in plan.edits if e.kind == ADD_ROW and e.key == "Dataset")
        assert (row.column, row.new) == ("sheet_name", "Dataset")

    def test_cell_edits_name_the_property_and_the_reason(self, prepared):
        wb = load_workbook(prepared)
        ws = wb["Catalog"]
        cols = headers(ws)
        row = next(
            r for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=cols["Property URI"]).value == "dct:publisher"
        )
        ws.cell(row=row, column=cols["SHACL_sh:node"], value="old:AgentShape")
        wb.save(prepared)

        plan, _ = compute_plan(prepared)
        edit = next(e for e in plan.edits if e.kind == SET_CELL)
        assert (edit.sheet, edit.key, edit.column) == ("Catalog", "dct:publisher", "SHACL_sh:node")
        assert (edit.old, edit.new) == ("old:AgentShape", "hri:AgentShape")
        assert edit.reason == "class of this model"
        assert edit.apply is True

    def test_prepared_workbook_has_no_edits(self, prepared):
        plan, _ = compute_plan(prepared)
        assert plan.edits == []

    def test_gaps_are_required_cells_only_and_keyed_by_content(self, prepared):
        plan, _ = compute_plan(prepared)
        assert not plan.is_empty
        columns = {(g.sheet, g.column) for g in plan.gaps}
        assert ("Catalog", "SeMPyRO_rdf_term") in columns
        assert ("classes", "SeMPyRO_annotations_IRI") in columns
        assert all(g.key and g.value == "" for g in plan.gaps)
        assert not any(g.column == "SHACL_pattern" for g in plan.gaps)

    def test_fully_prepared_and_filled_workbook_gives_an_empty_plan(self, prepared):
        fill_reported_gaps(prepared)
        prepare_workbook(prepared)
        plan, _ = compute_plan(prepared)
        assert plan.is_empty, (plan.edits[:3], plan.gaps[:3])

    def test_duplicate_keys_get_an_occurrence_number(self, tmp_path):
        wb = Workbook()
        ws = wb.active
        ws.title = "Thing"
        ws.append(["Property label", "Property URI", "Range", "Cardinality"])
        ws.append(["a", "ex:p", "xsd:string", "1"])
        ws.append(["b", "ex:p", "xsd:string", "1"])
        path = tmp_path / "dup.xlsx"
        wb.save(path)

        plan, _ = compute_plan(path)
        gaps = [g for g in plan.gaps if g.sheet == "Thing" and g.column == "SeMPyRO_rdf_term"]
        assert [(g.key, g.occurrence) for g in gaps] == [("ex:p", 1), ("ex:p", 2)]

    def test_rows_are_keyed_as_the_source_names_them(self, tmp_path, monkeypatch):
        wb = Workbook()
        ws = wb.active
        ws.title = "Thing"
        ws.append(["Property label", "Property URI", "Range", "Cardinality"])
        ws.append(["title", None, "xsd:string", "1"])
        path = tmp_path / "label.xlsx"
        wb.save(path)

        def prepare_and_fill_uri(prepared, namespace, report):
            prepare_in_memory(prepared, namespace, report)
            sheet = prepared["Thing"]
            sheet.cell(row=2, column=headers(sheet)["Property URI"], value="ex:title")

        monkeypatch.setattr(plan_module, "prepare_in_memory", prepare_and_fill_uri)
        plan, _ = compute_plan(path)
        edit = next(e for e in plan.edits if e.kind == SET_CELL and e.column == "Property URI")
        assert (edit.key, edit.occurrence, edit.new) == ("label: title", 1, "ex:title")
        assert {g.key for g in plan.gaps if g.sheet == "Thing"} == {"label: title"}

    def test_duplicate_keys_get_their_own_cell_edits(self, tmp_path):
        wb = Workbook()
        ws = wb.active
        ws.title = "Thing"
        ws.append(["Property label", "Property URI", "Range", "Cardinality"])
        ws.append(["a", "ex:p", "ex:Foo", "1"])
        ws.append(["b", "ex:p", "ex:Bar", "1"])
        classes = wb.create_sheet("classes")
        classes.append(["sheet_name", "SHACL_target_ontology_name", "class_URI"])
        classes.append(["Thing", "ex:Thing", "ex:Thing"])
        path = tmp_path / "dup.xlsx"
        wb.save(path)

        plan, _ = compute_plan(path)
        ranges = [(e.key, e.occurrence, e.old, e.new) for e in plan.edits if e.kind == SET_CELL and e.column == "Range"]
        assert ranges == [("ex:p", 1, "ex:Foo", "ex:Foo (IRI)"), ("ex:p", 2, "ex:Bar", "ex:Bar (IRI)")]

    def test_rename_precedes_the_edits_of_the_renamed_sheet(self, source):
        wb = load_workbook(source)
        wb.create_sheet("Classes", 0)
        wb["Classes"].append(["sheet_name"])
        wb.save(source)

        plan, _ = compute_plan(source)
        rename = next(i for i, e in enumerate(plan.edits) if e.kind == RENAME_SHEET)
        on_sheet = [i for i, e in enumerate(plan.edits) if e.sheet == "classes" and e.kind != RENAME_SHEET]
        assert on_sheet and rename < min(on_sheet)
        assert {e.key for e in plan.edits if e.kind == ADD_ROW and e.sheet == "classes"} >= {"Catalog", "Dataset"}

    def test_issues_alone_leave_the_plan_empty(self):
        plan = Plan("m.xlsx", "0" * 64, "1", issues=[IssueRow("classes", "Catalog", "x", "note")])
        assert plan.is_empty

    def test_case_variant_of_a_general_sheet_is_a_rename(self, source):
        wb = load_workbook(source)
        wb.create_sheet("Classes", 0)
        wb["Classes"].append(["sheet_name"])
        wb.save(source)

        plan, _ = compute_plan(source)
        rename = next(e for e in plan.edits if e.kind == RENAME_SHEET)
        assert (rename.old, rename.new) == ("Classes", "classes")

    def test_row_key_falls_back_to_label_and_row_number(self):
        ws = Workbook().active
        ws.append(["Property label", "Property URI"])
        ws.append(["only a label", None])
        ws.append([None, None])
        cols = headers(ws)
        assert row_key(ws, 2, cols) == "label: only a label"
        assert row_key(ws, 3, cols) == "row 3"


class TestPlanFile:
    def test_round_trip(self, source, tmp_path):
        plan, _ = compute_plan(source, namespace="ex")
        path = tmp_path / "plan.xlsx"
        write_plan(plan, path)

        loaded = read_plan(path)
        assert loaded.source_name == plan.source_name
        assert loaded.source_hash == plan.source_hash
        assert loaded.namespace == "ex"
        assert loaded.edits == plan.edits
        assert loaded.gaps == plan.gaps
        assert loaded.issues == plan.issues

    def test_edits_by_a_person_are_read_back(self, source, tmp_path):
        plan, _ = compute_plan(source)
        path = tmp_path / "plan.xlsx"
        write_plan(plan, path)
        wb = load_workbook(path)
        edits, gaps = wb["Edits"], wb["Gaps"]
        edits.cell(row=2, column=1, value="no")
        gaps.cell(row=2, column=5, value="hri:Catalog")
        wb.save(path)

        loaded = read_plan(path)
        assert loaded.edits[0].apply is False
        assert all(e.apply for e in loaded.edits[1:])
        assert loaded.gaps[0].value == "hri:Catalog"

    def test_existing_plan_is_not_overwritten(self, source, tmp_path):
        plan, _ = compute_plan(source)
        path = tmp_path / "plan.xlsx"
        write_plan(plan, path)
        with pytest.raises(ValueError, match="--overwrite"):
            write_plan(plan, path)
        write_plan(plan, path, overwrite=True)

    def test_a_workbook_that_is_not_a_plan_is_rejected(self, source):
        with pytest.raises(ValueError, match="not a plan"):
            read_plan(source)

    @pytest.mark.parametrize(
        ("typed", "expected"),
        [
            ("no", False),
            ("N", False),
            ("FALSE", False),
            (0, False),
            (False, False),
            ("Y", True),
            (True, True),
            (1, True),
        ],
    )
    def test_apply_accepts_yes_and_no_spellings(self, plan_file, typed, expected):
        _edit_plan(plan_file, lambda wb: wb["Edits"].cell(row=2, column=1, value=typed))
        assert read_plan(plan_file).edits[0].apply is expected

    def test_invalid_cells_are_reported_together(self, plan_file):
        def spoil(wb):
            edits = wb["Edits"]
            edits.cell(row=2, column=1, value="ok")
            edits.cell(row=3, column=2, value="move cell")
            edits.cell(row=4, column=5, value="two")
            edits.cell(row=5, column=10, value=1)
            wb["Gaps"].cell(row=2, column=2).value = None

        _edit_plan(plan_file, spoil)
        with pytest.raises(ValueError) as error:
            read_plan(plan_file)
        message = str(error.value)
        for problem in ("Edits row 2, Apply", "Edits row 3, Kind", "Edits row 4, Occurrence", "Edits row 5, Row"):
            assert problem in message
        assert "Gaps row 2, Key" in message

    def test_numeric_cells_are_read_as_typed(self, plan_file):
        def numbers(wb):
            wb["Edits"].cell(row=2, column=5, value=2.0)
            wb["Gaps"].cell(row=2, column=5, value=1)

        _edit_plan(plan_file, numbers)
        loaded = read_plan(plan_file)
        assert loaded.edits[0].occurrence == 2
        assert loaded.gaps[0].value == "1"

    def test_set_cell_edits_need_a_key_and_column(self, plan_file):
        def blank(wb):
            wb["Edits"].cell(row=3, column=4).value = None
            wb["Edits"].cell(row=3, column=6).value = None

        _edit_plan(plan_file, blank)
        with pytest.raises(ValueError, match="Key: required for 'set cell'") as error:
            read_plan(plan_file)
        assert "Column: required for 'set cell'" in str(error.value)

    def test_two_edits_of_the_same_cell_are_rejected(self, plan_file):
        def duplicate(wb):
            edits = wb["Edits"]
            edits.append([c.value for c in edits[3]])

        _edit_plan(plan_file, duplicate)
        with pytest.raises(ValueError, match="same cell as row"):
            read_plan(plan_file)

    def test_summary_needs_the_source_hash(self, plan_file):
        def clear_hash(wb):
            wb["Summary"].cell(row=2, column=2).value = None

        _edit_plan(plan_file, clear_hash)
        with pytest.raises(ValueError, match="Source SHA-256"):
            read_plan(plan_file)

    def test_summary_is_read_by_label(self, plan_file):
        _edit_plan(plan_file, lambda wb: wb["Summary"].insert_rows(1))
        assert read_plan(plan_file).source_hash == PLAN_HASH

    def test_default_path_is_next_to_the_source(self, tmp_path):
        assert default_plan_path(tmp_path / "Health-RI.xlsx") == tmp_path / "Health-RI-plan.xlsx"

    def test_edit_defaults(self):
        assert Edit(SET_CELL, "s").apply is True


class TestPlanCommand:
    def test_writes_the_plan_next_to_the_source(self, runner, source):
        before = sha(source)
        result = runner.invoke(plan_excel, ["-i", str(source)])
        assert result.exit_code == 0, result.output
        assert sha(source) == before
        assert default_plan_path(source).exists()
        assert "Plan written to" in result.output
        assert "Required cells to fill in" in result.output

    def test_refuses_to_replace_a_plan_without_overwrite(self, runner, source):
        assert runner.invoke(plan_excel, ["-i", str(source)]).exit_code == 0
        result = runner.invoke(plan_excel, ["-i", str(source)])
        assert result.exit_code == 1
        assert "--overwrite" in result.output
        assert runner.invoke(plan_excel, ["-i", str(source), "--overwrite"]).exit_code == 0

    def test_custom_output_path(self, runner, source, tmp_path):
        out = tmp_path / "elsewhere" / "p.xlsx"
        result = runner.invoke(plan_excel, ["-i", str(source), "-o", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists() and not default_plan_path(source).exists()

    def test_refuses_to_write_the_plan_over_the_source(self, runner, source):
        before = sha(source)
        result = runner.invoke(plan_excel, ["-i", str(source), "-o", str(source), "--overwrite"])
        assert result.exit_code == 1
        assert "must differ" in result.output
        assert sha(source) == before

    def test_nothing_to_plan_writes_nothing_and_names_the_issues(self, runner, prepared):
        fill_reported_gaps(prepared)
        prepare_workbook(prepared)
        result = runner.invoke(plan_excel, ["-i", str(prepared)])
        assert result.exit_code == 0, result.output
        assert "Nothing to plan" in result.output
        assert "issue(s) in the report above" in result.output
        assert not default_plan_path(prepared).exists()

    def test_a_plan_from_an_earlier_run_is_reported_as_outdated(self, runner, prepared):
        assert runner.invoke(plan_excel, ["-i", str(prepared)]).exit_code == 0
        fill_reported_gaps(prepared)
        prepare_workbook(prepared)
        result = runner.invoke(plan_excel, ["-i", str(prepared)])
        assert result.exit_code == 0, result.output
        assert "earlier run and no longer applies" in result.output
        assert default_plan_path(prepared).exists()

    def test_an_unreadable_input_fails(self, runner, tmp_path):
        broken = tmp_path / "broken.xlsx"
        broken.write_text("not a workbook")
        result = runner.invoke(plan_excel, ["-i", str(broken)])
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert not default_plan_path(broken).exists()

    def test_namespace_reaches_the_plan(self, runner, source):
        prepare_workbook(source)
        answer_classes(source, {k: v for k, v in CLASS_ANSWERS.items() if k != "Resource"}, class_uris=False)
        result = runner.invoke(plan_excel, ["-i", str(source), "-n", "ex"])
        assert result.exit_code == 0, result.output

        plan = read_plan(default_plan_path(source))
        assert plan.namespace == "ex"
        class_uris = {e.key: e.new for e in plan.edits if e.column == "class_URI"}
        assert class_uris["Catalog"] == "ex:Catalog"
