from pathlib import Path
from typing import Union

from pydantic import ConfigDict, Field
from rdflib.namespace import SKOS
from sempyro import LiteralField, RDFModel
from sempyro.namespaces import ADMS


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIIdentifier(RDFModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "http://www.w3.org/TR/vocab-adms/",
            "$namespace": str(HRI),
            "$IRI": "ADMS.Identifier",
            "$prefix": "hri",
        },
    )
    notation: Optional[Union[LiteralField, str]] = Field(
        default=None,
        description="""A string that is an identifier in the context of the identifier scheme referenced by its datatype. """,
        json_schema_extra={"rdf_term": SKOS.notation, "rdf_type": "rdfs_literal"},
    )

    schema_agency: Optional[Union[LiteralField, str]] = Field(
        default=None,
        description="""The name of the agency that issued the identifier.""",
        json_schema_extra={"rdf_term": ADMS.schemaAgency, "rdf_type": "rdfs_literal"},
    )
