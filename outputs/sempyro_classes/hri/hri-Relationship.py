from pathlib import Path
from typing import List

from pydantic import AnyHttpUrl, ConfigDict, Field
from rdflib.namespace import DCAT, DCTERMS
from sempyro import RDFModel


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIRelationship(RDFModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vocab-dcat-3/",
            "$namespace": str(HRI),
            "$IRI": "DCAT.Relationship",
            "$prefix": "hri",
        },
    )
    had_role: list[AnyHttpUrl] = Field(
        description="""The function of an entity or agent with respect to another entity or resource.""",
        json_schema_extra={"rdf_term": DCAT.hadRole, "rdf_type": "uri"},
    )

    relation: list[AnyHttpUrl] = Field(
        description="""A related resource.""",
        json_schema_extra={"rdf_term": DCTERMS.relation, "rdf_type": "uri"},
    )
