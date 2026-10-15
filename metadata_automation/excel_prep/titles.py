"""Check that independent classes have a title, as the FDP lists them on their own."""

from openpyxl.workbook import Workbook

from metadata_automation.excel_prep.prefix_check import expand, namespace_map
from metadata_automation.excel_prep.report import Report
from metadata_automation.excel_prep.structure import ModelClass
from metadata_automation.excel_prep.workbook import headers, property_rows, text

TITLE_PROPERTY = "dct:title"


def check_titles(wb: Workbook, model: dict[str, ModelClass], report: Report) -> None:
    """Report independent classes without a dct:title property."""
    namespaces = namespace_map(wb)
    title_iri = expand(TITLE_PROPERTY, namespaces)
    for cls in model.values():
        if not cls.independent:
            continue
        ws = wb[cls.sheet]
        cols = headers(ws)
        uris = [text(ws, r, cols.get("Property URI")) for r in property_rows(ws, cols)]
        if not any(u == TITLE_PROPERTY or (title_iri and expand(u, namespaces) == title_iri) for u in uris):
            report.issue(cls.sheet, None, "Property URI", f"independent class has no {TITLE_PROPERTY} property")
