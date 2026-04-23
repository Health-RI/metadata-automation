"""Tests for inspect_inheritance CLI command."""

from pathlib import Path
from textwrap import dedent

import pytest

from metadata_automation.cli import inspect_inheritance
from metadata_automation.sempyro.inheritance_inspector import (
    ClassInfo,
    FieldMeta,
    _resolve_ancestor,
    compare_field_infos,
    format_report,
    inspect_file,
    parse_class_from_source,
)


# ---------------------------------------------------------------------------
# Synthetic source fixtures
# ---------------------------------------------------------------------------

_PARENT_SOURCE = dedent("""\
    from pydantic import BaseModel, Field

    class ParentClass(BaseModel):
        shared_field: str = Field(
            description="A shared field.",
            json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"},
        )
        parent_only: str = Field(
            description="Only in parent.",
            json_schema_extra={"rdf_term": DCTERMS.creator, "rdf_type": "uri"},
        )
""")

_CHILD_SOURCE = dedent("""\
    from pydantic import BaseModel, Field
    from parent_module import ParentClass

    class ChildClass(ParentClass):
        shared_field: str = Field(
            description="A shared field.",
            json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"},
        )
        different_field: str = Field(
            description="Same name, different rdf_type.",
            json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "uri"},
        )
        child_only: str = Field(
            description="Only in child.",
            json_schema_extra={"rdf_term": DCTERMS.identifier, "rdf_type": "rdfs_literal"},
        )
""")

_PARENT_SOURCE_FOR_DIFFERENT = dedent("""\
    from pydantic import BaseModel, Field

    class ParentClass(BaseModel):
        shared_field: str = Field(
            description="A shared field.",
            json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"},
        )
        different_field: str = Field(
            description="DIFFERENT description.",
            json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "rdfs_literal"},
        )
""")

# Parent uses unprefixed field names; child uses prefixed names (e.g. dct_title).
# Same rdf_term means the fields are semantically equivalent despite different names.
_PARENT_WITH_UNPREFIXED = dedent("""\
    from pydantic import BaseModel, Field

    class ParentClass(BaseModel):
        title: str = Field(
            description="Title of the resource.",
            json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"},
        )
        description: str = Field(
            description="Description of the resource.",
            json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "rdfs_literal"},
        )
        unique_parent_field: str = Field(
            description="Only in parent.",
            json_schema_extra={"rdf_term": DCTERMS.creator, "rdf_type": "uri"},
        )
""")

_CHILD_WITH_PREFIXED = dedent("""\
    from pydantic import BaseModel, Field
    from parent_module import ParentClass

    class ChildClass(ParentClass):
        dct_title: str = Field(
            description="Title of the resource.",
            json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"},
        )
        dct_description: str = Field(
            description="Description of the resource.",
            json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "rdfs_literal"},
        )
        child_only: str = Field(
            description="Only in child.",
            json_schema_extra={"rdf_term": DCTERMS.identifier, "rdf_type": "rdfs_literal"},
        )
""")


@pytest.fixture
def synthetic_dir(tmp_path):
    """Create a directory with a parent and child class file for testing."""
    parent_file = tmp_path / "parent_module.py"
    parent_file.write_text(_PARENT_SOURCE)
    child_file = tmp_path / "child_module.py"
    child_file.write_text(_CHILD_SOURCE)
    return tmp_path


@pytest.fixture
def synthetic_dir_with_diff(tmp_path):
    """Like synthetic_dir but the parent has a different field definition."""
    parent_file = tmp_path / "parent_module.py"
    parent_file.write_text(_PARENT_SOURCE_FOR_DIFFERENT)
    child_file = tmp_path / "child_module.py"
    child_file.write_text(_CHILD_SOURCE)
    return tmp_path


@pytest.fixture
def synthetic_dir_with_renamed_fields(tmp_path):
    """Parent uses unprefixed field names; child uses prefixed names (dct_*)."""
    parent_file = tmp_path / "parent_module.py"
    parent_file.write_text(_PARENT_WITH_UNPREFIXED)
    child_file = tmp_path / "child_module.py"
    child_file.write_text(_CHILD_WITH_PREFIXED)
    return tmp_path


