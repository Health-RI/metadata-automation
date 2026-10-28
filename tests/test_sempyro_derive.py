"""Tests for deriving the sempyro types and imports files."""

import importlib.util
import textwrap

import pandas as pd
import pytest
import yaml

from metadata_automation.cli import sempyro
from metadata_automation.sempyro.derive import (
    SempyroIndex,
    SymbolResolver,
    collect_range_types,
    collect_symbols,
    derive_imports,
    derive_types,
    merge_hand_only,
    merge_types,
    provided_names,
    write_imports_yaml,
)
from metadata_automation.sempyro.utils import parse_import_statements


def _sheet(*rows):
    return pd.DataFrame(rows, columns=["Property label", "SeMPyRO_range"])


class TestTypeDerivation:
    def test_collects_every_type_in_ranges(self):
        sheets = {
            "A": _sheet(("one", "str"), ("two", "AnyHttpUrl, LiteralField"), ("three", "nan"), ("nan", "Ghost")),
            "B": _sheet(("one", "str"), ("two", " Location ")),
            "Unlisted": _sheet(("one", "NotInClasses")),
        }
        classes = pd.DataFrame({"sheet_name": ["A", "B", "Missing"]})

        used = collect_range_types(sheets, classes)

        assert used == {
            "AnyHttpUrl": ["A"],
            "LiteralField": ["A"],
            "Location": ["B"],
            "str": ["A", "B"],
        }

    def test_sheet_without_range_column_is_skipped(self):
        sheets = {"A": pd.DataFrame({"Property label": ["x"]})}
        assert collect_range_types(sheets, pd.DataFrame({"sheet_name": ["A"]})) == {}

    def test_derived_types_have_uri_base_and_description(self):
        types = derive_types(["str", "int", "date", "datetime", "LiteralField", "Agent"])

        assert types["str"]["uri"] == "xsd:string"
        assert types["int"]["uri"] == "xsd:int"
        assert types["date"]["uri"] == "xsd:date"
        assert types["datetime"]["uri"] == "xsd:dateTime"
        assert types["LiteralField"]["uri"] == "rdfs:Literal"
        assert types["Agent"]["uri"] == "xsd:anyURI"
        assert all(t["base"] == name and t["description"] for name, t in types.items())

    def test_hand_maintained_types_take_precedence_and_are_kept(self):
        hand = {
            "id": "https://example.org/mine",
            "types": {
                "Agent": {"uri": "xsd:string", "base": "Agent", "description": "by hand"},
                "Unused": {"uri": "xsd:anyURI", "base": "Unused", "description": "kept"},
            },
        }

        merged = merge_types(derive_types(["Agent", "str"]), hand)

        assert merged["id"] == "https://example.org/mine"
        assert merged["types"]["Agent"]["description"] == "by hand"
        assert set(merged["types"]) == {"Agent", "str", "Unused"}

    def test_default_header_without_hand_maintained_file(self):
        merged = merge_types(derive_types(["str"]), None)

        assert merged["prefixes"]["xsd"] == "http://www.w3.org/2001/XMLSchema#"
        assert "str" in merged["types"]


class TestSymbolCollection:
    def test_collects_referenced_but_undefined_names(self):
        source = textwrap.dedent(
            """
            logger = logging.getLogger(__name__)

            class Child(Parent):
                model_config = ConfigDict(json_schema_extra={"$namespace": str(NS)})
                title: Union[LiteralField, str] = Field(json_schema_extra={"rdf_term": DCTERMS.title})
            """
        )

        assert collect_symbols(source) == {
            "logging",
            "Parent",
            "ConfigDict",
            "NS",
            "Union",
            "LiteralField",
            "Field",
            "DCTERMS",
        }

    def test_defined_imported_and_builtin_names_are_not_symbols(self):
        source = textwrap.dedent(
            """
            import os
            from typing import List as L

            CONSTANT = 1

            class Local:
                pass

            def helper(arg, *rest, key=None, **kw):
                inner = [item for item in rest if item]
                return len(inner), arg, key, kw, L, os, CONSTANT, Local
            """
        )

        assert collect_symbols(source) == set()

    def test_field_named_like_its_type_still_needs_the_type(self):
        source = "class A(Base):\n    date: date = Field()\n"

        assert collect_symbols(source) == {"Base", "date", "Field"}

    def test_class_level_names_are_visible_in_the_class_body(self):
        source = textwrap.dedent(
            """
            class A(Base):
                _literal_fields: ClassVar[Set[str]] = {"a"}

                @field_validator(*_literal_fields, mode="before")
                @classmethod
                def check(cls, value: List[str]) -> List[str]:
                    return convert(value)
            """
        )

        assert collect_symbols(source) == {"Base", "ClassVar", "Set", "field_validator", "List", "convert"}

    def test_source_is_not_executed(self):
        # Would raise if executed.
        assert collect_symbols("raise RuntimeError(boom)") == {"boom"}

    def test_invalid_source_raises_syntax_error(self):
        with pytest.raises(SyntaxError):
            collect_symbols("class (")


