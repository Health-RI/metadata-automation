"""Tests for shacl_from_shaclplay CLI command."""

import re
from pathlib import Path

import pandas as pd
import pytest
from rdflib import Graph
from rdflib.compare import isomorphic

from metadata_automation.cli import shacl_from_shaclplay
from metadata_automation.fdp.shapes import validation_filename


def normalize_turtle(content: str) -> str:
    """Normalize Turtle RDF for comparison.

    Removes comments and normalizes whitespace while preserving structure.
    """
    lines = [line for line in content.split("\n") if not line.strip().startswith("#")]  # Remove comment lines
    normalized = "\n".join(lines)  # Rejoin and normalize whitespace
    normalized = re.sub(r"\n\s*\n+", "\n", normalized)  # Remove extra blank lines
    return normalized.strip()


def assert_turtle_equivalent(actual_path: Path, expected_path: Path) -> None:
    """Compare two Turtle files, ignoring comments and whitespace variations."""
    actual_content = actual_path.read_text()
    expected_content = expected_path.read_text()

    actual_normalized = normalize_turtle(actual_content)
    expected_normalized = normalize_turtle(expected_content)

    assert actual_normalized == expected_normalized, (
        f"Turtle files differ:\nExpected: {expected_path}\nActual: {actual_path}"
    )


def write_model_excel(path: Path, independent: dict[str, bool], nodes: dict[str, list[str]] | None = None) -> Path:
    """Minimal model Excel: one class sheet per class, with optional sh:node references."""
    nodes = nodes or {}
    sheets = {
        "prefixes": pd.DataFrame({"prefix": ["hri"], "namespace": ["http://example.com/"]}),
        "classes": pd.DataFrame(
            {
                "sheet_name": list(independent),
                "class_URI": [f"hri:{name}" for name in independent],
                "SHACL_independent_class": list(independent.values()),
            }
        ),
    }
    for name in independent:
        sheets[name] = pd.DataFrame({"SHACL_sh:node": nodes.get(name) or [None]})
    with pd.ExcelWriter(path) as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return path


