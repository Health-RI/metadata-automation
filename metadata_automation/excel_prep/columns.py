"""Sheets and columns the prepared workbook must have."""

BASE_COLUMNS = [
    "Property label",
    "Definition",
    "Property URI",
    "Controlled vocabulary (if applicable)",
    "Usage note",
    "Range",
    "Cardinality",
]
CLASS_SHEET_COLUMNS = [
    "SHACL_sh:node",
    "SHACL_dash:viewer",
    "SHACL_dash:editor",
    "SHACL_pattern",
    "SHACL_default_value",
    "SHACL_sh:uniqueLang",
    "SeMPyRO_rdf_term",
    "SeMPyRO_rdf_type",
    "SeMPyRO_range",
]
CLASSES_COLUMNS = [
    "sheet_name",
    "description",
    "class_URI",
    "SHACL_target_ontology_name",
    "SHACL_independent_class",
    "SeMPyRO_inherits_from",
    "SeMPyRO_import_classes",
    "SeMPyRO_annotations_ontology",
    "SeMPyRO_annotations_IRI",
    "SeMPyRO_add_rdf_model",
]
PREFIXES_COLUMNS = ["prefix", "namespace"]

REQUIRED_CLASSES_COLUMNS = [
    "class_URI",
    "SHACL_target_ontology_name",
    "SeMPyRO_annotations_ontology",
    "SeMPyRO_annotations_IRI",
]
OPTIONAL_CLASSES_COLUMNS = [
    "description",
    "SHACL_independent_class",
    "SeMPyRO_inherits_from",
    "SeMPyRO_import_classes",
    "SeMPyRO_add_rdf_model",
]
REQUIRED_PROPERTY_COLUMNS = ["SeMPyRO_rdf_term", "SeMPyRO_rdf_type", "SeMPyRO_range"]
OPTIONAL_PROPERTY_COLUMNS = [
    "SHACL_dash:viewer",
    "SHACL_dash:editor",
    "SHACL_pattern",
    "SHACL_default_value",
    "SHACL_sh:uniqueLang",
]

GENERAL_SHEETS = ["prefixes", "classes"]
FDP_SHEETS = ["Resource"]
SHEET_COLUMNS = {"prefixes": PREFIXES_COLUMNS, "classes": CLASSES_COLUMNS, "Resource": BASE_COLUMNS}
