import logging
from typing import Union

from pydantic import ConfigDict, Field
from rdflib.namespace import DCTERMS
from sempyro import LiteralField, RDFModel

metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRITestclass(RDFModel):
    """
    A test class
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "http://example.com/ontology",
            "$namespace": str(HRI),
            "$IRI": "http://example.com/TestClass",
            "$prefix": "hri",
        },
    )
    title: list[Union[LiteralField, str]] = Field(
        description="""The title""", json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"}
    )

    description: list[Union[LiteralField, str]] = Field(
        description="""The description""",
        json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "rdfs_literal"},
    )
