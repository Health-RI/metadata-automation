"""Inspect inheritance overlap in generated SeMPyRO Pydantic classes.

Parses Python source files statically via AST — no imports are executed.
This means the tool works even when the dependencies of the generated files
(e.g. the ``sempyro`` package) are not installed in the current environment.

Ancestor classes are resolved by:
1. Searching ``search_dirs`` (files in the same directory by default).
2. Falling back to locating the source file via ``importlib.util.find_spec``
   when the package containing the ancestor is installed.
"""

import ast
import importlib.util
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import Any

# Class names at which ancestor traversal stops.
_STOP_CLASS_NAMES = frozenset({"RDFModel", "BaseModel", "object"})

# Legacy/generated base-class names that do not match the actual imported symbol.
_LEGACY_BASE_CLASS_ALIASES = {
    "FOAFAgent": "Agent",
    "VCARDKind": "VCard",
    "DCATDataservice": "DCATDataService",
    "DCATDatasetseries": "DCATDatasetSeries",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FieldMeta:
    """Metadata for a single Pydantic field, extracted from AST."""

    description: str = ""
    rdf_term: str = ""
    rdf_type: str = ""


@dataclass
class ClassInfo:
    """Information about a Python class, extracted via AST."""

    class_name: str
    bases: list[str]
    import_map: dict[str, str]  # name → module path (from ``from X import Y``)
    own_fields: dict[str, FieldMeta] = dataclass_field(default_factory=dict)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _ast_get_name(node: ast.expr) -> str:
    """Return the identifier string from a Name or Attribute AST node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _extract_description(kw: ast.keyword) -> str:
    """Extract a description string from a ``description=`` keyword argument."""
    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
        return kw.value.value.strip()
    return ""


def _extract_json_schema_extra(kw: ast.keyword) -> tuple[str, str]:
    """Extract rdf_term and rdf_type from a ``json_schema_extra=`` keyword argument."""
    rdf_term = rdf_type = ""
    if not isinstance(kw.value, ast.Dict):
        return rdf_term, rdf_type
    for k, v in zip(kw.value.keys, kw.value.values, strict=False):
        if not isinstance(k, ast.Constant):
            continue
        if k.value == "rdf_term":
            rdf_term = ast.unparse(v)
        elif k.value == "rdf_type":
            rdf_type = v.value if isinstance(v, ast.Constant) else ast.unparse(v)
    return rdf_term, rdf_type


def _ast_extract_field_meta(call_node: ast.Call) -> FieldMeta:
    """Extract FieldMeta from the keyword arguments of a ``Field(...)`` call."""
    description = rdf_term = rdf_type = ""
    for kw in call_node.keywords:
        if kw.arg == "description":
            description = _extract_description(kw)
        elif kw.arg == "json_schema_extra":
            rdf_term, rdf_type = _extract_json_schema_extra(kw)
    return FieldMeta(description=description, rdf_term=rdf_term, rdf_type=rdf_type)


# ---------------------------------------------------------------------------
# Source parsing
# ---------------------------------------------------------------------------


def parse_class_from_source(
    source: str,
    target_class: str | None = None,
) -> ClassInfo | None:
    """Parse Python source code and return ClassInfo for a class.

    Args:
        source: Full Python source code as a string.
        target_class: If given, return info only for this class name.
            Otherwise returns the first class definition found.

    Returns:
        A :class:`ClassInfo`, or ``None`` if no matching class is found or
        the source cannot be parsed.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    # Build import_map: imported_name → module_path
    import_map: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                import_map[name] = node.module

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if target_class and node.name != target_class:
            continue

        bases = [_ast_get_name(b) for b in node.bases if _ast_get_name(b)]
        own_fields: dict[str, FieldMeta] = {}

        for stmt in node.body:
            if (
                isinstance(stmt, ast.AnnAssign)
                and isinstance(stmt.target, ast.Name)
                and stmt.value
                and isinstance(stmt.value, ast.Call)
                and _ast_get_name(stmt.value.func) == "Field"
            ):
                own_fields[stmt.target.id] = _ast_extract_field_meta(stmt.value)

        return ClassInfo(
            class_name=node.name,
            bases=bases,
            import_map=import_map,
            own_fields=own_fields,
        )

    return None


# ---------------------------------------------------------------------------
# Ancestor resolution
# ---------------------------------------------------------------------------


def _find_in_dirs(class_name: str, search_dirs: list[Path]) -> ClassInfo | None:
    """Search directories for a ``.py`` file that defines *class_name*."""
    for directory in search_dirs:
        for py_file in sorted(directory.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            info = parse_class_from_source(source, class_name)
            if info is not None:
                return info
    return None


def _find_in_package(class_name: str, module_path: str) -> ClassInfo | None:
    """Locate a class's source file via ``importlib`` and parse it with AST.

    When *module_path* resolves to a package ``__init__.py`` (i.e. the class
    is re-exported from the package rather than defined there), all ``.py``
    files under the package directory are scanned until the class definition
    is found.

    This does **not** execute the module; it only finds the file on disk.
    Returns ``None`` if the package is not installed or the file cannot be read.
    """
    try:
        spec = importlib.util.find_spec(module_path)
    except (ModuleNotFoundError, ValueError):
        return None
    if spec is None or spec.origin is None:
        return None
    try:
        source = Path(spec.origin).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    info = parse_class_from_source(source, class_name)
    if info is not None:
        return info
    # The spec points to a package __init__.py that re-exports the class but
    # doesn't contain its body.  Scan all .py files in the package tree.
    if Path(spec.origin).name == "__init__.py" and spec.submodule_search_locations:
        for search_location in spec.submodule_search_locations:
            for py_file in sorted(Path(search_location).rglob("*.py")):
                if py_file.name == "__init__.py":
                    continue
                try:
                    sub_source = py_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                info = parse_class_from_source(sub_source, class_name)
                if info is not None:
                    return info
    return None


def _normalize_identifier(name: str) -> str:
    """Normalize a Python identifier for loose matching."""
    return "".join(char for char in name.lower() if char.isalnum())


def _resolve_imported_class_name(class_name: str, import_map: dict[str, str]) -> str:
    """Resolve *class_name* to the actual imported symbol name when possible.

    Generated HRI files may reference legacy/synthetic parent names such as
    ``DCATDataservice`` or ``FOAFAgent`` while importing the real classes as
    ``DCATDataService`` and ``Agent``. This helper maps those names back to the
    imported symbol used in the file.
    """
    if class_name in import_map:
        return class_name

    alias_name = _LEGACY_BASE_CLASS_ALIASES.get(class_name)
    if alias_name and alias_name in import_map:
        return alias_name

    normalized_target = _normalize_identifier(class_name)
    normalized_matches = [
        imported_name for imported_name in import_map if _normalize_identifier(imported_name) == normalized_target
    ]
    if len(normalized_matches) == 1:
        return normalized_matches[0]

    return class_name


def _resolve_ancestor(
    class_name: str,
    import_map: dict[str, str],
    search_dirs: list[Path],
) -> ClassInfo | None:
    """Try to locate and parse the source of *class_name*.

    Resolution order:
    1. Search *search_dirs* for a file defining the class.
    2. Use ``importlib.util.find_spec`` on the module listed in *import_map*.
    """
    resolved_class_name = _resolve_imported_class_name(class_name, import_map)

    info = _find_in_dirs(class_name, search_dirs)
    if info is None and resolved_class_name != class_name:
        info = _find_in_dirs(resolved_class_name, search_dirs)
    if info is not None:
        return info
    module_path = import_map.get(resolved_class_name)
    if module_path:
        return _find_in_package(resolved_class_name, module_path)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compare_field_infos(
    child_info: FieldMeta,
    parent_info: FieldMeta,
) -> dict[str, dict[str, Any]]:
    """Compare two :class:`FieldMeta` objects attribute by attribute.

    Compares ``description``, ``rdf_term``, and ``rdf_type``.

    Args:
        child_info: Field metadata from the subclass.
        parent_info: Field metadata from the ancestor class.

    Returns:
        Dict with keys ``description``, ``rdf_term``, ``rdf_type``.
        Each value has keys ``same`` (bool), ``child`` (str), ``parent`` (str).
    """

    def _cmp(a: str, b: str) -> dict[str, Any]:
        return {"same": a == b, "child": a, "parent": b}

    return {
        "description": _cmp(child_info.description, parent_info.description),
        "rdf_term": _cmp(child_info.rdf_term, parent_info.rdf_term),
        "rdf_type": _cmp(child_info.rdf_type, parent_info.rdf_type),
    }


def inspect_file(
    file_path: Path,
    search_dirs: list[Path] | None = None,
) -> dict[str, Any]:
    """Inspect a generated SeMPyRO file for fields that overlap with ancestors.

    Parses the file with AST (no import/execution), then walks the ancestor
    chain by resolving each parent class's source file in turn.

    Args:
        file_path: Path to a generated ``.py`` SeMPyRO file.
        search_dirs: Extra directories to search for ancestor source files.
            The directory of *file_path* is always included.

    Returns:
        Dict with keys:
        ``class_name``, ``file_path``, ``ancestor_chain``,
        ``total_direct_fields``, ``overlapping``, ``error``.
    """
    result: dict[str, Any] = {
        "class_name": None,
        "file_path": file_path,
        "ancestor_chain": [],
        "total_direct_fields": 0,
        "overlapping": [],
        "error": None,
    }

    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        result["error"] = str(exc)
        return result

    child_info = parse_class_from_source(source)
    if child_info is None:
        result["error"] = f"No class definition found in {file_path.name}"
        return result

    result["class_name"] = child_info.class_name
    result["total_direct_fields"] = len(child_info.own_fields)

    all_search_dirs: list[Path] = [file_path.parent]
    if search_dirs:
        all_search_dirs.extend(d for d in search_dirs if d != file_path.parent)

    unmatched: set[str] = set(child_info.own_fields)
    current: ClassInfo = child_info
    level = 0

    while current.bases and unmatched:
        parent_name = current.bases[0]
        if parent_name in _STOP_CLASS_NAMES:
            break

        level += 1
        parent_info = _resolve_ancestor(parent_name, current.import_map, all_search_dirs)

        if parent_info is None:
            result["ancestor_chain"].append((level, f"{parent_name} [source unavailable]"))
            break

        result["ancestor_chain"].append((level, parent_info.class_name))

        # --- exact name match ---
        for field_name in list(unmatched):
            if field_name in parent_info.own_fields:
                comparison = compare_field_infos(
                    child_info.own_fields[field_name],
                    parent_info.own_fields[field_name],
                )
                identical = all(v["same"] for v in comparison.values())
                result["overlapping"].append(
                    {
                        "field_name": field_name,
                        "parent_field_name": field_name,
                        "matched_by": "name",
                        "found_in": parent_info.class_name,
                        "found_at_level": level,
                        "comparison": comparison,
                        "identical": identical,
                    }
                )
                unmatched.discard(field_name)

        # --- rdf_term-based semantic match (renamed fields) ---
        # Build a reverse map: rdf_term_expression → (parent_field_name, FieldMeta)
        parent_rdf_term_index: dict[str, tuple[str, FieldMeta]] = {
            pf_meta.rdf_term: (pf_name, pf_meta)
            for pf_name, pf_meta in parent_info.own_fields.items()
            if pf_meta.rdf_term
        }
        for field_name in list(unmatched):
            child_meta = child_info.own_fields[field_name]
            if not child_meta.rdf_term:
                continue
            match = parent_rdf_term_index.get(child_meta.rdf_term)
            if match is None:
                continue
            parent_field_name, parent_meta = match
            comparison = compare_field_infos(child_meta, parent_meta)
            # Field names differ, so this can never be trivially "identical"
            result["overlapping"].append(
                {
                    "field_name": field_name,
                    "parent_field_name": parent_field_name,
                    "matched_by": "rdf_term",
                    "found_in": parent_info.class_name,
                    "found_at_level": level,
                    "comparison": comparison,
                    "identical": False,
                }
            )
            unmatched.discard(field_name)

        current = parent_info

    return result


def format_report(results: list[dict[str, Any]]) -> str:
    """Render a human-readable overlap report for one or more classes.

    Args:
        results: List of dicts as returned by :func:`inspect_file`.

    Returns:
        Formatted plain-text report string.
    """
    lines: list[str] = []

    for result in results:
        lines.append("=" * 80)

        if result["error"]:
            lines.append(f"ERROR – {result['file_path'].name}: {result['error']}")
            lines.append("")
            continue

        class_name = result["class_name"]
        chain_names = " → ".join(name for _, name in result["ancestor_chain"])
        header = class_name
        if chain_names:
            header += f"  (inherits from: {chain_names})"
        lines.append(header)
        lines.append("")

        overlapping = result["overlapping"]
        total = result["total_direct_fields"]
        overlap_count = len(overlapping)

        if overlap_count == 0:
            lines.append(f"  No overlapping properties found ({total} direct fields, none redefined from ancestors).")
            lines.append("")
            continue

        identical_count = sum(1 for o in overlapping if o["identical"])
        different_count = overlap_count - identical_count

        lines.append(
            f"  Overlapping properties: {overlap_count} of {total} direct fields are also defined in an ancestor class"
        )
        lines.append("")

        for overlap in overlapping:
            field_name = overlap["field_name"]
            parent_field_name = overlap.get("parent_field_name", field_name)
            matched_by = overlap.get("matched_by", "name")
            found_in = overlap["found_in"]
            level = overlap["found_at_level"]
            level_label = "level" if level == 1 else "levels"
            if matched_by == "rdf_term":
                lines.append(f"  {field_name}  →  {parent_field_name}  (matched by rdf_term)")
            else:
                lines.append(f"  {field_name}")
            lines.append(f"    found in    : {found_in}  ({level} {level_label} up)")

            comparison = overlap["comparison"]
            for attr, values in comparison.items():
                label = f"{attr:<11}"
                if values["same"]:
                    lines.append(f"    {label} : SAME    → {values['child']}")
                else:
                    lines.append(f"    {label} : DIFFERENT")
                    lines.append(f"                   child  : {values['child']}")
                    lines.append(f"                   parent : {values['parent']}")

            verdict = "[IDENTICAL – can be removed]" if overlap["identical"] else "[DIFFERS – review before removing]"
            lines.append(f"    {verdict}")
            lines.append("")

        lines.append(f"  Summary: {identical_count} identical, {different_count} different")
        lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)
