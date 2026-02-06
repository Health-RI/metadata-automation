"""Test error handling and edge cases in CLI commands."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from click.testing import CliRunner

import metadata_automation.cli as cli_module
from metadata_automation.cli import main


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


class TestSHACLPlayErrors:
    """Test error handling in shaclplay command."""

    def test_template_not_found(self, runner, tmp_path, test_input_dir):
        """Test error when SHACLPlay template is missing."""
        # Mock template path so that the CLI thinks the template is missing
        with patch("metadata_automation.cli.Path") as mock_path_class:
            mock_template = MagicMock()
            mock_template.exists.return_value = False

            mock_file_path = MagicMock()
            mock_parent1 = MagicMock()
            mock_parent2 = MagicMock()
            mock_resolved = MagicMock()

            mock_file_path.parent = mock_parent1
            mock_parent1.parent = mock_parent2
            mock_parent2.resolve.return_value = mock_resolved
            mock_resolved.__truediv__ = lambda self, other: mock_template

            real_path = Path

            def path_side_effect(arg):
                if arg == cli_module.__file__:
                    return mock_file_path
                else:
                    return real_path(arg)

            mock_path_class.side_effect = path_side_effect

            result = runner.invoke(
                main,
                [
                    "shaclplay",
                    "-i",
                    str(test_input_dir / "test_metadata.xlsx"),
                    "-o",
                    str(tmp_path / "output"),
                ],
            )

            assert result.exit_code == 1
            assert "Error: SHACLPlay template not found" in result.output

    def test_input_excel_not_found(self, runner, tmp_path):
        """Test error when input Excel file doesn't exist."""
        result = runner.invoke(
            main,
            [
                "shaclplay",
                "-i",
                str(tmp_path / "nonexistent.xlsx"),
                "-o",
                str(tmp_path / "output"),
            ],
        )

        assert result.exit_code != 0

    def test_prefixes_sheet_not_found(self, runner, tmp_path):
        """Test error when prefixes sheet is missing."""
        # Create an Excel file without prefixes sheet
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"col": [1, 2, 3]})
        df.to_excel(test_file, sheet_name="classes", index=False)

        with patch("metadata_automation.cli.Path") as mock_path_class:
            mock_template = MagicMock()
            mock_template.exists.return_value = True

            mock_file_path = MagicMock()
            mock_parent1 = MagicMock()
            mock_parent2 = MagicMock()
            mock_resolved = MagicMock()

            mock_file_path.parent = mock_parent1
            mock_parent1.parent = mock_parent2
            mock_parent2.resolve.return_value = mock_resolved
            mock_resolved.__truediv__ = lambda self, other: mock_template

            def path_side_effect(arg):
                if arg == "__file__":
                    return mock_file_path
                else:
                    return Path(arg)

            mock_path_class.side_effect = path_side_effect

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
            assert "Error: 'prefixes' sheet not found in" in result.output

    def test_classes_sheet_not_found(self, runner, tmp_path):
        """Test error when classes sheet is missing."""
        # Create an Excel file with prefixes but no classes sheet
        test_file = tmp_path / "test.xlsx"
        with pd.ExcelWriter(test_file) as writer:
            pd.DataFrame({"prefix": ["ex"], "namespace": ["http://example.org/"]}).to_excel(
                writer, sheet_name="prefixes", index=False
            )

        with patch("metadata_automation.cli.Path") as mock_path_class:
            mock_template = MagicMock()
            mock_template.exists.return_value = True

            mock_file_path = MagicMock()
            mock_parent1 = MagicMock()
            mock_parent2 = MagicMock()
            mock_resolved = MagicMock()

            mock_file_path.parent = mock_parent1
            mock_parent1.parent = mock_parent2
            mock_parent2.resolve.return_value = mock_resolved
            mock_resolved.__truediv__ = lambda self, other: mock_template

            def path_side_effect(arg):
                if arg == "__file__":
                    return mock_file_path
                else:
                    return Path(arg)

            mock_path_class.side_effect = path_side_effect

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
            assert "Error: 'classes' sheet not found in" in result.output

    def test_classes_sheet_empty(self, runner, tmp_path):
        """Test error when classes sheet is empty."""
        test_file = tmp_path / "test.xlsx"
        with pd.ExcelWriter(test_file) as writer:
            pd.DataFrame({"prefix": ["ex"], "namespace": ["http://example.org/"]}).to_excel(
                writer, sheet_name="prefixes", index=False
            )
            pd.DataFrame(columns=["sheet_name", "class_URI"]).to_excel(writer, sheet_name="classes", index=False)

        with patch("metadata_automation.cli.Path") as mock_path_class:
            # Mock template to exist
            mock_template = MagicMock()
            mock_template.exists.return_value = True

            mock_file_path = MagicMock()
            mock_parent1 = MagicMock()
            mock_parent2 = MagicMock()
            mock_resolved = MagicMock()

            mock_file_path.parent = mock_parent1
            mock_parent1.parent = mock_parent2
            mock_parent2.resolve.return_value = mock_resolved
            mock_resolved.__truediv__ = lambda self, other: mock_template

            def path_side_effect(arg):
                if arg == "__file__":
                    return mock_file_path
                else:
                    return Path(arg)

            mock_path_class.side_effect = path_side_effect

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
            assert "Error: 'classes' sheet is empty" in result.output

    def test_missing_required_columns(self, runner, tmp_path):
        """Test error when required columns are missing in classes sheet."""
        test_file = tmp_path / "test.xlsx"
        with pd.ExcelWriter(test_file) as writer:
            pd.DataFrame({"prefix": ["ex"], "namespace": ["http://example.org/"]}).to_excel(
                writer, sheet_name="prefixes", index=False
            )
            # Missing SHACL_target_ontology_name column
            pd.DataFrame(
                {
                    "sheet_name": ["TestClass"],
                    "class_URI": ["ex:TestClass"],
                }
            ).to_excel(writer, sheet_name="classes", index=False)

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
        assert "KeyError: 'SHACL_target_ontology_name'" in result.output

    def test_class_sheet_not_found(self, runner, tmp_path):
        """Test error when a specific class sheet is missing."""
        test_file = tmp_path / "test.xlsx"
        with pd.ExcelWriter(test_file) as writer:
            pd.DataFrame({"prefix": ["ex"], "namespace": ["http://example.org/"]}).to_excel(
                writer, sheet_name="prefixes", index=False
            )
            pd.DataFrame(
                {
                    "sheet_name": ["NonExistentSheet"],
                    "class_URI": ["ex:TestClass"],
                    "SHACL_target_ontology_name": ["ex:TestClass"],
                }
            ).to_excel(writer, sheet_name="classes", index=False)

        with patch("metadata_automation.cli.Path") as mock_path_class:
            mock_template = MagicMock()
            mock_template.exists.return_value = True

            mock_file_path = MagicMock()
            mock_parent1 = MagicMock()
            mock_parent2 = MagicMock()
            mock_resolved = MagicMock()

            mock_file_path.parent = mock_parent1
            mock_parent1.parent = mock_parent2
            mock_parent2.resolve.return_value = mock_resolved
            mock_resolved.__truediv__ = lambda self, other: mock_template

            def path_side_effect(arg):
                if arg == "__file__":
                    return mock_file_path
                else:
                    return Path(arg)

            mock_path_class.side_effect = path_side_effect

            with patch("metadata_automation.cli.SHACLPlayConverter"):
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
                assert "Error: Sheet 'NonExistentSheet' not found in" in result.output


