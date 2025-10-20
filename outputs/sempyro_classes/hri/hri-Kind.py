import logging
from abc import ABCMeta
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import ClassVar, List, Optional, Set, Union

from pydantic import AnyHttpUrl, AwareDatetime, ConfigDict, Field, NaiveDatetime, field_validator
from rdflib import DCAT, DCTERMS, ODRL2, PROV, URIRef
from sempyro import LiteralField, RDFModel
from sempyro.foaf import Agent
from sempyro.geo import Location
from sempyro.namespaces import ADMS, ADMSStatus, DCATv3
from sempyro.odrl import ODRLPolicy
from sempyro.time import PeriodOfTime
from sempyro.utils.validator_functions import convert_to_literal, date_handler
from sempyro.vcard import VCard


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIKind(RDFModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vcard-rdf/",
            "$namespace": str(HRI),
            "$IRI": "VCARD.Kind",
            "$prefix": "hri",
        },
    )
    contact_page: Optional[list[AnyUrl]] = Field(
        default=None,
        description="""To specify a uniform resource locator associated with the object.""",
        json_schema_extra={"rdf_term": VCARD.hasURL, "rdf_type": "uri"},
    )
    has_email: str = Field(
        description="""To specify the electronic mail address for communication with the object.""",
        json_schema_extra={"rdf_term": VCARD.hasEmail, "rdf_type": "uri"},
    )
    formatted_name: AnyHttpUrl = Field(
        description="""The formatted text corresponding to the name of the object.""",
        json_schema_extra={"rdf_term": VCARD.fn, "rdf_type": "rdfs_literal"},
    )
