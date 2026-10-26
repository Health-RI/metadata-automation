"""Keep drawings (text boxes, shapes, images, charts), which openpyxl drops on save.

After openpyxl saves, each sheet's drawing and the parts it refers to are copied
from the source package into the output and linked to the sheet of the same name.
"""

import posixpath
import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_DRAWING_TYPE = f"{_REL_NS}/drawing"
_CONTENT_TYPES = "[Content_Types].xml"
# In openpyxl's sheet XML (default namespace, no extLst), only these follow <drawing>.
_AFTER_DRAWING = re.compile(rb"<(?:legacyDrawing|tableParts)[\s/>]|</worksheet>")
_HAS_DRAWING = re.compile(rb"<drawing[\s/>]")
# Drawing content openpyxl drops; it keeps charts (graphicFrame) itself.
_SHAPES = re.compile(rb"<(?:\w+:)?(?:sp|grpSp|cxnSp|pic)[\s>]")


def drawing_sheets(path: Path) -> list[str]:
    """Names of the sheets that contain a drawing."""
    files = _read(path)
    return [name for name, part in _sheet_parts(files).items() if _drawing_target(files, part)]


def restore_drawings(src: Path, dst: Path) -> list[str]:
    """Copy the drawings of ``src`` into ``dst`` by sheet name. Returns the sheets whose drawings could not be kept."""
    files = _read(src)
    out = _read(dst)
    out_sheets = _sheet_parts(out)
    copied: dict[str, str] = {}
    overrides: dict[str, str] = {}
    lost = []
    for name, part in _sheet_parts(files).items():
        drawing = _drawing_target(files, part)
        if not drawing:
            continue
        out_part = out_sheets.get(name)
        if out_part is None or _HAS_DRAWING.search(out[out_part]):
            if _SHAPES.search(files[drawing]):
                lost.append(name)
            continue
        new = _copy_part(files, out, drawing, copied, overrides)
        rel_id = _add_relation(out, out_part, _DRAWING_TYPE, _relative(out_part, new))
        out[out_part] = _insert_drawing(out[out_part], rel_id)
    if copied:
        out[_CONTENT_TYPES] = _add_overrides(out[_CONTENT_TYPES], overrides)
        _write(dst, out)
    return lost


def _read(path: Path) -> dict[str, bytes]:
    with ZipFile(path) as zf:
        return {name: zf.read(name) for name in zf.namelist()}


def _write(path: Path, files: dict[str, bytes]) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)


def _sheet_parts(files: dict[str, bytes]) -> dict[str, str]:
    """Sheet name to its worksheet part."""
    targets = _relations(files, "xl/workbook.xml")
    parts = {}
    for sheet in ElementTree.fromstring(files["xl/workbook.xml"]).iter(f"{_MAIN}sheet"):
        rel = targets.get(sheet.get(f"{{{_REL_NS}}}id"))
        if rel:
            parts[sheet.get("name")] = _resolve("xl/workbook.xml", rel[0])
    return parts


def _drawing_target(files: dict[str, bytes], part: str) -> str | None:
    return next((_resolve(part, t) for t, kind, _ in _relations(files, part).values() if kind == _DRAWING_TYPE), None)


def _relations(files: dict[str, bytes], part: str) -> dict[str, tuple[str, str, str | None]]:
    """Relationship id to (target, type, target mode) for ``part``."""
    rels = _rels_path(part)
    if rels not in files:
        return {}
    root = ElementTree.fromstring(files[rels])
    return {
        r.get("Id"): (r.get("Target"), r.get("Type"), r.get("TargetMode"))
        for r in root.iter(f"{{{_PKG_REL_NS}}}Relationship")
    }


def _rels_path(part: str) -> str:
    return posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")


def _resolve(base: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), target))


def _relative(base: str, part: str) -> str:
    return posixpath.relpath(part, posixpath.dirname(base))


def _copy_part(
    files: dict[str, bytes], out: dict[str, bytes], part: str, copied: dict[str, str], overrides: dict[str, str]
) -> str:
    """Copy ``part`` and every internal part it refers to, renaming on a clash. Returns the new name."""
    if part in copied:
        return copied[part]
    new = _free_name(out, part)
    copied[part] = new
    out[new] = files[part]
    overrides[new] = _content_type(files, part)
    rels = _rels_path(part)
    if rels in files:
        ElementTree.register_namespace("", _PKG_REL_NS)
        root = ElementTree.fromstring(files[rels])
        for rel in root.iter(f"{{{_PKG_REL_NS}}}Relationship"):
            if rel.get("TargetMode") != "External":
                target = _copy_part(files, out, _resolve(part, rel.get("Target")), copied, overrides)
                rel.set("Target", _relative(new, target))
        out[_rels_path(new)] = ElementTree.tostring(root, encoding="UTF-8", xml_declaration=True)
    return new


def _free_name(out: dict[str, bytes], part: str) -> str:
    if part not in out:
        return part
    stem, ext = posixpath.splitext(part)
    n = 1
    while f"{stem}_{n}{ext}" in out:
        n += 1
    return f"{stem}_{n}{ext}"


def _content_type(files: dict[str, bytes], part: str) -> str:
    root = ElementTree.fromstring(files[_CONTENT_TYPES])
    for override in root.iter(f"{{{_CT_NS}}}Override"):
        if override.get("PartName").lstrip("/") == part:
            return override.get("ContentType")
    ext = posixpath.splitext(part)[1].lstrip(".").lower()
    for default in root.iter(f"{{{_CT_NS}}}Default"):
        if default.get("Extension").lower() == ext:
            return default.get("ContentType")
    return "application/octet-stream"


def _add_overrides(content_types: bytes, overrides: dict[str, str]) -> bytes:
    ElementTree.register_namespace("", _CT_NS)
    root = ElementTree.fromstring(content_types)
    for part, content_type in overrides.items():
        ElementTree.SubElement(root, f"{{{_CT_NS}}}Override", PartName=f"/{part}", ContentType=content_type)
    return ElementTree.tostring(root, encoding="UTF-8", xml_declaration=True)


def _add_relation(out: dict[str, bytes], part: str, kind: str, target: str) -> str:
    """Add a relationship from ``part`` and return its id."""
    rels = _rels_path(part)
    ElementTree.register_namespace("", _PKG_REL_NS)
    if rels in out:
        root = ElementTree.fromstring(out[rels])
    else:
        root = ElementTree.Element(f"{{{_PKG_REL_NS}}}Relationships")
    ids = {r.get("Id") for r in root.iter(f"{{{_PKG_REL_NS}}}Relationship")}
    rel_id = next(f"rId{n}" for n in range(1, len(ids) + 2) if f"rId{n}" not in ids)
    ElementTree.SubElement(root, f"{{{_PKG_REL_NS}}}Relationship", Id=rel_id, Type=kind, Target=target)
    out[rels] = ElementTree.tostring(root, encoding="UTF-8", xml_declaration=True)
    return rel_id


def _insert_drawing(sheet: bytes, rel_id: str) -> bytes:
    """Insert ``<drawing>`` at its schema position in a sheet written by openpyxl."""
    element = f'<drawing xmlns:r="{_REL_NS}" r:id="{rel_id}"/>'.encode()
    match = _AFTER_DRAWING.search(sheet)
    return sheet[: match.start()] + element + sheet[match.start() :]