class TestSHACLFromSHACLPlayErrors:
    """Test error handling in shacl_from_shaclplay command."""

    def test_jar_not_found(self, runner, tmp_path):
        """Test error when xls2rdf JAR is missing."""
        # Mock jar path so that the CLI thinks the JAR is missing
        with patch("metadata_automation.cli.Path") as mock_path_class:
            mock_jar = MagicMock()
            mock_jar.exists.return_value = False

            mock_file_path = MagicMock()
            mock_parent1 = MagicMock()
            mock_parent2 = MagicMock()
            mock_resolved = MagicMock()

            mock_file_path.parent = mock_parent1
            mock_parent1.parent = mock_parent2
            mock_parent2.resolve.return_value = mock_resolved
            mock_resolved.__truediv__ = lambda self, other: mock_jar

            real_path = Path

            def path_side_effect(arg):
                if arg == cli_module.__file__:
                    return mock_file_path
                else:
                    return real_path(arg)

            mock_path_class.side_effect = path_side_effect

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
            assert "Error: xls2rdf JAR not found" in result.output

    def test_no_excel_files_found(self, runner, tmp_path):
        """Test error when no SHACLPlay Excel files are found."""
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
        assert "No SHACLPlay Excel files found" in result.output

    def test_nodeshapes_sheet_not_found(self, runner, tmp_path):
        """Test error when NodeShapes sheet is missing."""
        # Create a SHACLPlay Excel file without NodeShapes sheet
        test_file = tmp_path / "SHACL-test.xlsx"
        df = pd.DataFrame({"col": [1, 2, 3]})
        df.to_excel(test_file, sheet_name="SomeSheet", index=False)

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
        assert "Error: 'NodeShapes (classes)' sheet not found in" in result.output

    def test_subprocess_error(self, runner, tmp_path):
        """Test error when xls2rdf subprocess fails."""
        # Create a proper SHACLPlay Excel file
        test_file = tmp_path / "SHACL-test.xlsx"
        df = pd.DataFrame([[None] * 20 for _ in range(20)])
        df.iloc[13, 0] = "ex:TestClass"
        df.to_excel(test_file, sheet_name="NodeShapes (classes)", index=False, header=False)

        # Mock subprocess to raise CalledProcessError
        with patch("metadata_automation.cli.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1,
                cmd=["java"],
                output="some output",
                stderr="some error",
            )

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
            assert "Error: Failed to convert" in result.output


