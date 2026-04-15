from datetime import date
from pathlib import Path
from typing import ClassVar, List, Set, Union

from pydantic import AnyHttpUrl, ConfigDict, Field, field_validator
from rdflib.namespace import DCAT, DCTERMS
from sempyro import LiteralField
from sempyro.adms import Identifier
from sempyro.dcat import AccessRights, DCATDataService
from sempyro.hri_dcat.hri_agent import HRIAgent
from sempyro.hri_dcat.hri_dataset import HRIDataset
from sempyro.hri_dcat.hri_vcard import HRIVCard
from sempyro.hri_dcat.vocabularies import DatasetTheme, GeonovumLicences
from sempyro.namespaces import ADMS, DCATAPv3
from sempyro.utils.validator_functions import convert_to_literal


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIDataservice(DCATDataservice):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vocab-dcat-3/",
            "$namespace": str(HRI),
            "$IRI": "DCAT.DataService",
            "$prefix": "hri",
        },
    )
    dct_access_rights: AccessRights = Field(
        description="""Information about who access the resource or an indication of its security status.""",
        json_schema_extra={"rdf_term": DCTERMS.accessRights, "rdf_type": "uri"},
    )

    dcatap_applicable_legislation: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""The legislation that is applicable to this resource.""",
        json_schema_extra={"rdf_term": DCATAPv3.applicableLegislation, "rdf_type": "uri"},
    )

    dct_application_profile: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""An established standard to which the described resource conforms.""",
        json_schema_extra={"rdf_term": DCTERMS.conformsTo, "rdf_type": "uri"},
    )

    dcat_contact_point: Union[AnyHttpUrl, HRIVCard] = Field(
        description="""Relevant contact information for the cataloged resource.""",
        json_schema_extra={"rdf_term": DCAT.contactPoint, "rdf_type": "uri"},
    )

    dct_creator: Optional[list[Union[AnyHttpUrl, HRIAgent]]] = Field(
        default=None,
        description="""An entity responsible for making the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.creator, "rdf_type": "uri"},
    )

    dct_rights: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""Information about rights held in and over the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.rights, "rdf_type": "uri"},
    )

    dct_description: list[Union[LiteralField, str]] = Field(
        description="""An account of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "rdfs_literal"},
    )

    dcat_end_point_description: AnyHttpUrl = Field(
        description="""A description of the services available via the end-points, including their operations, parameters etc.""",
        json_schema_extra={"rdf_term": DCAT.endpointDescription, "rdf_type": "uri"},
    )

    dcat_end_point_url: Union[AnyHttpUrl, DCATResource] = Field(
        description="""The root location or primary endpoint of the service (a Web-resolvable IRI).""",
        json_schema_extra={"rdf_term": DCAT.endpointURL, "rdf_type": "uri"},
    )

    dct_format: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""The file format, physical medium, or dimensions of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.format, "rdf_type": "uri"},
    )

    dcatap_hvd_category: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A data category defined in the High Value Dataset Implementing Regulation.""",
        json_schema_extra={"rdf_term": DCATAPv3.hvdCategory, "rdf_type": "uri"},
    )

    dct_identifier: Union[LiteralField, str] = Field(
        description="""An unambiguous reference to the resource within a given context.""",
        json_schema_extra={"rdf_term": DCTERMS.identifier, "rdf_type": "rdfs_literal"},
    )

    dcat_keyword: Optional[list[LiteralField]] = Field(
        default=None,
        description="""A keyword or tag describing the resource.""",
        json_schema_extra={"rdf_term": DCAT.keyword, "rdf_type": "rdfs_literal"},
    )

    dcat_landing_page: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A Web page that can be navigated to in a Web browser to gain access to the catalog, a dataset, its distributions and/or additional information.""",
        json_schema_extra={"rdf_term": DCAT.landingPage, "rdf_type": "uri"},
    )

    dct_language: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A language of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.language, "rdf_type": "uri"},
    )

    dct_licence: Union[AnyHttpUrl, GeonovumLicenses] = Field(
        description="""A legal document giving official permission to do something with the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.license, "rdf_type": "uri"},
    )

    dct_modification_date: Optional[Union[AwareDatetime, NaiveDatetime, date, str]] = Field(
        default=None,
        description="""Date on which the resource was changed.""",
        json_schema_extra={"rdf_term": DCTERMS.modified, "rdf_type": "datetime_literal"},
    )

    adms_other_identifier: Optional[list[Union[AnyHttpUrl, Identifier]]] = Field(
        default=None,
        description="""Links a resource to an adms:Identifier class.""",
        json_schema_extra={"rdf_term": ADMS.identifier, "rdf_type": "uri"},
    )

    dct_publisher: Union[AnyHttpUrl, HRIAgent] = Field(
        description="""An entity responsible for making the resource available.""",
        json_schema_extra={"rdf_term": DCTERMS.publisher, "rdf_type": "uri"},
    )

    dcat_serves_dataset: Optional[list[Union[AnyHttpUrl, DCATDataset]]] = Field(
        default=None,
        description="""A collection of data that this data service can distribute.""",
        json_schema_extra={"rdf_term": DCAT.servesDataset, "rdf_type": "uri"},
    )

    dcat_theme: list[DatasetTheme] = Field(
        description="""A main category of the resource. A resource can have multiple themes.""",
        json_schema_extra={"rdf_term": DCAT.theme, "rdf_type": "uri"},
    )

    dct_title: list[Union[LiteralField, str]] = Field(
        description="""A name given to the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"},
    )
