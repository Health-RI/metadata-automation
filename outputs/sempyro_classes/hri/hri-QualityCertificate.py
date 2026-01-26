from pathlib import Path

from pydantic import AnyHttpUrl, ConfigDict, Field
from sempyro import RDFModel
from sempyro.namespaces import DQV, OA


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIQualitycertificate(RDFModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vocab-dqv/",
            "$namespace": str(HRI),
            "$IRI": "DQV.QualityCertificate",
            "$prefix": "hri",
        },
    )
    target: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The relationship between an Annotation and its Target.""",
        json_schema_extra={"rdf_term": OA.hasTarget, "rdf_type": "uri"},
    )

    body: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The object of the relationship is a resource that is a body of the Annotation.""",
        json_schema_extra={"rdf_term": OA.hasBody, "rdf_type": "uri"},
    )
