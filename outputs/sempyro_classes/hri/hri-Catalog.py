import logging
from datetime import date
from typing import ClassVar, List, Optional, Set, Union

from pydantic import (
    AnyHttpUrl,
    AwareDatetime,
    ConfigDict,
    Field,
    NaiveDatetime,
    field_validator,
)
from rdflib.namespace import DCAT, DCTERMS, FOAF
from sempyro import LiteralField
from sempyro.dcat import DCATCatalog, DCATDataset
from sempyro.geo import Location
from sempyro.hri import HRI
from sempyro.hri_dcat.hri_agent import HRIAgent
from sempyro.hri_dcat.hri_data_service import HRIDataService
from sempyro.hri_dcat.hri_vcard import HRIVCard
from sempyro.namespaces import DCATAPv3
from sempyro.time import PeriodOfTime
from sempyro.utils.validator_functions import convert_to_literal, date_handler


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRICatalog(DCATCatalog):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vocab-dcat-3/",
            "$namespace": str(HRI),
            "$IRI": "DCAT.Catalog",
            "$prefix": "hri",
        },
    )
    applicable_legislation: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""The legislation that is applicable to this resource.""",
        json_schema_extra={
            "rdf_term": DCATAPv3.applicableLegislation,
            "rdf_type": "uri",
        },
    )

    catalog: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A catalog that is listed in the catalog.""",
        json_schema_extra={"rdf_term": DCAT.catalog, "rdf_type": "uri"},
    )

    contact_point: Union[AnyHttpUrl, HRIVCard] = Field(
        description="""Relevant contact information for the cataloged resource.""",
        json_schema_extra={"rdf_term": DCAT.contactPoint, "rdf_type": "uri"},
    )

    creator: Optional[list[Union[AnyHttpUrl, HRIAgent]]] = Field(
        default=None,
        description="""An entity responsible for making the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.creator, "rdf_type": "uri"},
    )

    dataset: Optional[list[Union[AnyHttpUrl, DCATDataset]]] = Field(
        default=None,
        description="""A dataset that is listed in the catalog.""",
        json_schema_extra={"rdf_term": DCAT.dataset, "rdf_type": "uri"},
    )

    description: list[Union[LiteralField, str]] = Field(
        description="""An account of the resource.""",
        json_schema_extra={
            "rdf_term": DCTERMS.description,
            "rdf_type": "rdfs_literal",
        },
    )

    geographical_coverage: Optional[list[Union[AnyHttpUrl, Location]]] = Field(
        default=None,
        description="""Spatial characteristics of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.spatial, "rdf_type": "uri"},
    )

    has_part: Optional[list[Union[AnyHttpUrl, DCATCatalog]]] = Field(
        default=None,
        description="""A related resource that is included either physically or logically in the described resource.""",
        json_schema_extra={"rdf_term": DCTERMS.hasPart, "rdf_type": "uri"},
    )

    home_page: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""A homepage for some thing.""",
        json_schema_extra={"rdf_term": FOAF.homepage, "rdf_type": "uri"},
    )

    language: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A language of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.language, "rdf_type": "uri"},
    )

    licence: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""A legal document giving official permission to do something with the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.license, "rdf_type": "uri"},
    )

    modification_date: Optional[
        Union[AwareDatetime, NaiveDatetime, date, str]
    ] = Field(
        default=None,
        description="""Date on which the resource was changed.""",
        json_schema_extra={
            "rdf_term": DCTERMS.modified,
            "rdf_type": "datetime_literal",
        },
    )

    publisher: Union[AnyHttpUrl, HRIAgent] = Field(
        description="""An entity responsible for making the resource available.""",
        json_schema_extra={"rdf_term": DCTERMS.publisher, "rdf_type": "uri"},
    )

    release_date: Optional[Union[AwareDatetime, NaiveDatetime, date, str]] = (
        Field(
            default=None,
            description="""Date of formal issuance of the resource.""",
            json_schema_extra={
                "rdf_term": DCTERMS.issued,
                "rdf_type": "datetime_literal",
            },
        )
    )

    rights: Optional[Union[AnyHttpUrl, LiteralField]] = Field(
        default=None,
        description="""Information about rights held in and over the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.rights, "rdf_type": "uri"},
    )

    service: Optional[list[Union[AnyHttpUrl, HRIDataService]]] = Field(
        default=None,
        description="""A service that is listed in the catalog.""",
        json_schema_extra={"rdf_term": DCAT.service, "rdf_type": "uri"},
    )

    temporal_coverage: Optional[list[PeriodOfTime]] = Field(
        default=None,
        description="""Temporal characteristics of the resource.""",
        json_schema_extra={
            "rdf_term": DCTERMS.temporal,
            "rdf_type": "DCTERMS.PeriodOfTime",
        },
    )

    themes: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A main category of the resource. A resource can have multiple themes.""",
        json_schema_extra={"rdf_term": DCAT.themeTaxonomy, "rdf_type": "uri"},
    )

    title: list[AnyHttpUrl] = Field(
        description="""A name given to the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.type, "rdf_type": "uri"},
    )

    _validate_literal_fields: ClassVar[Set[str]] = {
        "title",
        "description",
        "keyword",
        "version",
        "version_notes",
    }

    @field_validator(*_validate_literal_fields, mode="before")
    @classmethod
    def validate_literal(
        cls, value: List[Union[str, LiteralField]]
    ) -> List[LiteralField]:
        return convert_to_literal(value)

    @field_validator("release_date", "modification_date", mode="before")
    @classmethod
    def date_validator(cls, value):
        return date_handler(value)

    @field_validator("temporal_resolution", mode="after")
    @classmethod
    def validate_xsd_duration(
        cls, value: Union[str, LiteralField]
    ) -> LiteralField:
        if isinstance(value, str):
            return LiteralField(value=value, datatype="xsd:duration")
        if (
            isinstance(value, LiteralField)
            and value.datatype != "xsd:duration"
        ):
            return LiteralField(value=value.value, datatype="xsd:duration")
        return value
