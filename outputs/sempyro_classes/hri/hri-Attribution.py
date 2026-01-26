from pathlib import Path
from typing import Union

from pydantic import AnyHttpUrl, ConfigDict, Field
from rdflib.namespace import DCAT, PROV
from sempyro import RDFModel
from sempyro.foaf import Agent


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIAttribution(RDFModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/prov-o/",
            "$namespace": str(HRI),
            "$IRI": "PROV.Attribution",
            "$prefix": "hri",
        },
    )
    agent: Optional[Union[Agent, AnyHttpUrl]] = Field(
        default=None,
        description="""The prov:agent property references an prov:Agent which influenced a resource.""",
        json_schema_extra={"rdf_term": PROV.agent, "rdf_type": "uri"},
    )

    role: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The function of an entity or agent with respect to another entity or resource.""",
        json_schema_extra={"rdf_term": DCAT.hadRole, "rdf_type": "uri"},
    )
