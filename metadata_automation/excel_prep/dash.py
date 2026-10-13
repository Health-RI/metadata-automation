"""Expected DASH viewer and editor for a property, derived from its range."""

from metadata_automation.excel_prep.workbook import IRI_SUFFIX

URI = ("dash:URIViewer", "dash:URIEditor")
DETAILS = ("dash:DetailsViewer", "dash:BlankNodeEditor")
DATE_TIME = ("dash:LiteralViewer", "dash:DateTimePickerEditor")
TEXT_AREA = ("dash:LiteralViewer", "dash:TextAreaEditor")
TEXT_FIELD = ("dash:LiteralViewer", "dash:TextFieldEditor")

DESCRIPTION_PROPERTY = "dct:description"


def expected_dash(range_: str, node: str, is_description: bool) -> tuple[str, str] | None:
    """Return ``(viewer, editor)`` for a prepared range, or None when no rule applies.

    Rules, in order: a range ending in (IRI) is a URI; a range with a node shape
    links to another class of the model; xsd:dateTime gets a date picker;
    dct:description gets a text area; any other literal gets a text field.
    """
    range_ = range_.strip()
    if range_.endswith(IRI_SUFFIX):
        return URI
    if node:
        return DETAILS
    if range_ == "xsd:dateTime":
        return DATE_TIME
    if range_.startswith(("xsd:", "rdfs:Literal")):
        return TEXT_AREA if is_description else TEXT_FIELD
    return None
