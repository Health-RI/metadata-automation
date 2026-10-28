"""Derive the supporting inputs of the ``sempyro`` command from the model itself.

- The LinkML types file is derived from the ``SeMPyRO_range`` values in the Excel file.
- The per-class imports are derived from a first, import-less generation pass: the symbols the generated code
  references are collected with AST (the code is never imported or executed) and resolved against the installed
  ``sempyro`` package, which is also read statically.

Hand-maintained entries take precedence over derived ones, see :func:`merge_types` and :func:`merge_imports`.
"""

import ast
import builtins
import importlib
import importlib.util
import sys
import textwrap
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd
import yaml

from metadata_automation.sempyro.inheritance_inspector import _LEGACY_BASE_CLASS_ALIASES
from metadata_automation.sempyro.utils import parse_import_statements

RANGE_COLUMN = "SeMPyRO_range"

DEFAULT_TYPES_HEADER: Dict[str, Any] = {
    "id": "https://example.org/my-project/types",
    "name": "my-project-types",
    "title": "My Project Types",
    "description": "Common types for my project",
    "prefixes": {
        "linkml": "https://w3id.org/linkml/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    },
    "default_prefix": "my-project-types",
    "default_range": "string",
}

# URI per type that is not a class: anything else is a class or URL type and gets xsd:anyURI.
TYPE_URIS = {
    "str": "xsd:string",
    "int": "xsd:int",
    "float": "xsd:float",
    "bool": "xsd:boolean",
    "date": "xsd:date",
    "datetime": "xsd:dateTime",
    "LiteralField": "rdfs:Literal",
}
DEFAULT_TYPE_URI = "xsd:anyURI"

# Modules searched, in this order, for symbols that are not part of ``sempyro``.
_EXTERNAL_MODULES = ("typing", "datetime", "abc", "enum", "pydantic")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


def collect_range_types(sheets: Dict[str, pd.DataFrame], class_table: pd.DataFrame) -> Dict[str, List[str]]:
    """Collect every type used in a ``SeMPyRO_range`` cell.

    Args:
        sheets: All sheets of the Excel file by name (as read with ``dtype=str``).
        class_table: The ``classes`` sheet.

    Returns:
        Type name -> sorted sheet names it is used in.
    """
    used_in: Dict[str, Set[str]] = defaultdict(set)
    for sheet_name in class_table["sheet_name"]:
        sheet = sheets.get(sheet_name)
        if sheet is None or RANGE_COLUMN not in sheet.columns:
            continue
        for label, cell in zip(sheet["Property label"], sheet[RANGE_COLUMN], strict=False):
            if label == "nan" or pd.isna(cell):
                continue
            for type_name in str(cell).split(","):
                type_name = type_name.strip()
                if type_name and type_name != "nan":
                    used_in[type_name].add(sheet_name)
    return {name: sorted(sheet_names) for name, sheet_names in sorted(used_in.items())}


def derive_types(type_names: Iterable[str]) -> Dict[str, Dict[str, str]]:
    """Build a LinkML ``types`` entry per type name."""
    return {
        name: {
            "uri": TYPE_URIS.get(name, DEFAULT_TYPE_URI),
            "base": name,
            "description": f"{name} (derived from {RANGE_COLUMN})",
        }
        for name in sorted(type_names)
    }


def merge_types(derived: Dict[str, Dict[str, str]], hand_maintained: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine derived types with a hand-maintained types file; hand-maintained entries win.

    Every hand-maintained type is kept, also when it is not used in a range.
    """
    schema = dict(hand_maintained) if hand_maintained else dict(DEFAULT_TYPES_HEADER)
    hand_types = dict(schema.get("types") or {})
    schema["types"] = {**{n: t for n, t in derived.items() if n not in hand_types}, **hand_types}
    return schema


# ---------------------------------------------------------------------------
# Symbol collection
# ---------------------------------------------------------------------------


class _FreeNameCollector(ast.NodeVisitor):
    """Collect names that are loaded but never bound, in statement order, without executing anything."""

    def __init__(self) -> None:
        self.free: Set[str] = set()
        self._scopes: List[Set[str]] = [set()]

    def _bound(self, name: str) -> bool:
        return name in dir(builtins) or any(name in scope for scope in self._scopes)

    def _bind(self, name: str) -> None:
        self._scopes[-1].add(name)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if not self._bound(node.id):
                self.free.add(node.id)
        else:
            self._bind(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._bind(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self._bind(alias.asname or alias.name)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self.visit(target)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        # The annotation is evaluated before the target is bound: ``date: date = ...`` references the type.
        self.visit(node.annotation)
        if node.value is not None:
            self.visit(node.value)
        self.visit(node.target)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        self.visit(node.target)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self.visit(node.target)
        for stmt in node.body + node.orelse:
            self.visit(stmt)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is not None:
            self.visit(node.type)
        if node.name:
            self._bind(node.name)
        for stmt in node.body:
            self.visit(stmt)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for expr in [*node.decorator_list, *node.bases, *[k.value for k in node.keywords]]:
            self.visit(expr)
        self._scopes.append(set())
        for stmt in node.body:
            self.visit(stmt)
        self._scopes.pop()
        self._bind(node.name)

    def _visit_function(self, node: Any) -> None:
        args = node.args
        for expr in node.decorator_list:
            self.visit(expr)
        for default in [*args.defaults, *[d for d in args.kw_defaults if d is not None]]:
            self.visit(default)
        all_args = [*args.posonlyargs, *args.args, *args.kwonlyargs, *[a for a in (args.vararg, args.kwarg) if a]]
        for arg in all_args:
            if arg.annotation is not None:
                self.visit(arg.annotation)
        if node.returns is not None:
            self.visit(node.returns)
        self._bind(node.name)
        self._scopes.append({arg.arg for arg in all_args})
        for stmt in node.body:
            self.visit(stmt)
        self._scopes.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Lambda(self, node: ast.Lambda) -> None:
        args = node.args
        for default in [*args.defaults, *[d for d in args.kw_defaults if d is not None]]:
            self.visit(default)
        names = {
            a.arg
            for a in [*args.posonlyargs, *args.args, *args.kwonlyargs, *[x for x in (args.vararg, args.kwarg) if x]]
        }
        self._scopes.append(names)
        self.visit(node.body)
        self._scopes.pop()

    def _visit_comprehension(self, node: Any) -> None:
        self._scopes.append(set())
        for generator in node.generators:
            self.visit(generator.iter)
            self.visit(generator.target)
            for condition in generator.ifs:
                self.visit(condition)
        for expr in [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]:
            self.visit(expr)
        self._scopes.pop()

    visit_ListComp = visit_SetComp = visit_GeneratorExp = visit_DictComp = _visit_comprehension


def collect_symbols(source: str) -> Set[str]:
    """Return the names a piece of Python source references but does not define or import itself.

    The source is parsed, never imported or executed. Built-ins are not returned.

    Raises:
        SyntaxError: If the source cannot be parsed.
    """
    collector = _FreeNameCollector()
    collector.visit(ast.parse(source))
    return collector.free


# ---------------------------------------------------------------------------
# Symbol resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedSymbol:
    """Where a symbol is imported from: ``from module import name [as alias]`` or ``import module``."""

    module: str
    name: Optional[str] = None
    alias: Optional[str] = None


class SempyroIndex:
    """Static index of the names ``sempyro`` modules expose, built by parsing the installed source.

    A name is exposed by the module that defines it (class, function or assigned name) and by a package
    ``__init__`` that re-exports it from inside the package. No ``sempyro`` module is imported.
    """

    def __init__(self, package: str = "sempyro") -> None:
        self.package = package
        self.modules_by_name: Dict[str, Set[str]] = defaultdict(set)
        spec = importlib.util.find_spec(package)
        self.available = bool(spec and spec.submodule_search_locations)
        if self.available:
            self._index(Path(next(iter(spec.submodule_search_locations))))

    def _index(self, root: Path) -> None:
        for path in sorted(root.rglob("*.py")):
            parts = list(path.relative_to(root).with_suffix("").parts)
            if "tests" in parts or "test" in parts:
                continue
            is_init = parts[-1] == "__init__"
            module = ".".join([self.package, *(parts[:-1] if is_init else parts)])
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in tree.body:
                for name in self._exposed_names(node, is_init):
                    if not name.startswith("_"):
                        self.modules_by_name[name].add(module)

    def _exposed_names(self, node: ast.stmt, is_init: bool) -> List[str]:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            return [node.name]
        if isinstance(node, ast.Assign):
            return [t.id for t in node.targets if isinstance(t, ast.Name)]
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            return [node.target.id]
        if is_init and isinstance(node, ast.ImportFrom):
            internal = node.level > 0 or (node.module or "").split(".")[0] == self.package
            return [a.asname or a.name for a in node.names] if internal else []
        return []

    def lookup(self, name: str) -> Tuple[Optional[str], Optional[str]]:
        """Return ``(module, None)`` for the shortest module path exposing ``name``.

        ``(None, reason)`` if the name is unknown or several modules at the same depth expose it.
        """
        modules = self.modules_by_name.get(name)
        if not modules:
            return None, "not found in the installed sempyro package"
        shortest = min(m.count(".") for m in modules)
        best = sorted(m for m in modules if m.count(".") == shortest)
        if len(best) > 1:
            return None, f"ambiguous: exposed by {', '.join(best)}"
        return best[0], None

    def lookup_case_insensitive(self, name: str) -> Optional[str]:
        """Return the one exposed name that equals ``name`` ignoring case, if there is exactly one."""
        matches = [n for n in self.modules_by_name if n.lower() == name.lower()]
        return matches[0] if len(matches) == 1 else None


class SymbolResolver:
    """Resolve symbols referenced by generated code to the import that provides them."""

    def __init__(self, index: Optional[SempyroIndex] = None) -> None:
        self.index = index if index is not None else SempyroIndex()
        self._external: List[Any] = []
        for module_name in _EXTERNAL_MODULES:
            self._external.append(importlib.import_module(module_name))
        # Namespaces are imported from rdflib.namespace, anything else from rdflib itself.
        self._rdflib_namespace = self._optional_import("rdflib.namespace")
        self._rdflib = self._optional_import("rdflib")

    @staticmethod
    def _optional_import(name: str) -> Any:
        try:
            return importlib.import_module(name)
        except ImportError:
            return None

    def _resolve_external(self, name: str) -> Optional[ResolvedSymbol]:
        for module in self._external:
            if hasattr(module, name):
                return ResolvedSymbol(module.__name__, name)
        if name in sys.stdlib_module_names:
            return ResolvedSymbol(name)
        if self._rdflib_namespace is not None and name in getattr(self._rdflib_namespace, "__all__", ()):
            return ResolvedSymbol("rdflib.namespace", name)
        if self._rdflib is not None and hasattr(self._rdflib, name):
            return ResolvedSymbol("rdflib", name)
        return None

    def resolve(self, symbol: str) -> Tuple[Optional[ResolvedSymbol], Optional[str]]:
        """Resolve one symbol.

        Returns:
            ``(resolved, None)``, or ``(None, reason)`` when it cannot be resolved.
            A symbol known under a different name (e.g. the generated base class name ``FOAFAgent`` for
            ``sempyro.foaf.Agent``) resolves to an aliased import.
        """
        external = self._resolve_external(symbol)
        if external:
            return external, None
        module, reason = self.index.lookup(symbol)
        if module:
            return ResolvedSymbol(module, symbol), None
        if reason and reason.startswith("ambiguous"):
            return None, reason
        actual = _LEGACY_BASE_CLASS_ALIASES.get(symbol) or self.index.lookup_case_insensitive(symbol)
        if actual and actual != symbol:
            module, _ = self.index.lookup(actual)
            if module:
                return ResolvedSymbol(module, actual, alias=symbol), None
        return None, reason


@dataclass
class ImportsReport:
    """Outcome of deriving imports."""

    # (class key, symbol, reason) for every symbol that could not be resolved.
    unresolved: List[Tuple[str, str, str]] = field(default_factory=list)
    # (class key, symbol, imported as) for symbols resolved under another name.
    aliased: List[Tuple[str, str, str]] = field(default_factory=list)


def render_imports(resolved: Iterable[ResolvedSymbol]) -> str:
    """Render resolved symbols as import statements, one line per module."""
    plain: Set[str] = set()
    grouped: Dict[str, Set[str]] = defaultdict(set)
    for symbol in resolved:
        if symbol.name is None:
            plain.add(symbol.module)
        else:
            grouped[symbol.module].add(f"{symbol.name} as {symbol.alias}" if symbol.alias else symbol.name)
    lines = [f"import {module}" for module in sorted(plain)]
    lines += [f"from {module} import {', '.join(sorted(names))}" for module, names in sorted(grouped.items())]
    return "\n".join(lines)


def provided_names(import_text: str) -> Set[str]:
    """Names a block of hand-written import statements makes available."""
    names: Set[str] = set()
    for item in parse_import_statements(import_text).imports:
        if item.objects:
            names.update(o.alias or o.name for o in item.objects)
        else:
            names.add(item.alias or item.module.split(".")[0])
    return names


def derive_imports(
    symbols_per_class: Dict[str, Set[str]],
    hand_maintained: Optional[Dict[str, str]] = None,
    resolver: Optional[SymbolResolver] = None,
) -> Tuple[Dict[str, str], ImportsReport]:
    """Resolve the symbols of every class into an import block, keyed ``{namespace}-{ClassName}``.

    Hand-maintained blocks take precedence: a hand-maintained block is kept verbatim and a symbol it already
    provides is not imported again. Symbols it does not provide are added from the derived imports.
    Symbols that cannot be resolved are collected in the report and left out; they do not stop the run.
    """
    resolver = resolver if resolver is not None else SymbolResolver()
    hand_maintained = hand_maintained or {}
    report = ImportsReport()
    imports: Dict[str, str] = {}

    for class_key in sorted(symbols_per_class):
        hand_block = textwrap.dedent(hand_maintained.get(class_key) or "").strip()
        provided = provided_names(hand_block) if hand_block else set()
        resolved: List[ResolvedSymbol] = []
        for symbol in sorted(symbols_per_class[class_key] - provided):
            result, reason = resolver.resolve(symbol)
            if result is None:
                report.unresolved.append((class_key, symbol, reason or "unknown"))
                continue
            if result.alias:
                report.aliased.append((class_key, symbol, f"{result.module}.{result.name}"))
            resolved.append(result)
        blocks = [block for block in (_clean_block(hand_block), render_imports(resolved)) if block]
        imports[class_key] = "\n\n".join(blocks) + "\n"
    return imports, report


def _clean_block(block: str) -> str:
    return "\n".join(line.rstrip() for line in block.splitlines())


def merge_hand_only(imports: Dict[str, str], hand_maintained: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Add hand-maintained blocks for class keys that were not generated, so nothing hand-written is dropped."""
    merged = dict(imports)
    for key, block in (hand_maintained or {}).items():
        merged.setdefault(key, block)
    return merged


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


class _LiteralDumper(yaml.SafeDumper):
    """Dump multi-line strings as literal blocks, the format of ``imports.yaml``."""


def _represent_str(dumper: yaml.SafeDumper, data: str) -> Any:
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_LiteralDumper.add_representer(str, _represent_str)


def write_imports_yaml(imports: Dict[str, str], path: Path) -> None:
    """Write ``{namespace}-{ClassName}`` -> import block in the format of ``imports.yaml``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(imports, Dumper=_LiteralDumper, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def write_types_yaml(schema: Dict[str, Any], path: Path) -> None:
    """Write a LinkML types file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(schema, sort_keys=False, default_flow_style=False), encoding="utf-8")
