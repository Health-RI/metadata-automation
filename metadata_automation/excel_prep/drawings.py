"""Keep drawings (text boxes, shapes, images, charts), which openpyxl drops on save.

After openpyxl saves, each sheet's drawing and the parts it refers to are copied
from the source package into the output and linked to the sheet of the same name.

Background: an .xlsx is a zip of XML "parts". Parts point at each other through
relationship files: ``dir/_rels/name.xml.rels`` lists the targets of ``dir/name.xml``
by id (``rId1``, ...). The chain for a sheet with a text box and a picture is:

    xl/workbook.xml          <sheet name="classes" r:id="rId3"/>
      -> xl/worksheets/sheet3.xml          <drawing r:id="rId1"/>
           -> xl/drawings/drawing1.xml     the shapes and their positions
                -> xl/media/image1.png     a picture used in the drawing

``[Content_Types].xml`` must declare the type of every part, or Excel refuses the file.

Restoring a drawing therefore means: copy the drawing part and everything it points
at (recursively), add a relationship from the output sheet to it, add ``<drawing>``
to the sheet XML, and declare the content types of the copied parts.
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
    # Both packages are held in memory as {part name: bytes}; ``out`` is edited and rewritten.
    files = _read(src)
    out = _read(dst)
    # Excel sheet names are unique regardless of case; the preparer may fix their case.
    out_sheets = {name.lower(): part for name, part in _sheet_parts(out).items()}
    # Source part to its name in ``out``, so a part shared by several drawings (e.g. one
    # image) is copied once.
    copied: dict[str, str] = {}
    # Content type of each copied part, added to [Content_Types].xml at the end.
    overrides: dict[str, str] = {}
    lost = []
    for name, part in _sheet_parts(files).items():
        drawing = _drawing_target(files, part)
        if not drawing:
            continue
        out_part = out_sheets.get(name.lower())
        # Skip a sheet that is gone from the output, or whose output already has a drawing:
        # openpyxl keeps charts, and a sheet has room for only one drawing. Only report it
        # when the source drawing holds shapes that are now lost (not just charts).
        if out_part is None or _HAS_DRAWING.search(out[out_part]):
            if _SHAPES.search(files[drawing]):
                lost.append(name)
            continue
        # 1. Copy the drawing and the parts it refers to, 2. point the sheet's .rels at it,
        # 3. reference that relationship from the sheet XML.
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
    # workbook.xml gives each sheet's name and relationship id; its .rels maps the id to a file.
    targets = _relations(files, "xl/workbook.xml")
    parts = {}
    for sheet in ElementTree.fromstring(files["xl/workbook.xml"]).iter(f"{_MAIN}sheet"):
        rel = targets.get(sheet.get(f"{{{_REL_NS}}}id"))
        if rel:
            parts[sheet.get("name")] = _resolve("xl/workbook.xml", rel[0])
    return parts


def _drawing_target(files: dict[str, bytes], part: str) -> str | None:
    """The drawing part a sheet refers to, if any."""
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
    """Relationship file of ``part``: ``a/b.xml`` -> ``a/_rels/b.xml.rels``."""
    return posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")


def _resolve(base: str, target: str) -> str:
    """Part name of a relationship target, which is relative to ``base``'s folder or absolute."""
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), target))


def _relative(base: str, part: str) -> str:
    """Inverse of ``_resolve``: ``part`` as a target relative to ``base``'s folder."""
    return posixpath.relpath(part, posixpath.dirname(base))


def _copy_part(
    files: dict[str, bytes], out: dict[str, bytes], part: str, copied: dict[str, str], overrides: dict[str, str]
) -> str:
    """Copy ``part`` and every internal part it refers to, renaming on a clash. Returns the new name."""
    if part in copied:
        return copied[part]
    # openpyxl may have written its own part under the same name (e.g. drawing1.xml for a chart).
    new = _free_name(out, part)
    copied[part] = new
    out[new] = files[part]
    overrides[new] = _content_type(files, part)
    # Copy what this part refers to as well, and rewrite its .rels to the new names.
    # Relationship ids are kept, so the part's own XML needs no change.
    rels = _rels_path(part)
    if rels in files:
        ElementTree.register_namespace("", _PKG_REL_NS)
        root = ElementTree.fromstring(files[rels])
        for rel in root.iter(f"{{{_PKG_REL_NS}}}Relationship"):
            # External targets (e.g. hyperlinks) are URLs, not parts in the zip.
            if rel.get("TargetMode") != "External":
                target = _copy_part(files, out, _resolve(part, rel.get("Target")), copied, overrides)
                rel.set("Target", _relative(new, target))
        out[_rels_path(new)] = ElementTree.tostring(root, encoding="UTF-8", xml_declaration=True)
    return new


def _free_name(out: dict[str, bytes], part: str) -> str:
    """``part``, or ``stem_N.ext`` with the lowest N not yet in ``out``."""
    if part not in out:
        return part
    stem, ext = posixpath.splitext(part)
    n = 1
    while f"{stem}_{n}{ext}" in out:
        n += 1
    return f"{stem}_{n}{ext}"


def _content_type(files: dict[str, bytes], part: str) -> str:
    """Content type of ``part``: its Override by part name, else the Default for its extension."""
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
    """Declare the content type of each copied part by name, so it holds whatever the Defaults say."""
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
    # Pick the lowest rIdN not in use.
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
