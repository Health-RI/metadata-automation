"""Shared pytest fixtures and configuration for metadata-automation tests."""

from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture(scope="session")
def tests_dir():
    """Path to the tests directory."""
    return Path(__file__).resolve().parent


@pytest.fixture(scope="session")
def test_input_dir(tests_dir):
    """Path to static test input files."""
    return tests_dir / "test_input"


@pytest.fixture(scope="session")
def test_expected_dir(tests_dir):
    """Path to static expected output files."""
    return tests_dir / "test_expected"


@pytest.fixture(scope="session")
def test_imports_path(test_input_dir):
    """Path to test imports configuration."""
    imports_path = test_input_dir / "imports.yaml"
    if not imports_path.exists():
        pytest.skip("test imports.yaml not found")
    return imports_path


@pytest.fixture(scope="session")
def template_file():
    """Path to SHACLPlay template."""
    template_path = Path(__file__).resolve().parent.parent / "inputs" / "shacls" / "shaclplay-template.xlsx"
    if not template_path.exists():
        pytest.skip("SHACLPlay template not found")
    return template_path


@pytest.fixture(scope="session")
def xls2rdf_jar():
    """Path to xls2rdf JAR file."""
    jar_path = Path(__file__).resolve().parent.parent / "inputs" / "shacls" / "xls2rdf-app-3.2.1-onejar.jar"
    if not jar_path.exists():
        pytest.skip("xls2rdf JAR not found")
    return jar_path


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()
