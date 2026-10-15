"""Init run: in-place update without the FDP rules."""

import shutil

import pytest
from openpyxl import load_workbook
from prep_helpers import CLASS_ANSWERS, answer_classes, cell, find_row, sha

from metadata_automation.excel_prep.columns import CLASS_SHEET_COLUMNS
from metadata_automation.excel_prep.preparer import prepare_workbook
from metadata_automation.excel_prep.report import Cell
from metadata_automation.excel_prep.workbook import class_sheet_names, headers


class TestInit:
    @pytest.fixture
    def plain_copy(self, plain_small, tmp_path):
        path = tmp_path / "plain.xlsx"
        shutil.copy(plain_small, path)
        return path

    @pytest.fixture
    def answered(self, plain_copy):
        """An init output with the class questions answered, so every rule could apply."""
        prepare_workbook(plain_copy, init=True)
        answer_classes(plain_copy, {k: v for k, v in CLASS_ANSWERS.items() if k != "Resource"})
        return plain_copy

    def test_updates_in_place_without_fdp_sheets(self, plain_copy):
        before = sha(plain_copy)
        report = prepare_workbook(plain_copy, init=True)
        assert sha(plain_copy) != before
        wb = load_workbook(plain_copy)
        assert wb.sheetnames[:3] == ["Info", "prefixes", "classes"]
        assert "Resource" not in wb.sheetnames
        for name in class_sheet_names(wb):
            assert set(CLASS_SHEET_COLUMNS) <= set(headers(wb[name]))
        assert any(c.cell.sheet == "prefixes" for c in report.changes)
        assert report.prefix_issues

    def test_rejects_output_path(self, plain_copy, tmp_path):
        with pytest.raises(ValueError, match="in place"):
            prepare_workbook(plain_copy, tmp_path / "out.xlsx", init=True)

    def test_model_range_gets_node_shape_only(self, answered):
        report = prepare_workbook(answered, init=True)
        ws = load_workbook(answered)["Catalog"]
        row = find_row(ws, "Property URI", "dcat:dataset")
        assert cell(ws, row, "Range") == "dcat:Dataset"
        assert cell(ws, row, "Cardinality") == "1..n"
        assert cell(ws, row, "SHACL_sh:node") == "hri:DatasetShape"
        assert cell(ws, row, "SHACL_dash:viewer") == "dash:DetailsViewer"
        assert not any(f.cell.column in ("Range", "Cardinality") for f in report.changes)

    def test_out_of_model_range_is_flagged_not_changed(self, answered):
        report = prepare_workbook(answered, init=True)
        ws = load_workbook(answered)["Catalog"]
        row = find_row(ws, "Property URI", "dct:license")
        assert cell(ws, row, "Range") == "dct:LicenseDocument"
        assert any(
            f.cell == Cell("Catalog", row, "Range")
            and f.message == "'dct:LicenseDocument' is not a class of this model"
            for f in report.issues
        )

    def test_no_title_check(self, answered):
        wb = load_workbook(answered)
        ws = wb["Catalog"]
        ws.delete_rows(find_row(ws, "Property URI", "dct:title"))
        wb.save(answered)
        report = prepare_workbook(answered, init=True)
        assert not any("dct:title" in f.message for f in report.issues)
