"""Fixtures for the Excel preparation tests."""

import pytest
from openpyxl import load_workbook
from prep_helpers import answer_classes

from metadata_automation.excel_prep.fdp import derive_fdp_workbook


@pytest.fixture
def plain_small(test_input_dir):
    return test_input_dir / "plain_small.xlsx"


@pytest.fixture
def plain_metadata(test_input_dir):
    return test_input_dir / "plain_metadata.xlsx"


@pytest.fixture
def second_pass(plain_small, tmp_path):
    """Prepare, answer the class questions, and derive the FDP variant."""
    first = tmp_path / "first.xlsx"
    derive_fdp_workbook(plain_small, first)
    answer_classes(first)
    second = tmp_path / "second.xlsx"
    report = derive_fdp_workbook(first, second)
    return report, load_workbook(second), second