class TestSymbolResolution:
    @pytest.fixture(scope="class")
    def resolver(self):
        return SymbolResolver()

    @pytest.mark.parametrize(
        ("symbol", "module"),
        [
            ("LiteralField", "sempyro"),
            ("RDFModel", "sempyro"),
            ("DCATDataset", "sempyro.dcat"),
            ("PeriodOfTime", "sempyro.time"),
            ("HEALTHDCATAP", "sempyro.namespaces"),
            ("validate_convert_email", "sempyro.utils.validator_functions"),
            ("Union", "typing"),
            ("date", "datetime"),
            ("ConfigDict", "pydantic"),
            ("field_validator", "pydantic"),
            ("DCTERMS", "rdflib.namespace"),
            ("URIRef", "rdflib"),
            ("logging", "logging"),
        ],
    )
    def test_resolves_to_import_path(self, resolver, symbol, module):
        resolved, reason = resolver.resolve(symbol)

        assert reason is None
        assert resolved.module == module

    def test_plain_module_import_has_no_name(self, resolver):
        resolved, _ = resolver.resolve("logging")

        assert resolved.name is None

    def test_symbol_known_under_another_name_resolves_to_an_alias(self, resolver):
        resolved, _ = resolver.resolve("FOAFAgent")

        assert (resolved.module, resolved.name, resolved.alias) == ("sempyro.foaf", "Agent", "FOAFAgent")

    def test_case_difference_resolves_to_an_alias(self, resolver):
        resolved, _ = resolver.resolve("DCATDataservice")

        assert (resolved.name, resolved.alias) == ("DCATDataService", "DCATDataservice")

    def test_unknown_symbol_is_unresolved_with_reason(self, resolver):
        resolved, reason = resolver.resolve("NoSuchThingAnywhere")

        assert resolved is None
        assert "not found" in reason

    def test_ambiguous_symbol_is_not_guessed(self):
        index = SempyroIndex.__new__(SempyroIndex)
        index.package = "sempyro"
        index.modules_by_name = {"Twice": {"sempyro.a", "sempyro.b"}}

        resolved, reason = SymbolResolver(index).resolve("Twice")

        assert resolved is None
        assert "ambiguous" in reason
        assert "sempyro.a" in reason

    def test_index_does_not_import_sempyro(self):
        import sys

        before = {m for m in sys.modules if m.startswith("sempyro.")}
        SempyroIndex()

        assert {m for m in sys.modules if m.startswith("sempyro.")} == before


class TestImportDerivation:
    def test_derived_block_for_each_class(self):
        imports, report = derive_imports({"hri-A": {"logging", "Union", "LiteralField"}})

        assert list(imports) == ["hri-A"]
        block = imports["hri-A"]
        assert "import logging" in block
        assert "from typing import Union" in block
        assert "from sempyro import LiteralField" in block
        assert report.unresolved == []

    def test_unresolved_symbol_is_reported_by_name_and_class_without_aborting(self):
        imports, report = derive_imports({"hri-A": {"Union", "HRI"}, "hri-B": {"HRI", "Optional"}})

        assert [(c, s) for c, s, _ in report.unresolved] == [("hri-A", "HRI"), ("hri-B", "HRI")]
        assert "from typing import Union" in imports["hri-A"]
        assert "HRI" not in imports["hri-A"].replace("HRI\n", "")
        assert "from typing import Optional" in imports["hri-B"]

    def test_hand_maintained_import_takes_precedence(self):
        hand = {"hri-A": "from custom.module import LiteralField\n"}

        imports, report = derive_imports({"hri-A": {"LiteralField", "Union"}}, hand)

        assert "from custom.module import LiteralField" in imports["hri-A"]
        assert "from sempyro import LiteralField" not in imports["hri-A"]
        assert "from typing import Union" in imports["hri-A"]
        assert report.unresolved == []

    def test_hand_maintained_import_fills_an_unresolvable_symbol(self):
        hand = {"hri-A": "from rdflib.namespace import OWL as HRI"}

        imports, report = derive_imports({"hri-A": {"HRI"}}, hand)

        assert report.unresolved == []
        assert provided_names(imports["hri-A"]) == {"HRI"}

    def test_hand_maintained_block_of_other_classes_is_kept(self):
        imports, _ = derive_imports({"hri-A": {"Union"}})

        merged = merge_hand_only(imports, {"hri-Old": "import logging"})

        assert set(merged) == {"hri-A", "hri-Old"}

    def test_written_file_has_the_imports_yaml_format(self, tmp_path):
        imports, _ = derive_imports({"hri-A": {"logging", "Union", "LiteralField"}})
        path = tmp_path / "out" / "imports.yaml"

        write_imports_yaml(imports, path)

        loaded = yaml.safe_load(path.read_text())
        assert loaded == imports
        assert path.read_text().startswith("hri-A: |\n  import logging")
        assert parse_import_statements(loaded["hri-A"]).imports


