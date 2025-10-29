from datetime import date, datetime
from pathlib import Path
from typing import List, Union

from pydantic import AnyHttpUrl, AwareDatetime, ConfigDict, Field, NaiveDatetime
from rdflib.namespace import DCAT, DCTERMS, FOAF
from sempyro import LiteralField
from sempyro.dcat import DCATDistribution
from sempyro.hri_dcat import HRIDataService
from sempyro.hri_dcat.vocabularies import DistributionStatus, GeonovumLicences
from sempyro.namespaces import ADMS, DCATAPv3
from sempyro.time import PeriodOfTime


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIDistribution(DCATDistribution):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vocab-dcat-3/",
            "$namespace": str(HRI),
            "$IRI": "DCAT.Distribution",
            "$prefix": "hri",
        },
    )
    access_service: Optional[Union[AnyHttpUrl, HRIDataService]] = Field(
        default=None,
        description="""A data service that gives access to the distribution of the dataset.""",
        json_schema_extra={"rdf_term": DCAT.accessService, "rdf_type": "uri"},
    )

    access_url: AnyHttpUrl = Field(
        description="""A URL of the resource that gives access to a distribution of the dataset. E.g., landing page, feed, SPARQL endpoint.""",
        json_schema_extra={"rdf_term": DCAT.accessURL, "rdf_type": "uri"},
    )

    applicable_legislation: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""The legislation that is applicable to this resource.""",
        json_schema_extra={"rdf_term": DCATAPv3.applicableLegislation, "rdf_type": "uri"},
    )

    byte_size: Union[LiteralField, int] = Field(
        description="""The size of a distribution in bytes.""",
        json_schema_extra={"rdf_term": DCAT.byteSize, "rdf_type": "xsd:integer"},
    )

    checksum: Optional[Checksum] = Field(
        default=None,
        description="""The checksum property provides a mechanism that can be used to verify that the contents of a file or package have not changed.""",
        json_schema_extra={"rdf_term": SPDX.checksum, "rdf_type": "uri"},
    )

    compression_format: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The compression format of the distribution in which the data is contained in a compressed form, e.g., to reduce the size of the downloadable file.""",
        json_schema_extra={"rdf_term": DCAT.compressFormat, "rdf_type": "uri"},
    )

    description: Optional[list[LiteralField]] = Field(
        default=None,
        description="""An account of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "rdfs_literal"},
    )

    documentation: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A homepage for some thing.""",
        json_schema_extra={"rdf_term": FOAF.page, "rdf_type": "uri"},
    )

    download_URL: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The URL of the downloadable file in a given format. E.g., CSV file or RDF file. The format is indicated by the distribution's dcterms:format and/or dcat:mediaType.""",
        json_schema_extra={"rdf_term": DCAT.downloadURL, "rdf_type": "uri"},
    )

    format: AnyUrl = Field(
        description="""The file format, physical medium, or dimensions of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.format, "rdf_type": "uri"},
    )

    language: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A language of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.language, "rdf_type": "uri"},
    )

    license: Union[AnyHttpUrl, GeonovumLicenses] = Field(
        description="""A legal document giving official permission to do something with the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.license, "rdf_type": "uri"},
    )

    linked_schemas: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""An established standard to which the described resource conforms.""",
        json_schema_extra={"rdf_term": DCTERMS.conformsTo, "rdf_type": "uri"},
    )

    media_type: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The media type of the distribution as defined by IANA.""",
        json_schema_extra={"rdf_term": DCAT.mediaType, "rdf_type": "uri"},
    )

    modification_date: Optional[Union[AwareDatetime, NaiveDatetime, date, str]] = Field(
        default=None,
        description="""Date on which the resource was changed.""",
        json_schema_extra={"rdf_term": DCTERMS.modified, "rdf_type": "datetime_literal"},
    )

    packaging_format: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The package format of the distribution in which one or more data files are grouped together, e.g., to enable a set of related files to be downloaded together.""",
        json_schema_extra={"rdf_term": DCAT.packageFormat, "rdf_type": "uri"},
    )

    release_date: Optional[Union[AwareDatetime, NaiveDatetime, date, str]] = Field(
        default=None,
        description="""Date of formal issuance of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.issued, "rdf_type": "datetime_literal"},
    )

    retention_period: Optional[Union[AnyHttpUrl, PeriodOfTime]] = Field(
        default=None,
        description="""A temporal period which the dataset is available for secondary use.""",
        json_schema_extra={"rdf_term": DCTERMS.accrualPeriodicity, "rdf_type": "uri"},
    )

    rights: AnyHttpUrl = Field(
        description="""Information about rights held in and over the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.rights, "rdf_type": "uri"},
    )

    status: Optional[Union[AnyHttpUrl, DistributionStatus]] = Field(
        default=None,
        description="""The status of the Asset in the context of a particular workflow process.""",
        json_schema_extra={"rdf_term": ADMS.status, "rdf_type": "uri"},
    )

    temporal_resolution: Optional[Union[LiteralField, str]] = Field(
        default=None,
        description="""Minimum time period resolvable in the dataset.""",
        json_schema_extra={"rdf_term": DCAT.spatialResolutionInMeters, "rdf_type": "xsd:duration"},
    )

    title: Optional[list[LiteralField]] = Field(
        default=None,
        description="""A name given to the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"},
    )

    @field_validator("title", "description", mode="before")
    @classmethod
    def validate_literal(cls, value: List[Union[str, LiteralField]]) -> List[LiteralField]:
        return convert_to_literal(value)

    @field_validator("temporal_resolution", mode="after")
    @classmethod
    def validate_xsd_duration(cls, value: Union[str, LiteralField]) -> LiteralField:
        if isinstance(value, str):
            return LiteralField(value=value, datatype="xsd:duration")
        if isinstance(value, LiteralField) and value.datatype != "xsd:duration":
            return LiteralField(value=value.value, datatype="xsd:duration")
        return value

    @field_validator("release_date", "modification_date", mode="before")
    @classmethod
    def date_validator(cls, value):
        return date_handler(value)
