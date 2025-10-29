import logging
from datetime import date, datetime
from typing import ClassVar, List, Optional, Set, Union

from pydantic import AnyHttpUrl, AwareDatetime, ConfigDict, Field, NaiveDatetime, field_validator
from rdflib.namespace import DCAT, DCTERMS, FOAF, ORDL2, PROV
from sempyro import LiteralField
from sempyro.adms import Identifier
from sempyro.dcat import AccessRights, Attribution, DCATDataset, DCATDatasetSeries, DCATDistribution, Relationship
from sempyro.dqv import QualityCertificate
from sempyro.geo import Location
from sempyro.hri import HRI
from sempyro.hri_dcat.hri_agent import HRIAgent
from sempyro.hri_dcat.hri_vcard import HRIVCard
from sempyro.hri_dcat.vocabularies import DatasetStatus, DatasetTheme
from sempyro.namespaces import ADMS, DCATAPv3, DCATv3, DPV, DQV, HEALTHDCATAP
from sempyro.odrl import ODRLPolicy
from sempyro.prov import Activity
from sempyro.time import PeriodOfTime
from sempyro.utils.validator_functions import convert_to_literal


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIDataset(DCATDataset):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vocab-dcat-3/",
            "$namespace": str(HRI),
            "$IRI": "DCAT.Dataset",
            "$prefix": "hri",
        },
    )
    access_rights: AccessRights = Field(
        description="""Information about who access the resource or an indication of its security status.""",
        json_schema_extra={"rdf_term": DCTERMS.accessRights, "rdf_type": "uri"},
    )

    analytics: Optional[list[Union[AnyHttpUrl, DCATDistribution]]] = Field(
        default=None,
        description="""An analytics distribution of the dataset.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.analytics, "rdf_type": "uri"},
    )

    applicable_legislation: list[AnyHttpUrl] = Field(
        description="""The legislation that is applicable to this resource.""",
        json_schema_extra={"rdf_term": DCATAPv3.applicableLegislation, "rdf_type": "uri"},
    )

    code_values: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""Health classifications and their codes associated with the dataset""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.hasCodeValues, "rdf_type": "uri"},
    )

    coding_system: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""Coding systems in use (ex: ICD-10-CM, DGRs, SNOMED=CT, ...)""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.hasCodingSystem, "rdf_type": "uri"},
    )

    conforms_to: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""An established standard to which the described resource conforms.""",
        json_schema_extra={"rdf_term": DCTERMS.conformsTo, "rdf_type": "uri"},
    )

    contact_point: Union[AnyHttpUrl, HRIVCard] = Field(
        description="""Relevant contact information for the cataloged resource.""",
        json_schema_extra={"rdf_term": DCAT.contactPoint, "rdf_type": "uri"},
    )

    creator: list[Union[AnyHttpUrl, HRIAgent]] = Field(
        description="""An entity responsible for making the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.creator, "rdf_type": "uri"},
    )

    description: list[Union[LiteralField, str]] = Field(
        description="""An account of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "rdfs_literal"},
    )

    distribution: Optional[list[Union[AnyHttpUrl, DCATDistribution]]] = Field(
        default=None,
        description="""An available Distribution for the Dataset.""",
        json_schema_extra={"rdf_term": DCAT.distribution, "rdf_type": "uri"},
    )

    documentation: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A page or document about this thing.""",
        json_schema_extra={"rdf_term": FOAF.page, "rdf_type": "uri"},
    )

    frequency: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The frequency with which items are added to a collection.""",
        json_schema_extra={"rdf_term": DCTERMS.accrualPeriodicity, "rdf_type": "uri"},
    )

    geographical_coverage: Optional[list[Union[AnyHttpUrl, Location]]] = Field(
        default=None,
        description="""Spatial characteristics of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.spatial, "rdf_type": "uri"},
    )

    has_version: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""This resource has a more specific, versioned resource.""",
        json_schema_extra={"rdf_term": DCTERMS.hasVersion, "rdf_type": "uri"},
    )

    health_theme: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A category of the Dataset or tag describing the Dataset.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.healthTheme, "rdf_type": "uri"},
    )

    identifier: Union[LiteralField, str] = Field(
        description="""An unambiguous reference to the resource within a given context.""",
        json_schema_extra={"rdf_term": DCTERMS.identifier, "rdf_type": "rdfs_literal"},
    )

    in_series: Optional[list[Union[AnyHttpUrl, DCATDatasetSeries]]] = Field(
        default=None,
        description="""A dataset series of which the dataset is part.""",
        json_schema_extra={"rdf_term": DCATv3.inSeries, "rdf_type": "uri"},
    )

    is_referenced_by: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A related resource that references, cites, or otherwise points to the described resource.""",
        json_schema_extra={"rdf_term": DCTERMS.isReferencedBy, "rdf_type": "uri"},
    )

    keyword: list[LiteralField] = Field(
        description="""A keyword or tag describing the resource.""",
        json_schema_extra={"rdf_term": DCAT.keyword, "rdf_type": "rdfs_literal"},
    )

    language: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A language of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.language, "rdf_type": "uri"},
    )

    legal_basis: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""Indicates use or applicability of a Legal Basis.""",
        json_schema_extra={"rdf_term": DPV.hasLegalBasis, "rdf_type": "uri"},
    )

    maximum_typical_age: Optional[Union[LiteralField, int]] = Field(
        default=None,
        description="""Maximum typical age of the population within the dataset""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.maxTypicalAge, "rdf_type": "xsd:nonNegativeInteger"},
    )

    minimum_typical_age: Optional[Union[LiteralField, int]] = Field(
        default=None,
        description="""Minimum typical age of the population within the dataset""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.minTypicalAge, "rdf_type": "xsd:nonNegativeInteger"},
    )

    modification_date: Optional[Union[AwareDatetime, NaiveDatetime, date, str]] = Field(
        default=None,
        description="""Date on which the resource was changed.""",
        json_schema_extra={"rdf_term": DCTERMS.modified, "rdf_type": "datetime_literal"},
    )

    number_of_records: Optional[Union[LiteralField, int]] = Field(
        default=None,
        description="""Size of the dataset in terms of the number of records""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.numberOfRecords, "rdf_type": "xsd:nonNegativeInteger"},
    )

    number_of_unique_infividuals: Optional[Union[LiteralField, int]] = Field(
        default=None,
        description="""Number of records for unique individuals.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.numberOfUniqueIndividuals, "rdf_type": "xsd:nonNegativeInteger"},
    )

    other_identifier: Optional[list[Identifier]] = Field(
        default=None,
        description="""Links a resource to an adms:Identifier class.""",
        json_schema_extra={"rdf_term": ADMS.identifier, "rdf_type": "uri"},
    )

    personal_data: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""Indicates association with Personal Data.""",
        json_schema_extra={"rdf_term": DPV.hasPersonalData, "rdf_type": "uri"},
    )

    population_coverage: Optional[list[Union[LiteralField, str]]] = Field(
        default=None,
        description="""A definition of the population within the dataset""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.populationCoverage, "rdf_type": "rdfs_literal"},
    )

    publisher: Union[AnyHttpUrl, HRIAgent] = Field(
        description="""An entity responsible for making the resource available.""",
        json_schema_extra={"rdf_term": DCTERMS.publisher, "rdf_type": "uri"},
    )

    purpose: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""Indicates association with Purpose.""",
        json_schema_extra={"rdf_term": DPV.hasPurpose, "rdf_type": "uri"},
    )

    qualified_attribution: Optional[list[Union[AnyHttpUrl, Attribution]]] = Field(
        default=None,
        description="""Attribution is the ascribing of an entity to an agent.""",
        json_schema_extra={"rdf_term": PROV.qualifiedAttribution, "rdf_type": "uri"},
    )

    qualified_relation: Optional[list[Union[AnyHttpUrl, Relationship]]] = Field(
        default=None,
        description="""Link to a description of a relationship with another resource.""",
        json_schema_extra={"rdf_term": DCAT.qualifiedRelation, "rdf_type": "uri"},
    )

    quality_annotation: Optional[list[Union[AnyHttpUrl, QualityCertificate]]] = Field(
        default=None,
        description="""Refers to a quality annotation.""",
        json_schema_extra={"rdf_term": DQV.hasQualityAnnotation, "rdf_type": "uri"},
    )

    release_date: Optional[Union[AwareDatetime, NaiveDatetime, date, datetime, str]] = Field(
        default=None,
        description="""Date of formal issuance of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.issued, "rdf_type": "datetime_literal"},
    )

    retention_period: Optional[PeriodOfTime] = Field(
        default=None,
        description="""A temporal period which the dataset is available for secondary use.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.retentionPeriod, "rdf_type": "DCTERMS.PeriodOfTime"},
    )

    sample: Optional[list[Union[AnyHttpUrl, DCATDistribution]]] = Field(
        default=None,
        description="""Links to a sample of an Asset (which is itself an Asset).""",
        json_schema_extra={"rdf_term": ADMS.sample, "rdf_type": "uri"},
    )

    source: Optional[list[Union[AnyHttpUrl, DCATDataset]]] = Field(
        default=None,
        description="""A related resource from which the described resource is derived.""",
        json_schema_extra={"rdf_term": DCTERMS.source, "rdf_type": "uri"},
    )

    status: Optional[DatasetStatus] = Field(
        default=None,
        description="""The status of the Asset in the context of a particular workflow process.""",
        json_schema_extra={"rdf_term": ADMS.status, "rdf_type": "uri"},
    )

    temporal_coverage: Optional[list[PeriodOfTime]] = Field(
        default=None,
        description="""Temporal characteristics of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.temporal, "rdf_type": "DCTERMS.PeriodOfTime"},
    )

    temporal_resolution: Optional[Union[LiteralField, str]] = Field(
        default=None,
        description="""Minimum time period resolvable in the dataset.""",
        json_schema_extra={"rdf_term": DCAT.temporalResolution, "rdf_type": "xsd:duration"},
    )

    theme: list[DatasetTheme] = Field(
        description="""A main category of the resource. A resource can have multiple themes.""",
        json_schema_extra={"rdf_term": DCAT.theme, "rdf_type": "uri"},
    )

    title: list[Union[LiteralField, str]] = Field(
        description="""A name given to the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"},
    )

    type: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""The nature or genre of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.type, "rdf_type": "uri"},
    )

    version: Optional[Union[LiteralField, str]] = Field(
        default=None,
        description="""The version indicator (name or identifier) of a resource.""",
        json_schema_extra={"rdf_term": DCATv3.version, "rdf_type": "rdfs_literal"},
    )

    version_notes: Optional[list[Union[LiteralField, str]]] = Field(
        default=None,
        description="""A description of changes between this version and the previous version of the Asset.""",
        json_schema_extra={"rdf_term": ADMS.versionNotes, "rdf_type": "rdfs_literal"},
    )

    was_generated_by: Optional[list[Union[Activity, AnyHttpUrl]]] = Field(
        default=None,
        description="""Generation is the completion of production of a new entity by an activity. This entity did not exist before generation and becomes available for usage after this generation.""",
        json_schema_extra={"rdf_term": PROV.wasGeneratedBy, "rdf_type": "uri"},
    )

    _validate_literal_fields: ClassVar[Set[str]] = {
        "title",
        "description",
        "keyword",
        "version",
        "version_notes",
        "population_coverage",
    }

    @field_validator("temporal_resolution", mode="after")
    @classmethod
    def validate_xsd_duration(cls, value: Union[str, LiteralField]) -> LiteralField:
        if isinstance(value, str):
            return LiteralField(value=value, datatype="xsd:duration")
        if isinstance(value, LiteralField) and value.datatype != "xsd:duration":
            return LiteralField(value=value.value, datatype="xsd:duration")
        return value

    @field_validator(*_validate_literal_fields, mode="before")
    @classmethod
    def validate_literal(cls, value: List[Union[str, LiteralField]]) -> List[LiteralField]:
        return convert_to_literal(value)
