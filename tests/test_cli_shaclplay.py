from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from metadata_automation.cli import shaclplay


class TestShaclplayCLI:
    """Integration tests for shaclplay CLI command."""

    @pytest.fixture
    def test_excel(self, test_input_dir):
        """Path to the standard test Excel input file."""
        return test_input_dir / "test_metadata.xlsx"

    def _assert_excel_matches(self, actual_path: Path, expected_path: Path) -> None:
        """Compare generated Excel output against expected, ignoring dynamic timestamps."""
        actual_sheets = pd.ExcelFile(actual_path).sheet_names
        expected_sheets = pd.ExcelFile(expected_path).sheet_names
        assert actual_sheets == expected_sheets

        for sheet_name in expected_sheets:
            actual_df = pd.read_excel(actual_path, sheet_name=sheet_name, header=None)
            expected_df = pd.read_excel(expected_path, sheet_name=sheet_name, header=None)

            if sheet_name == "NodeShapes (classes)":
                if actual_df.shape[0] > 6 and actual_df.shape[1] > 1:
                    actual_df.iat[6, 1] = None
                if expected_df.shape[0] > 6 and expected_df.shape[1] > 1:
                    expected_df.iat[6, 1] = None

            assert_frame_equal(actual_df, expected_df, check_dtype=False)

    def test_shaclplay_success(self, runner, test_excel, tmp_path):
        """Test successful SHACLPlay generation."""
        output_dir = tmp_path / "output"

        result = runner.invoke(shaclplay, ["--input-excel", str(test_excel), "--output-path", str(output_dir)])

        assert result.exit_code == 0

        output_file = output_dir / "SHACL-testclass.xlsx"
        assert output_file.exists()

        expected_file = Path(__file__).resolve().parent / "test_expected" / "default" / "SHACL-testclass.xlsx"
        self._assert_excel_matches(output_file, expected_file)

    def test_shaclplay_missing_excel(self, runner, tmp_path):
        """Test error handling for missing input file."""
        result = runner.invoke(shaclplay, ["--input-excel", "nonexistent.xlsx", "--output-path", str(tmp_path)])

        assert result.exit_code != 0
        assert "not found" in result.output or "does not exist" in result.output

    def test_shaclplay_missing_prefixes_sheet(self, runner, test_input_dir, tmp_path):
        """Test error handling for missing prefixes sheet."""
        excel_path = test_input_dir / "bad_metadata.xlsx"

        result = runner.invoke(shaclplay, ["--input-excel", str(excel_path), "--output-path", str(tmp_path / "output")])

        assert result.exit_code != 0
        assert "'prefixes' sheet not found" in result.output.lower()

    def test_shaclplay_namespace_override(self, runner, test_excel, test_expected_dir, tmp_path):
        """Test namespace override functionality."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            shaclplay, ["--input-excel", str(test_excel), "--output-path", str(output_dir), "--namespace", "custom"]
        )

        assert result.exit_code == 0

        output_file = output_dir / "SHACL-testclass.xlsx"
        expected_file = test_expected_dir / "namespace_override" / "SHACL-testclass.xlsx"
        self._assert_excel_matches(output_file, expected_file)

    def test_shaclplay_multiple_classes(self, runner, test_input_dir, test_expected_dir, tmp_path):
        """Test processing multiple classes."""
        excel_path = test_input_dir / "multi_metadata.xlsx"

        output_dir = tmp_path / "output"
        result = runner.invoke(shaclplay, ["--input-excel", str(excel_path), "--output-path", str(output_dir)])

        assert result.exit_code == 0

        actual_classa = output_dir / "SHACL-classa.xlsx"
        actual_classb = output_dir / "SHACL-classb.xlsx"
        expected_classa = test_expected_dir / "multi" / "SHACL-classa.xlsx"
        expected_classb = test_expected_dir / "multi" / "SHACL-classb.xlsx"

        assert actual_classa.exists()
        assert actual_classb.exists()

        self._assert_excel_matches(actual_classa, expected_classa)
        self._assert_excel_matches(actual_classb, expected_classb)
