"""check-excel: passes when the plan is empty, otherwise fails and says what to do."""

import shutil

import pytest
from prep_helpers import CLASS_ANSWERS, answer_classes, fill_reported_gaps, sha

from metadata_automation.cli import check_excel
from metadata_automation.excel_prep.check import DEFAULT_HINT, format_check
from metadata_automation.excel_prep.plan import compute_plan, default_plan_path
from metadata_automation.excel_prep.preparer import prepare_workbook


@pytest.fixture
def source(plain_small, tmp_path):
    path = tmp_path / "model.xlsx"
    shutil.copy(plain_small, path)
    return path


@pytest.fixture
def complete(source):
    """Prepared, class questions answered and every required cell filled in."""
    prepare_workbook(source)
    answer_classes(source, {k: v for k, v in CLASS_ANSWERS.items() if k != "Resource"})
    prepare_workbook(source)
    fill_reported_gaps(source)
    prepare_workbook(source)
    return source


class TestCheckCommand:
    def test_passes_on_a_correct_and_complete_workbook(self, runner, complete):
        result = runner.invoke(check_excel, ["-i", str(complete)])
        assert result.exit_code == 0, result.output
        assert "Excel check passed" in result.output

    def test_fails_on_pending_edits_and_names_the_remedy(self, runner, source):
        result = runner.invoke(check_excel, ["-i", str(source)])
        assert result.exit_code == 1
        assert "Excel check failed for `model.xlsx`" in result.output
        assert "edit(s) pending" in result.output
        assert DEFAULT_HINT in result.output

    def test_fails_on_required_gaps_alone(self, runner, source):
        prepare_workbook(source)
        result = runner.invoke(check_excel, ["-i", str(source)])
        assert result.exit_code == 1
        assert "0 edit(s) pending" in result.output
        assert "### Required cells to fill in" in result.output

    def test_custom_hint(self, runner, source):
        result = runner.invoke(check_excel, ["-i", str(source), "--hint", "Run the Plan columns workflow."])
        assert "Run the Plan columns workflow." in result.output
        assert DEFAULT_HINT not in result.output

    def test_source_is_not_modified(self, runner, source):
        before = sha(source)
        runner.invoke(check_excel, ["-i", str(source)])
        assert sha(source) == before

    def test_summary_file_is_appended(self, runner, source, tmp_path):
        summary = tmp_path / "summary.md"
        summary.write_text("# earlier step\n")
        runner.invoke(check_excel, ["-i", str(source), "--summary", str(summary)])
        text = summary.read_text()
        assert text.startswith("# earlier step\n")
        assert "Excel check failed" in text

    def test_unreadable_input_is_an_error_not_a_failed_check(self, runner, tmp_path):
        bad = tmp_path / "bad.xlsx"
        bad.write_text("not an excel file")
        result = runner.invoke(check_excel, ["-i", str(bad)])
        assert result.exit_code == 2
        assert "Error" in result.output


class TestFormat:
    def test_mentions_a_pending_plan_next_to_the_source(self, source):
        plan, _ = compute_plan(source)
        default_plan_path(source).write_bytes(b"x")
        assert "already next to the source" in format_check(plan, source=source)

    def test_long_lists_are_truncated(self, plain_metadata):
        plan, _ = compute_plan(plain_metadata)
        assert len(plan.edits) > 40
        result = format_check(plan)
        assert f"…and {len(plan.edits) - 40} more." in result

    def test_table_cells_are_escaped(self, source):
        plan, _ = compute_plan(source)
        edit = plan.edits[0]
        object.__setattr__(edit, "old", "a|b")
        assert "a\\|b" in format_check(plan)