class TestSeMPyROErrors:
    """Test error handling in sempyro command."""

    def test_namespace_auto_detect_no_class_uri(self, runner, tmp_path):
        """Test error when class_URI column is missing for auto-detection."""
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"sheet_name": ["TestClass"]})
        df.to_excel(test_file, sheet_name="classes", index=False)

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
        assert "Error: 'class_URI' column not found in classes sheet" in result.output

    def test_namespace_auto_detect_cannot_parse(self, runner, tmp_path):
        """Test error when namespace cannot be parsed from class_URI."""
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"class_URI": ["NoColonInURI"]})
        df.to_excel(test_file, sheet_name="classes", index=False)

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
        assert "Warning: Could not parse namespace from class_URI" in result.output

    def test_imports_file_not_found(self, runner, tmp_path):
        """Test error when imports file doesn't exist."""
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"class_URI": ["ex:TestClass"]})
        df.to_excel(test_file, sheet_name="classes", index=False)

        with patch("metadata_automation.cli.LinkMLCreator"):
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
                    "--imports-path",
                    str(tmp_path / "nonexistent.yaml"),
                ],
            )

            assert result.exit_code != 0
            assert "nonexistent.yaml' does not exist" in result.output

    def test_linkml_generation_error(self, runner, tmp_path):
        """Test error during LinkML generation."""
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"class_URI": ["ex:TestClass"]})
        df.to_excel(test_file, sheet_name="classes", index=False)

        imports_file = tmp_path / "imports.yaml"
        imports_file.write_text("ex-TestClass:\n  - import: something\n")

        with patch("metadata_automation.cli.LinkMLCreator") as mock_creator_class:
            mock_creator = MagicMock()
            mock_creator.build_sempyro.side_effect = Exception("LinkML build failed")
            mock_creator_class.return_value = mock_creator

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
                    "--imports-path",
                    str(imports_file),
                ],
            )

            assert result.exit_code == 1
            assert "Error: Failed to generate LinkML schemas" in result.output

    def test_schema_file_not_found(self, runner, tmp_path):
        """Test error when schema file doesn't exist for a class."""
        test_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"class_URI": ["ex:TestClass"]})
        df.to_excel(test_file, sheet_name="classes", index=False)

        imports_file = tmp_path / "imports.yaml"
        imports_file.write_text("ex-TestClass:\n  - import: something\n")

        # Mock LinkML creator
        with patch("metadata_automation.cli.LinkMLCreator") as mock_creator_class:
            mock_creator = MagicMock()
            mock_creator_class.return_value = mock_creator

            # Mock load_yaml to return imports
            with patch("metadata_automation.cli.load_yaml") as mock_load:
                mock_load.return_value = {"ex-TestClass": ["import: something"]}

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
                assert "Error: Schema file not found for" in result.output

    def test_ruff_not_found_warning(self, runner, tmp_path, test_input_dir):
        """Test warning when ruff is not found."""
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

        with patch("metadata_automation.cli.LinkMLCreator") as mock_creator_class:
            mock_creator = MagicMock()
            mock_creator_class.return_value = mock_creator

            with patch("metadata_automation.cli.load_yaml") as mock_load:
                mock_load.return_value = {"ex-TestClass": ["import: something"]}

                with patch("metadata_automation.cli.generate_from_linkml"):
                    with patch("metadata_automation.cli.remove_unwanted_classes"):
                        with patch("metadata_automation.cli.subprocess.run") as mock_run:
                            mock_run.side_effect = FileNotFoundError("ruff not found")

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
                            assert "Warning: ruff not found. Install with: pip install ruff" in result.output
