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


class DCATVCard(RDFModel):
    """
    A vCard-style representation of an agent (person or organization)
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vcard-rdf/",
            "$namespace": str(vcard),
            "$IRI": VCARD.Kind,
            "$prefix": "vcard",
        },
    )
    formatted_name: Optional[str] = Field(
        default=None,
        description="""The full name of the object (as a single string). This is the only mandatory property.""",
        json_schema_extra={"rdf_term": VCARD.fn, "rdf_type": "rdfs_literal"},
    )
    hasEmail: Optional[str] = Field(
        default=None,
        description="""The email address as a mailto URI""",
        json_schema_extra={"rdf_term": VCARD.hasEmail, "rdf_type": "uri"},
    )
    hasUID: Optional[str] = Field(
        default=None,
        description="""A unique identifier for the object""",
        json_schema_extra={"rdf_term": VCARD.hasUID, "rdf_type": "uri"},
    )
