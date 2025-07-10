from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, ConfigDict, Field, field_validator
from rdflib.namespace import DCAT, DCTERMS, PROV
from sempyro import LiteralField
from sempyro.dcat import DCATResource
from sempyro.namespaces import DCATv3, FREQ
from sempyro.prov import Activity


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class FOAFAgent(RDFModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "http://xmlns.com/foaf/spec/",
            "$namespace": str(FOAF),
            "$IRI": FOAF.Agent,
            "$prefix": "foaf",
        },
    )
    country: Optional[AnyHttpUrl] = Field(
        default=None, json_schema_extra={"rdf_term": DCTERMS.spatial, "rdf_type": "uri"}
    )
    email: AnyHttpUrl = Field(default=..., json_schema_extra={"rdf_term": FOAF.mbox, "rdf_type": "uri"})
    foaf_identifier: str = Field(
        default=..., json_schema_extra={"rdf_term": DCTERMS.identifier, "rdf_type": "rdfs_literal"}
    )
    name: str = Field(default=..., json_schema_extra={"rdf_term": FOAF.name, "rdf_type": "rdfs_literal"})
    publisher_note: Optional[str] = Field(
        default=None, json_schema_extra={"rdf_term": HEALTHDCATAP.publisherNote, "rdf_type": "rdfs_literal"}
    )
    publisher_type: Optional[AnyHttpUrl] = Field(
        default=None, json_schema_extra={"rdf_term": HEALTHDCATAP.publisherType, "rdf_type": "uri"}
    )
    foaf_type: Optional[AnyHttpUrl] = Field(
        default=None, json_schema_extra={"rdf_term": DCTERMS.type, "rdf_type": "uri"}
    )
    url: AnyHttpUrl = Field(default=..., json_schema_extra={"rdf_term": FOAF.homepage, "rdf_type": "uri"})
