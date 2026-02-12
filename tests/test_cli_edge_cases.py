"""Tests for CLI edge cases and exceptional scenarios."""

import subprocess
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from metadata_automation.cli import main


class TestSHACLPlayEdgeCases:
    """Tests for shaclplay command edge cases."""

    def test_generic_exception_reading_prefixes(self, runner, tmp_path):
        """Test generic exception when reading prefixes sheet."""
        test_file = tmp_path / "test.xlsx"
        # Create a valid Excel file but mock to raise generic exception
        with pd.ExcelWriter(test_file) as writer:
            pd.DataFrame({"col": [1]}).to_excel(writer, sheet_name="dummy", index=False)

        # Mock to raise generic exception (not ValueError)
        original_read_excel = pd.read_excel

        def mock_read_excel(*args, **kwargs):
            sheet_name = kwargs.get("sheet_name")
            if sheet_name == "prefixes":
                raise RuntimeError("Generic read error")
            return original_read_excel(*args, **kwargs)

        with patch("metadata_automation.cli.pd.read_excel", side_effect=mock_read_excel):
            result = runner.invoke(
                main,
                [
                    "shaclplay",
                    "-i",
                    str(test_file),
                    "-o",
                    str(tmp_path / "output"),
                ],
            )

        assert result.exit_code == 1
        assert "Error: Failed to read prefixes sheet" in result.output

    def test_generic_exception_reading_classes(self, runner, tmp_path):
        """Test generic exception when reading classes sheet."""
        test_file = tmp_path / "test.xlsx"
        # Create Excel with prefixes but make classes unreadable somehow
        with pd.ExcelWriter(test_file) as writer:
            pd.DataFrame({"prefix": ["ex"], "namespace": ["http://example.org/"]}).to_excel(
                writer, sheet_name="prefixes", index=False
            )

        # Mock pd.read_excel to raise generic exception for classes sheet only
        original_read_excel = pd.read_excel
        call_count = [0]

        def mock_read_excel(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call is for classes sheet
                raise RuntimeError("Simulated generic error")
            return original_read_excel(*args, **kwargs)

        with patch("metadata_automation.cli.pd.read_excel", side_effect=mock_read_excel):
            result = runner.invoke(
                main,
                [
                    "shaclplay",
                    "-i",
                    str(test_file),
                    "-o",
                    str(tmp_path / "output"),
                ],
            )

        assert result.exit_code == 1
        assert "Error: Failed to read classes sheet" in result.output

    @pytest.mark.parametrize(
        "missing_column,expected_error",
        [
            ("sheet_name", "Error: Row 0 missing 'sheet_name' column"),
            ("class_URI", "Error: Row 0 missing 'class_URI' column"),
        ],
    )
    def test_missing_column_in_row(self, runner, tmp_path, missing_column, expected_error):
        """Test error when required column is NaN in a row."""
        test_file = tmp_path / "test.xlsx"
        with pd.ExcelWriter(test_file) as writer:
            pd.DataFrame({"prefix": ["ex"], "namespace": ["http://example.org/"]}).to_excel(
                writer, sheet_name="prefixes", index=False
            )
            # Create classes with NaN in the specified column
            class_data = {
                "sheet_name": ["TestClass"] if missing_column != "sheet_name" else [None],
                "class_URI": ["ex:TestClass"] if missing_column != "class_URI" else [None],
                "SHACL_target_ontology_name": ["ex:TestClass"],
            }
            pd.DataFrame(class_data).to_excel(writer, sheet_name="classes", index=False)

        result = runner.invoke(
            main,
            [
                "shaclplay",
                "-i",
                str(test_file),
                "-o",
                str(tmp_path / "output"),
            ],
        )

        assert result.exit_code == 1
        assert expected_error in result.output

    def test_generic_exception_reading_class_sheet(self, runner, tmp_path):
        """Test generic exception when reading a specific class sheet."""
        test_file = tmp_path / "test.xlsx"
        with pd.ExcelWriter(test_file) as writer:
            pd.DataFrame({"prefix": ["ex"], "namespace": ["http://example.org/"]}).to_excel(
                writer, sheet_name="prefixes", index=False
            )
            pd.DataFrame(
                {
                    "sheet_name": ["TestClass"],
                    "class_URI": ["ex:TestClass"],
                    "SHACL_target_ontology_name": ["ex:TestClass"],
                }
            ).to_excel(writer, sheet_name="classes", index=False)

        # Mock read_excel to raise generic exception for TestClass sheet
        original_read_excel = pd.read_excel

        def mock_read_excel(*args, **kwargs):
            sheet_name = kwargs.get("sheet_name")
            if sheet_name == "TestClass":
                raise RuntimeError("Simulated error reading class sheet")
            return original_read_excel(*args, **kwargs)

        with patch("metadata_automation.cli.pd.read_excel", side_effect=mock_read_excel):
            result = runner.invoke(
                main,
                [
                    "shaclplay",
                    "-i",
                    str(test_file),
                    "-o",
                    str(tmp_path / "output"),
                ],
            )

        assert result.exit_code == 1
        assert "Error: Failed to read sheet 'TestClass'" in result.output


class TestSHACLFromSHACLPlayEdgeCases:
    """Tests for shacl_from_shaclplay command edge cases."""

    def test_generic_exception_reading_excel(self, runner, tmp_path):
        """Test generic exception when reading Excel file."""
        test_file = tmp_path / "SHACL-test.xlsx"
        # Create valid Excel but mock to raise generic exception
        with pd.ExcelWriter(test_file) as writer:
            pd.DataFrame({"col": [1]}).to_excel(writer, sheet_name="dummy", index=False)

        # Mock to raise generic exception
        original_read_excel = pd.read_excel

        def mock_read_excel(*args, **kwargs):
            if "SHACL-test.xlsx" in str(args[0]):
                raise RuntimeError("Generic read error")
            return original_read_excel(*args, **kwargs)

        with patch("metadata_automation.cli.pd.read_excel", side_effect=mock_read_excel):
            result = runner.invoke(
                main,
                [
                    "shacl-from-shaclplay",
                    "-i",
                    str(tmp_path),
                    "-o",
                    str(tmp_path / "output"),
                ],
            )

        assert result.exit_code == 1
        assert "Error: Failed to read SHACL-test.xlsx" in result.output

    def test_exception_extracting_namespace(self, runner, tmp_path):
        """Test exception when extracting namespace from Excel."""
        test_file = tmp_path / "SHACL-test.xlsx"
        # Create Excel with NodeShapes but make iloc raise exception
        df = pd.DataFrame([[None] * 5 for _ in range(10)])  # Too few rows
        df.to_excel(test_file, sheet_name="NodeShapes (classes)", index=False, header=False)

        result = runner.invoke(
            main,
            [
                "shacl-from-shaclplay",
                "-i",
                str(tmp_path),
                "-o",
                str(tmp_path / "output"),
            ],
        )

        assert result.exit_code == 1
        assert "Error: Could not extract namespace from SHACL-test.xlsx" in result.output

    @pytest.mark.parametrize(
        "stdout_content,stderr_content,expected_in_output",
        [
            ("Some output from xls2rdf", "", "Output: Some output from xls2rdf"),
            ("", "Warning: some warning", "Warnings: Warning: some warning"),
        ],
    )
    def test_subprocess_success_output_handling(
        self, runner, tmp_path, stdout_content, stderr_content, expected_in_output
    ):
        """Test subprocess success with different output scenarios."""
        test_file = tmp_path / "SHACL-test.xlsx"
        df = pd.DataFrame([[None] * 20 for _ in range(20)])
        df.iloc[13, 0] = "ex:TestClass"
        df.to_excel(test_file, sheet_name="NodeShapes (classes)", index=False, header=False)

        with patch("metadata_automation.cli.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = stdout_content
            mock_result.stderr = stderr_content
            mock_run.return_value = mock_result

            result = runner.invoke(
                main,
                [
                    "shacl-from-shaclplay",
                    "-i",
                    str(tmp_path),
                    "-o",
                    str(tmp_path / "output"),
                ],
            )

            assert expected_in_output in result.output

    def test_subprocess_error_with_stdout(self, runner, tmp_path):
        """Test subprocess error with stdout."""
        test_file = tmp_path / "SHACL-test.xlsx"
        df = pd.DataFrame([[None] * 20 for _ in range(20)])
        df.iloc[13, 0] = "ex:TestClass"
        df.to_excel(test_file, sheet_name="NodeShapes (classes)", index=False, header=False)

        with patch("metadata_automation.cli.subprocess.run") as mock_run:
            error = subprocess.CalledProcessError(
                returncode=1,
                cmd=["java"],
            )
            error.stdout = "stdout content"
            error.stderr = "stderr content"
            mock_run.side_effect = error

            result = runner.invoke(
                main,
                [
                    "shacl-from-shaclplay",
                    "-i",
                    str(tmp_path),
                    "-o",
                    str(tmp_path / "output"),
                ],
            )

            assert result.exit_code == 1
            assert "stdout: stdout content" in result.output
            assert "stderr: stderr content" in result.output


class TestSeMPyROEdgeCases:
    """Tests for sempyro command edge cases."""

    def test_generic_exception_auto_detecting_namespace(self, runner, tmp_path):
        """Test generic exception during namespace auto-detection."""
        test_file = tmp_path / "test.xlsx"
        # Create corrupted file that will cause generic exception
        test_file.write_text("not valid excel")

        result = runner.invoke(
            main,
            [
                "sempyro",
                "-i",
                str(test_file),
                "--linkml-output-path",
                str(tmp_path / "linkml"),
                "--sempyro-output-path",
                str(tmp_path / "sempyro"),
            ],
        )

        assert result.exit_code == 1
        assert "Error reading classes sheet:" in result.output

    def test_generic_exception_in_linkml_generation(self, runner, tmp_path):
        """Test generic exception in LinkML generation."""
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"class_URI": ["ex:TestClass"]})
        df.to_excel(test_file, sheet_name="classes", index=False)

        imports_file = tmp_path / "imports.yaml"
        imports_file.write_text("ex-TestClass:\n  - import: something\n")

        # Mock LinkMLCreator to raise exception in build_sempyro
        with patch("metadata_automation.cli.LinkMLCreator") as mock_creator_class:
            mock_creator = MagicMock()
            mock_creator.build_sempyro.side_effect = RuntimeError("Generic LinkML error")
            mock_creator_class.return_value = mock_creator

            result = runner.invoke(
                main,
                [
                    "sempyro",
                    "-i",
                    str(test_file),
                    "--namespace",
                    "ex",
                    "--linkml-output-path",
                    str(tmp_path / "linkml"),
                    "--sempyro-output-path",
                    str(tmp_path / "sempyro"),
                    "--imports-path",
                    str(imports_file),
                ],
            )

            assert result.exit_code == 1
            assert "Error: Failed to generate LinkML schemas" in result.output

    def test_generic_exception_loading_imports(self, runner, tmp_path):
        """Test generic exception when loading imports file."""
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"class_URI": ["ex:TestClass"]})
        df.to_excel(test_file, sheet_name="classes", index=False)

        imports_file = tmp_path / "imports.yaml"
        imports_file.write_text("invalid: [unclosed list")

        with patch("metadata_automation.cli.LinkMLCreator"):
            result = runner.invoke(
                main,
                [
                    "sempyro",
                    "-i",
                    str(test_file),
                    "--namespace",
                    "ex",
                    "--linkml-output-path",
                    str(tmp_path / "linkml"),
                    "--sempyro-output-path",
                    str(tmp_path / "sempyro"),
                    "--imports-path",
                    str(imports_file),
                ],
            )

            assert result.exit_code == 1
            assert "Error: Failed to load imports configuration" in result.output

    def test_generic_exception_in_generate_from_linkml(self, runner, tmp_path):
        """Test generic exception in generate_from_linkml."""
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"class_URI": ["ex:TestClass"]})
        df.to_excel(test_file, sheet_name="classes", index=False)

        imports_file = tmp_path / "imports.yaml"
        imports_file.write_text("ex-TestClass:\n  - import: something\n")

        # Create the schema file
        schema_dir = tmp_path / "linkml" / "ex"
        schema_dir.mkdir(parents=True)
        schema_file = schema_dir / "ex-TestClass.yaml"
        schema_file.write_text("classes:\n  TestClass:\n    attributes:\n      name:\n        range: string\n")

        with patch("metadata_automation.cli.LinkMLCreator"):
            with patch("metadata_automation.cli.load_yaml") as mock_load:
                mock_load.return_value = {"ex-TestClass": ["import"]}

                with patch("metadata_automation.cli.generate_from_linkml") as mock_gen:
                    mock_gen.side_effect = RuntimeError("Error generating from LinkML")

                    result = runner.invoke(
                        main,
                        [
                            "sempyro",
                            "-i",
                            str(test_file),
                            "--namespace",
                            "ex",
                            "--linkml-output-path",
                            str(tmp_path / "linkml"),
                            "--sempyro-output-path",
                            str(tmp_path / "sempyro"),
                            "--imports-path",
                            str(imports_file),
                        ],
                    )

                    assert result.exit_code == 1
                    assert "Error: Failed to generate TestClass" in result.output

    def test_ruff_format_with_stdout(self, runner, tmp_path):
        """Test ruff formatting with stdout output."""
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"class_URI": ["ex:TestClass"]})
        df.to_excel(test_file, sheet_name="classes", index=False)

        imports_file = tmp_path / "imports.yaml"
        imports_file.write_text("ex-TestClass:\n  - import: something\n")

        # Create the schema file
        schema_dir = tmp_path / "linkml" / "ex"
        schema_dir.mkdir(parents=True)
        schema_file = schema_dir / "ex-TestClass.yaml"
        schema_file.write_text("classes:\n  TestClass:\n    attributes:\n      name:\n        range: string\n")

        with patch("metadata_automation.cli.LinkMLCreator"):
            with patch("metadata_automation.cli.load_yaml") as mock_load:
                mock_load.return_value = {"ex-TestClass": ["import"]}

                with patch("metadata_automation.cli.generate_from_linkml"):
                    with patch("metadata_automation.cli.remove_unwanted_classes"):
                        with patch("metadata_automation.cli.subprocess.run") as mock_run:
                            mock_result = MagicMock()
                            mock_result.stdout = "1 file reformatted"
                            mock_run.return_value = mock_result

                            result = runner.invoke(
                                main,
                                [
                                    "sempyro",
                                    "-i",
                                    str(test_file),
                                    "--namespace",
                                    "ex",
                                    "--linkml-output-path",
                                    str(tmp_path / "linkml"),
                                    "--sempyro-output-path",
                                    str(tmp_path / "sempyro"),
                                    "--imports-path",
                                    str(imports_file),
                                ],
                            )

                            assert result.exit_code == 0
                            assert "1 file reformatted" in result.output

    def test_ruff_subprocess_error_with_stderr(self, runner, tmp_path):
        """Test ruff subprocess error with stderr."""
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"class_URI": ["ex:TestClass"]})
        df.to_excel(test_file, sheet_name="classes", index=False)

        imports_file = tmp_path / "imports.yaml"
        imports_file.write_text("ex-TestClass:\n  - import: something\n")

        # Create the schema file
        schema_dir = tmp_path / "linkml" / "ex"
        schema_dir.mkdir(parents=True)
        schema_file = schema_dir / "ex-TestClass.yaml"
        schema_file.write_text("classes:\n  TestClass:\n    attributes:\n      name:\n        range: string\n")

        with patch("metadata_automation.cli.LinkMLCreator"):
            with patch("metadata_automation.cli.load_yaml") as mock_load:
                mock_load.return_value = {"ex-TestClass": ["import"]}

                with patch("metadata_automation.cli.generate_from_linkml"):
                    with patch("metadata_automation.cli.remove_unwanted_classes"):
                        with patch("metadata_automation.cli.subprocess.run") as mock_run:
                            error = subprocess.CalledProcessError(returncode=1, cmd=["ruff"])
                            error.stderr = "ruff error message"
                            mock_run.side_effect = error

                            result = runner.invoke(
                                main,
                                [
                                    "sempyro",
                                    "-i",
                                    str(test_file),
                                    "--namespace",
                                    "ex",
                                    "--linkml-output-path",
                                    str(tmp_path / "linkml"),
                                    "--sempyro-output-path",
                                    str(tmp_path / "sempyro"),
                                    "--imports-path",
                                    str(imports_file),
                                ],
                            )

                            assert result.exit_code == 0  # Warning, not error
                            assert "Warning: ruff format failed" in result.output
                            assert "ruff error message" in result.output