@pytest.fixture(scope="session")
def hri_classes_dir():
    """Directory containing the real generated HRI SeMPyRO class files."""
    path = Path(__file__).resolve().parent.parent / "outputs" / "sempyro_classes" / "hri"
    if not path.exists():
        pytest.skip("HRI sempyro_classes output directory not found")
    return path


@pytest.fixture(scope="session")
def dataset_file(hri_classes_dir):
    """Path to the generated hri-Dataset.py file."""
    path = hri_classes_dir / "hri-Dataset.py"
    if not path.exists():
        pytest.skip("hri-Dataset.py not found")
    return path


# ---------------------------------------------------------------------------
# Unit tests: parse_class_from_source
# ---------------------------------------------------------------------------


class TestParseClassFromSource:
    def test_parses_class_name(self):
        info = parse_class_from_source(_CHILD_SOURCE)
        assert info is not None
        assert info.class_name == "ChildClass"

    def test_parses_bases(self):
        info = parse_class_from_source(_CHILD_SOURCE)
        assert "ParentClass" in info.bases

    def test_parses_own_fields(self):
        info = parse_class_from_source(_CHILD_SOURCE)
        assert "shared_field" in info.own_fields
        assert "child_only" in info.own_fields

    def test_parses_field_description(self):
        info = parse_class_from_source(_CHILD_SOURCE)
        assert info.own_fields["shared_field"].description == "A shared field."

    def test_parses_rdf_term_as_string(self):
        info = parse_class_from_source(_CHILD_SOURCE)
        # ast.unparse preserves the attribute access as-written
        assert info.own_fields["shared_field"].rdf_term == "DCTERMS.title"

    def test_parses_rdf_type(self):
        info = parse_class_from_source(_CHILD_SOURCE)
        assert info.own_fields["shared_field"].rdf_type == "rdfs_literal"

    def test_returns_none_on_empty_source(self):
        result = parse_class_from_source("# no class here\nx = 1\n")
        assert result is None

    def test_returns_none_on_syntax_error(self):
        result = parse_class_from_source("def broken(:\n")
        assert result is None

    def test_target_class_filter(self):
        source = _PARENT_SOURCE
        info = parse_class_from_source(source, target_class="ParentClass")
        assert info is not None
        assert info.class_name == "ParentClass"

    def test_target_class_not_found_returns_none(self):
        info = parse_class_from_source(_PARENT_SOURCE, target_class="NonExistent")
        assert info is None

    def test_builds_import_map(self):
        info = parse_class_from_source(_CHILD_SOURCE)
        assert "ParentClass" in info.import_map
        assert info.import_map["ParentClass"] == "parent_module"


# ---------------------------------------------------------------------------
# Unit tests: compare_field_infos
# ---------------------------------------------------------------------------


class TestCompareFieldInfos:
    def test_identical_fields_all_same(self):
        fi_a = FieldMeta(description="Desc.", rdf_term="DCTERMS.title", rdf_type="rdfs_literal")
        fi_b = FieldMeta(description="Desc.", rdf_term="DCTERMS.title", rdf_type="rdfs_literal")
        result = compare_field_infos(fi_a, fi_b)
        assert result["description"]["same"] is True
        assert result["rdf_term"]["same"] is True
        assert result["rdf_type"]["same"] is True

    def test_different_rdf_type(self):
        fi_a = FieldMeta(description="Desc.", rdf_term="DCTERMS.title", rdf_type="rdfs_literal")
        fi_b = FieldMeta(description="Desc.", rdf_term="DCTERMS.title", rdf_type="uri")
        result = compare_field_infos(fi_a, fi_b)
        assert result["rdf_type"]["same"] is False
        assert result["rdf_type"]["child"] == "rdfs_literal"
        assert result["rdf_type"]["parent"] == "uri"

    def test_different_description(self):
        fi_a = FieldMeta(description="Child desc.", rdf_term="DCTERMS.title", rdf_type="uri")
        fi_b = FieldMeta(description="Parent desc.", rdf_term="DCTERMS.title", rdf_type="uri")
        result = compare_field_infos(fi_a, fi_b)
        assert result["description"]["same"] is False

    def test_different_rdf_term(self):
        fi_a = FieldMeta(description="Desc.", rdf_term="DCTERMS.title", rdf_type="uri")
        fi_b = FieldMeta(description="Desc.", rdf_term="DCTERMS.description", rdf_type="uri")
        result = compare_field_infos(fi_a, fi_b)
        assert result["rdf_term"]["same"] is False


