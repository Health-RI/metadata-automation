"""Tests for sempyro CLI command."""

import pytest
from click.testing import CliRunner

from metadata_automation.cli import sempyro


class TestSemPyRoCLI:
    """Integration tests for sempyro CLI command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def test_excel(self, test_input_dir):
        """Path to the standard test Excel input file."""
        return test_input_dir / "test_metadata.xlsx"

    @pytest.fixture
    def multi_excel(self, test_input_dir):
        """Path to multi-class test Excel input file."""
        return test_input_dir / "multi_metadata.xlsx"

    @pytest.fixture
    def sempyro_output_dirs(self, tmp_path):
        """Output directories for sempyro CLI tests."""
        linkml_output_dir = tmp_path / "linkml"
        sempyro_output_dir = tmp_path / "sempyro_classes"
        return linkml_output_dir, sempyro_output_dir

    @pytest.fixture
    def cli_args_with_temp_paths(self, sempyro_output_dirs, test_imports_path):
        """CLI arguments to use temp output paths."""
        linkml_output_dir, sempyro_output_dir = sempyro_output_dirs
        return [
            "--linkml-output-path",
            str(linkml_output_dir),
            "--sempyro-output-path",
            str(sempyro_output_dir),
            "--imports-path",
            str(test_imports_path),
        ]

    def test_sempyro_missing_excel(self, runner, cli_args_with_temp_paths):
        """Test error handling for missing input file."""
        result = runner.invoke(sempyro, ["--input-excel", "nonexistent.xlsx"] + cli_args_with_temp_paths)

        assert result.exit_code != 0
        assert (
            "Error: Invalid value for '-i' / '--input-excel': Path 'nonexistent.xlsx' does not exist." in result.output
        )

    def test_sempyro_missing_classes_sheet(self, runner, test_input_dir, cli_args_with_temp_paths):
        """Test error handling for missing classes sheet."""
        excel_path = test_input_dir / "bad_metadata.xlsx"

        result = runner.invoke(sempyro, ["--input-excel", str(excel_path)] + cli_args_with_temp_paths)

        assert result.exit_code != 0

    def test_sempyro_accepts_explicit_namespace(self, runner, test_excel, cli_args_with_temp_paths):
        """Test that sempyro accepts --namespace parameter."""
        result = runner.invoke(
            sempyro,
            [
                "--input-excel",
                str(test_excel),
                "--namespace",
                "hri",
            ]
            + cli_args_with_temp_paths,
        )

        # Should show namespace is being used
        assert "Using provided namespace: hri" in result.output

    def test_sempyro_auto_detects_namespace(self, runner, test_excel, cli_args_with_temp_paths):
        """Test that sempyro can auto-detect namespace from Excel."""
        result = runner.invoke(
            sempyro,
            [
                "--input-excel",
                str(test_excel),
            ]
            + cli_args_with_temp_paths,
        )

        # Should attempt auto-detection and report detected namespace
        assert "Auto-detecting namespace from Excel file..." in result.output
        assert "Detected namespace: hri" in result.output

    def test_sempyro_requires_sempyro_ontology_column(self, runner, test_excel, cli_args_with_temp_paths):
        """Test that sempyro requires SeMPyRO_annotations_ontology column.

        Now that test files have the column, this should fail at a different stage
        (LinkML generation or imports loading) rather than column checking.
        """
        result = runner.invoke(
            sempyro,
            [
                "--input-excel",
                str(test_excel),
                "--namespace",
                "hri",
            ]
            + cli_args_with_temp_paths,
        )

        assert "Error: 'SeMPyRO_annotations_ontology' column not found in classes sheet" in result.output

    def test_sempyro_generates_expected_files(
        self,
        runner,
        test_excel,
        test_expected_dir,
        sempyro_output_dirs,
        cli_args_with_temp_paths,
    ):
        """Test that sempyro generates expected LinkML and class outputs."""
        linkml_output_dir, sempyro_output_dir = sempyro_output_dirs

        result = runner.invoke(
            sempyro,
            [
                "--input-excel",
                str(test_excel),
                "--namespace",
                "hri",
            ]
            + cli_args_with_temp_paths,
        )

        assert result.exit_code == 0

        actual_linkml = linkml_output_dir / "hri" / "hri-TestClass.yaml"
        actual_class = sempyro_output_dir / "hri" / "hri-TestClass.py"

        expected_linkml = test_expected_dir / "linkml" / "hri" / "hri-TestClass.yaml"
        expected_class = test_expected_dir / "sempyro_classes" / "hri" / "hri-TestClass.py"

        assert actual_linkml.exists()
        assert actual_class.exists()
        assert expected_linkml.exists()
        assert expected_class.exists()

        assert actual_linkml.read_text() == expected_linkml.read_text()
        assert actual_class.read_text() == expected_class.read_text()

    def test_sempyro_detects_class_count(self, runner, test_excel, cli_args_with_temp_paths):
        """Test that sempyro detects and reports class count."""
        result = runner.invoke(
            sempyro,
            [
                "--input-excel",
                str(test_excel),
                "--namespace",
                "hri",
            ]
            + cli_args_with_temp_paths,
        )

        # Should report how many classes were found in the Excel file
        assert "✓ Found" in result.output
        assert "classes in Excel file" in result.output

    def test_sempyro_with_multiple_classes(self, runner, multi_excel, cli_args_with_temp_paths):
        """Test sempyro with multiple classes in input Excel."""
        result = runner.invoke(
            sempyro,
            [
                "--input-excel",
                str(multi_excel),
                "--namespace",
                "hri",
            ]
            + cli_args_with_temp_paths,
        )

        # The command should execute and begin the 4-step process for multiple classes
        assert result.output  # Has some output
        assert "[1/4] Generating LinkML schemas..." in result.output
