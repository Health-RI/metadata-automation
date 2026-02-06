"""Tests for shacl_from_shaclplay CLI command."""

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from metadata_automation.cli import shacl_from_shaclplay


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


class TestShaclFromShaclplayCLI:
    """Integration tests for shacl_from_shaclplay CLI command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def shaclplay_input_dir(self, test_expected_dir):
        """Path to SHACLPlay files to use as input for SHACL conversion."""
        return test_expected_dir / "default"

    @pytest.fixture
    def shaclplay_multi_input_dir(self, test_expected_dir):
        """Path to multi-class SHACLPlay files for testing."""
        return test_expected_dir / "multi"

    def test_shacl_from_shaclplay_success(self, runner, shaclplay_input_dir, test_expected_dir, tmp_path):
        """Test successful SHACL Turtle generation from SHACLPlay Excel."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            shacl_from_shaclplay, ["--input-path", str(shaclplay_input_dir), "--output-path", str(output_dir)]
        )

        assert result.exit_code == 0

        output_file = output_dir / "hri" / "hri-testclass.ttl"
        expected_file = test_expected_dir / "default" / "hri" / "hri-testclass.ttl"

        assert output_file.exists()
        assert expected_file.exists()
        assert_turtle_equivalent(output_file, expected_file)

    def test_shacl_from_shaclplay_no_files(self, runner, tmp_path):
        """Test error handling when no SHACLPlay files found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(
            shacl_from_shaclplay, ["--input-path", str(empty_dir), "--output-path", str(tmp_path / "output")]
        )

        assert result.exit_code != 0
        assert "No SHACLPlay Excel files found" in result.output

    def test_shacl_from_shaclplay_invalid_excel(self, runner, test_input_dir, tmp_path):
        """Test error handling for invalid Excel structure."""
        shaclplay_dir = tmp_path / "shaclplay"
        shaclplay_dir.mkdir()

        excel_path = test_input_dir / "invalid_shaclplay.xlsx"
        target_path = shaclplay_dir / "SHACL-invalid.xlsx"
        target_path.write_bytes(excel_path.read_bytes())

        result = runner.invoke(
            shacl_from_shaclplay, ["--input-path", str(shaclplay_dir), "--output-path", str(tmp_path / "output")]
        )

        assert result.exit_code != 0

    def test_shacl_from_shaclplay_multiple_files(self, runner, shaclplay_multi_input_dir, test_expected_dir, tmp_path):
        """Test processing multiple SHACLPlay files."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            shacl_from_shaclplay, ["--input-path", str(shaclplay_multi_input_dir), "--output-path", str(output_dir)]
        )

        assert result.exit_code == 0

        output_classa = output_dir / "hri" / "hri-classa.ttl"
        output_classb = output_dir / "hri" / "hri-classb.ttl"
        expected_classa = test_expected_dir / "multi" / "hri" / "hri-classa.ttl"
        expected_classb = test_expected_dir / "multi" / "hri" / "hri-classb.ttl"

        assert output_classa.exists()
        assert output_classb.exists()

        assert_turtle_equivalent(output_classa, expected_classa)
        assert_turtle_equivalent(output_classb, expected_classb)

    def test_shacl_from_shaclplay_missing_input_directory(self, runner, tmp_path):
        """Test error handling when input directory doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent"

        result = runner.invoke(
            shacl_from_shaclplay, ["--input-path", str(nonexistent_dir), "--output-path", str(tmp_path / "output")]
        )

        assert result.exit_code != 0
        assert "Invalid value for '-i' / '--input-path'" in result.output

    def test_shacl_from_shaclplay_preserves_namespace(self, runner, shaclplay_input_dir, tmp_path):
        """Test that namespace is correctly preserved in output."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            shacl_from_shaclplay, ["--input-path", str(shaclplay_input_dir), "--output-path", str(output_dir)]
        )

        assert result.exit_code == 0

        output_file = output_dir / "hri" / "hri-testclass.ttl"
        content = output_file.read_text()
        assert "@prefix hri:" in content

    def test_shacl_from_shaclplay_file_naming(self, runner, shaclplay_input_dir, tmp_path):
        """Test that output files follow naming convention."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            shacl_from_shaclplay, ["--input-path", str(shaclplay_input_dir), "--output-path", str(output_dir)]
        )

        assert result.exit_code == 0

        # Files should be named as {namespace}/{namespace}-{classname}.ttl
        expected_file = output_dir / "hri" / "hri-testclass.ttl"
        assert expected_file.exists()
