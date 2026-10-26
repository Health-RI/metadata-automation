"""Detect drawings (text boxes, shapes, images, charts), which openpyxl does not keep on save."""

import posixpath
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def drawing_sheets(path: Path) -> list[str]:
    """Names of the sheets that contain a drawing."""
    with ZipFile(path) as zf:
        names = set(zf.namelist())
        targets = _relations(zf, "xl/_rels/workbook.xml.rels")
        sheets = []
        for sheet in ElementTree.fromstring(zf.read("xl/workbook.xml")).iter(f"{_MAIN}sheet"):
            target = targets.get(sheet.get(f"{_REL}id"), ("", ""))[0]
            part = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
            rels = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
            if rels in names and any(t.endswith("/drawing") for _, t in _relations(zf, rels).values()):
                sheets.append(sheet.get("name"))
        return sheets


def _relations(zf: ZipFile, rels: str) -> dict[str, tuple[str, str]]:
    """Relationship id to (target, type)."""
    root = ElementTree.fromstring(zf.read(rels))
    return {r.get("Id"): (r.get("Target"), r.get("Type")) for r in root.iter(f"{_PKG_REL}Relationship")}