# ---------------------------------------------------------------------------
# Unit tests: inspect_file
# ---------------------------------------------------------------------------


class TestInspectFile:
    def test_returns_class_name(self, synthetic_dir):
        result = inspect_file(synthetic_dir / "child_module.py")
        assert result["error"] is None
        assert result["class_name"] == "ChildClass"

    def test_has_ancestor_chain(self, synthetic_dir):
        result = inspect_file(synthetic_dir / "child_module.py")
        assert result["error"] is None
        assert len(result["ancestor_chain"]) >= 1
        level, name = result["ancestor_chain"][0]
        assert level == 1
        assert name == "ParentClass"

    def test_overlapping_fields_found(self, synthetic_dir):
        result = inspect_file(synthetic_dir / "child_module.py")
        assert result["error"] is None
        field_names = [o["field_name"] for o in result["overlapping"]]
        assert "shared_field" in field_names

    def test_child_only_field_not_in_overlapping(self, synthetic_dir):
        result = inspect_file(synthetic_dir / "child_module.py")
        field_names = [o["field_name"] for o in result["overlapping"]]
        assert "child_only" not in field_names

    def test_identical_field_marked_correctly(self, synthetic_dir):
        result = inspect_file(synthetic_dir / "child_module.py")
        overlap = next(o for o in result["overlapping"] if o["field_name"] == "shared_field")
        assert overlap["identical"] is True

    def test_different_field_marked_correctly(self, synthetic_dir_with_diff):
        result = inspect_file(synthetic_dir_with_diff / "child_module.py")
        field_names = [o["field_name"] for o in result["overlapping"]]
        assert "different_field" in field_names
        overlap = next(o for o in result["overlapping"] if o["field_name"] == "different_field")
        assert overlap["identical"] is False

    def test_each_overlap_has_required_keys(self, synthetic_dir):
        result = inspect_file(synthetic_dir / "child_module.py")
        for overlap in result["overlapping"]:
            assert "field_name" in overlap
            assert "parent_field_name" in overlap
            assert "matched_by" in overlap
            assert "found_in" in overlap
            assert "found_at_level" in overlap
            assert "comparison" in overlap
            assert "identical" in overlap

    def test_name_match_has_matched_by_name(self, synthetic_dir):
        result = inspect_file(synthetic_dir / "child_module.py")
        overlap = next(o for o in result["overlapping"] if o["field_name"] == "shared_field")
        assert overlap["matched_by"] == "name"
        assert overlap["parent_field_name"] == "shared_field"

    # --- rdf_term-based matching ---

    def test_rdf_term_match_finds_renamed_field(self, synthetic_dir_with_renamed_fields):
        """dct_title in child should match title in parent via rdf_term=DCTERMS.title."""
        result = inspect_file(synthetic_dir_with_renamed_fields / "child_module.py")
        assert result["error"] is None
        field_names = [o["field_name"] for o in result["overlapping"]]
        assert "dct_title" in field_names

    def test_rdf_term_match_reports_parent_field_name(self, synthetic_dir_with_renamed_fields):
        result = inspect_file(synthetic_dir_with_renamed_fields / "child_module.py")
        overlap = next(o for o in result["overlapping"] if o["field_name"] == "dct_title")
        assert overlap["parent_field_name"] == "title"
        assert overlap["matched_by"] == "rdf_term"

    def test_rdf_term_match_is_not_marked_identical(self, synthetic_dir_with_renamed_fields):
        """Field name differs, so identical must be False even if all other attrs match."""
        result = inspect_file(synthetic_dir_with_renamed_fields / "child_module.py")
        overlap = next(o for o in result["overlapping"] if o["field_name"] == "dct_title")
        assert overlap["identical"] is False

    def test_rdf_term_match_child_only_not_overlapping(self, synthetic_dir_with_renamed_fields):
        result = inspect_file(synthetic_dir_with_renamed_fields / "child_module.py")
        field_names = [o["field_name"] for o in result["overlapping"]]
        assert "child_only" not in field_names

    # --- package re-export resolution ---

    def test_resolves_class_through_package_init_reexport(self):
        """DCATDataset is defined in sempyro.dcat.dcat_dataset but re-exported
        from sempyro.dcat.__init__.  _find_in_package must walk submodules."""
        from metadata_automation.sempyro.inheritance_inspector import _find_in_package

        info = _find_in_package("DCATDataset", "sempyro.dcat")
        assert info is not None, "DCATDataset should be found via package submodule scan"
        assert info.class_name == "DCATDataset"
        # The class should expose its own fields
        assert len(info.own_fields) > 0

    def test_resolves_legacy_imported_parent_alias(self):
        import_map = {"Agent": "sempyro.foaf"}

        info = _resolve_ancestor("FOAFAgent", import_map, [])

        assert info is not None
        assert info.class_name == "Agent"

    def test_hri_dataset_has_overlapping_fields_via_rdf_term(self, dataset_file):
        """With sempyro installed and package re-export resolution, HRI Dataset
        fields should be detected as overlapping with DCATDataset via rdf_term."""
        result = inspect_file(dataset_file)
        assert result["error"] is None
        # At minimum dct_description or dct_title should overlap with DCATDataset
        rdf_term_matches = [o for o in result["overlapping"] if o.get("matched_by") == "rdf_term"]
        assert len(rdf_term_matches) > 0, (
            "Expected rdf_term-based overlaps between HRIDataset and DCATDataset"
        )

    def test_found_at_level_is_positive(self, synthetic_dir):
        result = inspect_file(synthetic_dir / "child_module.py")
        for overlap in result["overlapping"]:
            assert overlap["found_at_level"] >= 1

    def test_error_on_nonexistent_file(self, tmp_path):
        result = inspect_file(tmp_path / "nonexistent.py")
        assert result["error"] is not None

    def test_error_on_file_with_no_class(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("x = 1\n")
        result = inspect_file(f)
        assert result["error"] is not None

    def test_total_direct_fields_positive(self, synthetic_dir):
        result = inspect_file(synthetic_dir / "child_module.py")
        assert result["total_direct_fields"] > 0

    def test_hri_dataset_parses_class_name(self, dataset_file):
        """Smoke test: AST-parse a real HRI file (no sempyro import needed)."""
        result = inspect_file(dataset_file)
        assert result["error"] is None
        assert result["class_name"] == "HRIDataset"

    def test_hri_dataset_has_direct_fields(self, dataset_file):
        result = inspect_file(dataset_file)
        assert result["total_direct_fields"] > 0

    def test_hri_dataset_ancestor_reported(self, dataset_file):
        """Ancestor chain should list DCATDataset even if its source is unavailable."""
        result = inspect_file(dataset_file)
        chain_names = [name for _, name in result["ancestor_chain"]]
        # Either resolved or marked as unavailable — DCATDataset must appear
        assert any("DCATDataset" in name for name in chain_names)


# ---------------------------------------------------------------------------
# Unit tests: format_report
# ---------------------------------------------------------------------------


class TestFormatReport:
    def test_report_contains_class_name(self, synthetic_dir):
        results = [inspect_file(synthetic_dir / "child_module.py")]
        report = format_report(results)
        assert "ChildClass" in report

    def test_report_contains_ancestor_name(self, synthetic_dir):
        results = [inspect_file(synthetic_dir / "child_module.py")]
        report = format_report(results)
        assert "ParentClass" in report

    def test_report_contains_identical_verdict(self, synthetic_dir):
        results = [inspect_file(synthetic_dir / "child_module.py")]
        report = format_report(results)
        assert "IDENTICAL" in report

    def test_report_contains_differs_verdict(self, synthetic_dir_with_diff):
        results = [inspect_file(synthetic_dir_with_diff / "child_module.py")]
        report = format_report(results)
        assert "DIFFERS" in report

    def test_report_contains_found_in(self, synthetic_dir):
        results = [inspect_file(synthetic_dir / "child_module.py")]
        report = format_report(results)
        assert "found in" in report

    def test_report_error_handled_gracefully(self, tmp_path):
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("x = 1\n")
        results = [inspect_file(bad_file)]
        report = format_report(results)
        assert "ERROR" in report

    def test_report_contains_summary(self, synthetic_dir):
        results = [inspect_file(synthetic_dir / "child_module.py")]
        report = format_report(results)
        assert "Summary:" in report

    def test_report_shows_rdf_term_match_with_arrow(self, synthetic_dir_with_renamed_fields):
        results = [inspect_file(synthetic_dir_with_renamed_fields / "child_module.py")]
        report = format_report(results)
        # Renamed-field matches appear as "child_name  →  parent_name  (matched by rdf_term)"
        assert "dct_title" in report
        assert "→" in report
        assert "matched by rdf_term" in report


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestInspectInheritanceCLI:
    def test_runs_successfully_on_synthetic_dir(self, runner, synthetic_dir):
        result = runner.invoke(inspect_inheritance, ["--input-dir", str(synthetic_dir)])
        assert result.exit_code == 0

    def test_output_contains_class_name(self, runner, synthetic_dir):
        result = runner.invoke(inspect_inheritance, ["--input-dir", str(synthetic_dir)])
        assert result.exit_code == 0
        assert "ChildClass" in result.output

    def test_output_contains_ancestor_name(self, runner, synthetic_dir):
        result = runner.invoke(inspect_inheritance, ["--input-dir", str(synthetic_dir)])
        assert result.exit_code == 0
        assert "ParentClass" in result.output

    def test_output_file_written(self, runner, synthetic_dir, tmp_path):
        out_file = tmp_path / "report.txt"
        result = runner.invoke(
            inspect_inheritance,
            ["--input-dir", str(synthetic_dir), "--output-file", str(out_file)],
        )
        assert result.exit_code == 0
        assert out_file.exists()
        assert len(out_file.read_text(encoding="utf-8")) > 0

    def test_output_file_contains_inherits_from(self, runner, synthetic_dir, tmp_path):
        out_file = tmp_path / "report.txt"
        runner.invoke(
            inspect_inheritance,
            ["--input-dir", str(synthetic_dir), "--output-file", str(out_file)],
        )
        content = out_file.read_text(encoding="utf-8")
        assert "inherits from" in content

    def test_output_contains_summary(self, runner, synthetic_dir):
        result = runner.invoke(inspect_inheritance, ["--input-dir", str(synthetic_dir)])
        assert result.exit_code == 0
        assert "Summary:" in result.output

    def test_empty_directory_exits_with_error(self, runner, tmp_path):
        result = runner.invoke(inspect_inheritance, ["--input-dir", str(tmp_path)])
        assert result.exit_code != 0

    def test_nonexistent_directory_exits_with_error(self, runner):
        result = runner.invoke(inspect_inheritance, ["--input-dir", "/nonexistent/path/xyz"])
        assert result.exit_code != 0

    def test_hri_dir_parses_without_error(self, runner, hri_classes_dir):
        """Smoke test: AST-parse real HRI files without needing sempyro installed."""
        result = runner.invoke(inspect_inheritance, ["--input-dir", str(hri_classes_dir)])
        assert result.exit_code == 0
        # At least one HRI class name must appear (AST parse always works)
        assert "HRIDataset" in result.output or "HRICatalog" in result.output
