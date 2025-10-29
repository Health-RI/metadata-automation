from typing import List, Optional, Union

from pydantic import AnyHttpUrl, AnyUrl, ConfigDict, Field, field_validator
from rdflib import URIRef
from rdflib.namespace import DCTERMS, FOAF
from sempyro import LiteralField
from sempyro.foaf import Agent
from sempyro.geo import Location
from sempyro.namespaces import HEALTHDCATAP
from sempyro.utils.validator_functions import validate_convert_email


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIAgent(Agent):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "http://xmlns.com/foaf/spec/",
            "$namespace": str(HRI),
            "$IRI": "FOAF.Agent",
            "$prefix": "hri",
        },
    )
    country: Optional[list[Union[AnyHttpUrl, Location]]] = Field(
        default=None,
        description="""Spatial characteristics of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.spatial, "rdf_type": "uri"},
    )

    email: AnyUrl = Field(
        description="""A email address via which contact can be made. This property SHOULD be used to provide the email address of the Agent, specified using fully qualified mailto: URI scheme [RFC6068]. The email SHOULD be used to establish a communication channel to the agent.""",
        json_schema_extra={"rdf_term": FOAF.mbox, "rdf_type": "uri"},
    )

    identifier: list[Union[LiteralField, str]] = Field(
        description="""An unambiguous reference to the resource within a given context.""",
        json_schema_extra={"rdf_term": DCTERMS.identifier, "rdf_type": "rdfs_literal"},
    )

    name: list[Union[LiteralField, str]] = Field(
        description="""A name for some thing.""", json_schema_extra={"rdf_term": FOAF.name, "rdf_type": "rdfs_literal"}
    )

    publisher_note: Optional[Union[LiteralField, str]] = Field(
        default=None,
        description="""A description of the publisher activities.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.publisherNote, "rdf_type": "rdfs_literal"},
    )

    publisher_type: Optional[Union[AnyUrl, URIRef]] = Field(
        default=None,
        description="""A type of organisation that makes the Dataset available.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.publisherType, "rdf_type": "uri"},
    )

    type: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The nature or genre of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.type, "rdf_type": "uri"},
    )

    URL: AnyUrl = Field(
        description="""A homepage for some thing.""", json_schema_extra={"rdf_term": FOAF.homepage, "rdf_type": "uri"}
    )

    @field_validator("mbox", mode="before")
    @classmethod
    def _validate_email(cls, value: Union[str, AnyUrl, List[Union[str, AnyUrl]]]) -> List[AnyUrl]:
        """
        Checks if provided value is a valid email or mailto URI, fulfills an email to mailto URI
        """
        return validate_convert_email(value)