class TestShaclFromShaclplayCLI:
    """Integration tests for shacl_from_shaclplay CLI command."""

    @pytest.fixture
    def shaclplay_input_dir(self, test_expected_dir):
        """Path to SHACLPlay files to use as input for SHACL conversion."""
        return test_expected_dir / "default"

    @pytest.fixture
    def shaclplay_multi_input_dir(self, test_expected_dir):
        """Path to multi-class SHACLPlay files for testing."""
        return test_expected_dir / "multi"

    @pytest.fixture
    def model_excel(self, tmp_path):
        return write_model_excel(tmp_path / "model.xlsx", {"TestClass": True})

    @pytest.fixture
    def multi_model_excel(self, tmp_path):
        return write_model_excel(tmp_path / "model.xlsx", {"ClassA": True, "ClassB": True})

    def test_shacl_from_shaclplay_success(self, runner, shaclplay_input_dir, test_expected_dir, model_excel, tmp_path):
        """Test successful SHACL Turtle generation from SHACLPlay Excel."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            shacl_from_shaclplay,
            ["--input-path", str(shaclplay_input_dir), "--output-path", str(output_dir), "-e", str(model_excel)],
        )

        assert result.exit_code == 0

        output_file = output_dir / "PiecesShape" / "hri-testclass.ttl"
        expected_file = test_expected_dir / "default" / "hri" / "hri-testclass.ttl"

        assert output_file.exists()
        assert expected_file.exists()
        assert_turtle_equivalent(output_file, expected_file)

    def test_shacl_from_shaclplay_no_files(self, runner, model_excel, tmp_path):
        """Test error handling when no SHACLPlay files found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(
            shacl_from_shaclplay,
            ["--input-path", str(empty_dir), "--output-path", str(tmp_path / "output"), "-e", str(model_excel)],
        )

        assert result.exit_code != 0
        assert "No SHACLPlay Excel files found" in result.output

    def test_shacl_from_shaclplay_invalid_excel(self, runner, test_input_dir, model_excel, tmp_path):
        """Test error handling for invalid Excel structure."""
        shaclplay_dir = tmp_path / "shaclplay"
        shaclplay_dir.mkdir()

        excel_path = test_input_dir / "invalid_shaclplay.xlsx"
        target_path = shaclplay_dir / "SHACL-invalid.xlsx"
        target_path.write_bytes(excel_path.read_bytes())

        result = runner.invoke(
            shacl_from_shaclplay,
            ["--input-path", str(shaclplay_dir), "--output-path", str(tmp_path / "output"), "-e", str(model_excel)],
        )

        assert result.exit_code != 0

    def test_shacl_from_shaclplay_multiple_files(
        self, runner, shaclplay_multi_input_dir, test_expected_dir, multi_model_excel, tmp_path
    ):
        model_excel = multi_model_excel
        """Test processing multiple SHACLPlay files."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            shacl_from_shaclplay,
            ["--input-path", str(shaclplay_multi_input_dir), "--output-path", str(output_dir), "-e", str(model_excel)],
        )

        assert result.exit_code == 0

        output_classa = output_dir / "PiecesShape" / "hri-classa.ttl"
        output_classb = output_dir / "PiecesShape" / "hri-classb.ttl"
        expected_classa = test_expected_dir / "multi" / "hri" / "hri-classa.ttl"
        expected_classb = test_expected_dir / "multi" / "hri" / "hri-classb.ttl"

        assert output_classa.exists()
        assert output_classb.exists()

        assert_turtle_equivalent(output_classa, expected_classa)
        assert_turtle_equivalent(output_classb, expected_classb)

    def test_shacl_from_shaclplay_missing_input_directory(self, runner, model_excel, tmp_path):
        """Test error handling when input directory doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent"

        result = runner.invoke(
            shacl_from_shaclplay,
            ["--input-path", str(nonexistent_dir), "--output-path", str(tmp_path / "output"), "-e", str(model_excel)],
        )

        assert result.exit_code != 0
        assert "Invalid value for '-i' / '--input-path'" in result.output

    def test_shacl_from_shaclplay_file_naming(self, runner, shaclplay_input_dir, model_excel, tmp_path):
        """Test that output files follow naming convention."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            shacl_from_shaclplay,
            ["--input-path", str(shaclplay_input_dir), "--output-path", str(output_dir), "-e", str(model_excel)],
        )

        assert result.exit_code == 0

        # Files should be named as PiecesShape/{namespace}-{classname}.ttl
        expected_file = output_dir / "PiecesShape" / "hri-testclass.ttl"
        assert expected_file.exists()


class TestFdpShapes:
    """Tests for merging SHACL pieces into FDP and validation shapes."""

    def _run(self, runner, test_expected_dir, output_dir, excel):
        return runner.invoke(
            shacl_from_shaclplay, ["-i", str(test_expected_dir / "multi"), "-o", str(output_dir), "-e", str(excel)]
        )

    def test_merges_pieces_per_schema(self, runner, test_expected_dir, tmp_path):
        excel = write_model_excel(
            tmp_path / "model.xlsx", {"ClassA": True, "ClassB": False}, {"ClassA": ["hri:ClassBShape"]}
        )
        output_dir = tmp_path / "output"
        result = self._run(runner, test_expected_dir, output_dir, excel)

        assert result.exit_code == 0, result.output
        pieces = [Graph().parse(output_dir / "PiecesShape" / f) for f in ("hri-classa.ttl", "hri-classb.ttl")]
        assert [p.name for p in (output_dir / "FairDataPointShape").iterdir()] == ["ClassA.ttl"]
        assert isomorphic(Graph().parse(output_dir / "FairDataPointShape" / "ClassA.ttl"), pieces[0] + pieces[1])
        validation = Graph().parse(output_dir / "ValidationShape" / "hri-shapes.ttl")
        assert isomorphic(validation, pieces[0] + pieces[1])

    def test_missing_piece_fails(self, runner, test_expected_dir, tmp_path):
        excel = write_model_excel(tmp_path / "model.xlsx", {"ClassA": True, "Other": True})
        result = self._run(runner, test_expected_dir, tmp_path / "output", excel)

        assert result.exit_code == 1
        assert "other" in result.output

    def test_without_independent_classes_only_validation(self, runner, test_expected_dir, tmp_path):
        excel = write_model_excel(tmp_path / "model.xlsx", {"ClassA": None, "ClassB": None})
        output_dir = tmp_path / "output"
        result = self._run(runner, test_expected_dir, output_dir, excel)

        assert result.exit_code == 0, result.output
        assert not (output_dir / "FairDataPointShape").exists()
        pieces = [Graph().parse(output_dir / "PiecesShape" / f) for f in ("hri-classa.ttl", "hri-classb.ttl")]
        validation = Graph().parse(output_dir / "ValidationShape" / "hri-shapes.ttl")
        assert isomorphic(validation, pieces[0] + pieces[1])


@pytest.mark.parametrize("namespaces,expected", [({"hri"}, "hri-shapes.ttl"), ({"hri", "ex"}, "Validation-shapes.ttl")])
def test_validation_filename(namespaces, expected):
    assert validation_filename(namespaces) == expected
