from pathlib import Path
from typing import Union

from pydantic import AnyHttpUrl, ConfigDict, Field
from rdflib import Namespace
from sempyro import LiteralField, RDFModel


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIChecksum(RDFModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "http://spdx.org/rdf/terms/2.3",
            "$namespace": str(HRI),
            "$IRI": "SPDX.Checksum",
            "$prefix": "hri",
        },
    )
    algorithm: AnyHttpUrl = Field(
        description="""Identifies the algorithm used to produce the subject Checksum.""",
        json_schema_extra={"rdf_term": SPDX.algorithm, "rdf_type": "uri"},
    )

    checksum_value: Union[LiteralField, str] = Field(
        description="""The checksumValue property provides a lower case hexidecimal encoded digest value produced using a specific algorithm.""",
        json_schema_extra={
            "rdf_term": SPDX.checksumValue,
            "rdf_type": "xsd:Binary",
        },
    )
