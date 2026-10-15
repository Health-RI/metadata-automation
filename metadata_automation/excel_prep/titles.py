"""Check that independent classes have a title, as the FDP lists them on their own."""

from openpyxl.workbook import Workbook

from metadata_automation.excel_prep.prefix_check import namespace_map, same_term
from metadata_automation.excel_prep.report import Report
from metadata_automation.excel_prep.structure import ModelClass
from metadata_automation.excel_prep.workbook import headers, property_rows, text

TITLE_PROPERTY = "dct:title"


def check_titles(wb: Workbook, model: dict[str, ModelClass], report: Report) -> None:
    """Report independent classes without a dct:title property."""
    namespaces = namespace_map(wb)
    for cls in model.values():
        if not cls.independent:
            continue
        ws = wb[cls.sheet]
        cols = headers(ws)
        uris = [text(ws, r, cols.get("Property URI")) for r in property_rows(ws, cols)]
        if not any(same_term(u, TITLE_PROPERTY, namespaces) for u in uris):
            report.issue(cls.sheet, None, "Property URI", f"independent class has no {TITLE_PROPERTY} property")