class TestEndToEnd:
    @pytest.fixture
    def empty_yaml(self, tmp_path):
        path = tmp_path / "empty.yaml"
        path.write_text("{}")
        return path

    @pytest.fixture
    def run(self, runner, test_input_dir, tmp_path, empty_yaml):
        def _run(excel="test_metadata.xlsx", imports=None, types=None):
            args = [
                "--input-excel",
                str(test_input_dir / excel),
                "--namespace",
                "hri",
                "--linkml-output-path",
                str(tmp_path / "linkml"),
                "--sempyro-output-path",
                str(tmp_path / "classes"),
                "--types-path",
                str(types or empty_yaml),
                "--imports-path",
                str(imports or empty_yaml),
            ]
            return runner.invoke(sempyro, args)

        return _run

    @staticmethod
    def _import_module(path):
        spec = importlib.util.spec_from_file_location(f"generated_{path.stem.replace('-', '_')}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_runs_without_hand_maintained_files_and_reports_unresolved(self, run, tmp_path):
        result = run()

        assert result.exit_code == 0, result.output
        assert "Generation complete!" in result.output
        # The namespace object HRI is not part of sempyro, so it has to be supplied by hand.
        assert "hri-TestClass: cannot resolve symbol 'HRI'" in result.output

        types = yaml.safe_load((tmp_path / "linkml" / "sempyro_types.yaml").read_text())["types"]
        assert {"LiteralField", "str"} <= set(types)

        imports = yaml.safe_load((tmp_path / "classes" / "hri-imports.yaml").read_text())
        assert "hri-TestClass" in imports
        assert "from sempyro import LiteralField" in imports["hri-TestClass"]
        assert "from rdflib.namespace import DCTERMS" in imports["hri-TestClass"]

    def test_hand_maintained_entry_supplies_the_unresolvable_symbol(self, run, tmp_path):
        hand = tmp_path / "hand.yaml"
        hand.write_text(
            yaml.safe_dump(
                {
                    f"hri-{name}": "from rdflib.namespace import OWL as HRI\n"
                    for name in ("ClassA", "ClassB", "TestClass")
                }
            )
        )

        result = run(imports=hand)

        assert result.exit_code == 0, result.output
        assert "cannot resolve symbol 'HRI'" not in result.output
        generated = sorted((tmp_path / "classes" / "hri").glob("*.py"))
        assert generated
        for path in generated:
            module = self._import_module(path)
            assert any(name.startswith("HRI") for name in dir(module))

    def test_hand_maintained_types_take_precedence(self, run, tmp_path):
        hand = tmp_path / "types.yaml"
        hand.write_text(
            yaml.safe_dump({"id": "x", "types": {"str": {"uri": "xsd:token", "base": "str", "description": "mine"}}})
        )

        result = run(types=hand)

        assert result.exit_code == 0, result.output
        types = yaml.safe_load((tmp_path / "linkml" / "sempyro_types.yaml").read_text())["types"]
        assert types["str"]["description"] == "mine"
        assert "LiteralField" in types

    def test_multi_class_fixture(self, run, tmp_path):
        result = run(excel="multi_metadata.xlsx")

        assert result.exit_code == 0, result.output
        imports = yaml.safe_load((tmp_path / "classes" / "hri-imports.yaml").read_text())
        class_files = {p.stem for p in (tmp_path / "classes" / "hri").glob("*.py")}
        assert class_files == set(imports)
