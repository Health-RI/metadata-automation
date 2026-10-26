"""Writing the result without losing the source or an existing output."""

import os
import shutil
from zipfile import ZipFile

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from prep_helpers import sha

from metadata_automation.excel_prep.drawings import drawing_sheets
from metadata_automation.excel_prep.preparer import prepare_workbook
from metadata_automation.excel_prep.report import Cell

DRAWING_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing"


@pytest.fixture
def plain_copy(plain_small, tmp_path):
    path = tmp_path / "plain.xlsx"
    shutil.copy(plain_small, path)
    return path


def add_drawing(path, sheet_index):
    """Attach an empty drawing to the sheet at ``sheet_index``, as a text box would."""
    tmp = path.with_suffix(".tmp")
    with ZipFile(path) as src, ZipFile(tmp, "w") as dst:
        for item in src.infolist():
            dst.writestr(item, src.read(item))
        dst.writestr(
            f"xl/worksheets/_rels/sheet{sheet_index}.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{DRAWING_REL}" Target="../drawings/drawing1.xml"/></Relationships>',
        )
        dst.writestr(
            "xl/drawings/drawing1.xml",
            '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"/>',
        )
    os.replace(tmp, path)


def test_existing_output_is_refused(plain_small, tmp_path):
    out = tmp_path / "out.xlsx"
    out.write_bytes(b"keep")
    with pytest.raises(ValueError, match="--overwrite"):
        prepare_workbook(plain_small, out)
    assert out.read_bytes() == b"keep"


def test_overwrite_replaces_existing_output(plain_small, tmp_path):
    out = tmp_path / "out.xlsx"
    out.write_bytes(b"old")
    prepare_workbook(plain_small, out, overwrite=True)
    assert "classes" in load_workbook(out).sheetnames


def test_same_file_by_other_path_is_refused(plain_copy, tmp_path):
    link = tmp_path / "link.xlsx"
    os.link(plain_copy, link)
    before = sha(plain_copy)
    with pytest.raises(ValueError, match="must differ"):
        prepare_workbook(plain_copy, link, overwrite=True)
    assert sha(plain_copy) == before


def test_failed_save_leaves_source_intact(plain_copy, monkeypatch):
    def fail(self, filename):
        open(filename, "wb").write(b"partial")
        raise OSError("disk full")

    before = sha(plain_copy)
    monkeypatch.setattr(Workbook, "save", fail)
    with pytest.raises(OSError):
        prepare_workbook(plain_copy, init=True)
    assert sha(plain_copy) == before
    assert {p.name for p in plain_copy.parent.iterdir()} == {plain_copy.name}


def test_drawing_sheets(plain_copy):
    add_drawing(plain_copy, 1)
    assert drawing_sheets(plain_copy) == [load_workbook(plain_copy).sheetnames[0]]


def test_init_backs_up_source_with_drawings(plain_copy):
    add_drawing(plain_copy, 1)
    sheet = load_workbook(plain_copy).sheetnames[0]
    before = sha(plain_copy)
    report = prepare_workbook(plain_copy, init=True)
    backup = plain_copy.with_name("plain.xlsx.bak")
    assert sha(backup) == before
    assert any(f.cell == Cell(sheet) and "plain.xlsx.bak" in f.message for f in report.issues)


def test_full_run_reports_drawings_without_backup(plain_copy, tmp_path):
    add_drawing(plain_copy, 1)
    report = prepare_workbook(plain_copy, tmp_path / "out.xlsx")
    assert any("not copied to the output" in f.message for f in report.issues)
    assert not plain_copy.with_name("plain.xlsx.bak").exists()


def test_rich_text_is_kept(plain_copy):
    wb = load_workbook(plain_copy)
    rich = CellRichText(["plain ", TextBlock(InlineFont(b=True), "bold")])
    wb["Info"]["A10"] = rich
    wb.save(plain_copy)

    prepare_workbook(plain_copy, init=True)
    value = load_workbook(plain_copy, rich_text=True)["Info"]["A10"].value
    assert isinstance(value, CellRichText)
    assert str(value) == "plain bold"
