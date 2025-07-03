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


class Frequency(Enum):
    """
    Frequency enumeration
    """

    triennial = FREQ.triennial
    biennial = FREQ.biennial
    annual = FREQ.annual
    semiannual = FREQ.semiannual
    threeTimesAYear = FREQ.threeTimesAYear
    quarterly = FREQ.quarterly
    bimonthly = FREQ.bimonthly
    monthly = FREQ.monthly
    semimonthly = FREQ.semimonthly
    biweekly = FREQ.biweekly
    threeTimesAMonth = FREQ.threeTimesAMonth
    weekly = FREQ.weekly
    semiweekly = FREQ.semiweekly
    threeTimesAWeek = FREQ.threeTimesAWeek
    daily = FREQ.daily
    continuous = FREQ.continuous
    irregular = FREQ.irregular


class DCATDataset(DCATResource):
    """
    A collection of data, published or curated by a single source, and available for access or download in one or more representations.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vocab-dcat-3/",
            "$namespace": str(DCAT),
            "$IRI": DCAT.Dataset,
            "$prefix": "dcat",
        },
    )
    distribution: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""An available distribution of the dataset.""",
        json_schema_extra={"rdf_term": DCAT.distribution, "rdf_type": "uri"},
    )
    frequency: Optional[Union[AnyHttpUrl, Frequency]] = Field(
        default=None,
        description="""The frequency at which a dataset is published.""",
        json_schema_extra={"rdf_term": DCTERMS.accrualPeriodicity, "rdf_type": "uri"},
    )
    in_series: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A dataset series of which the dataset is part.""",
        json_schema_extra={"rdf_term": DCATv3.inSeries, "rdf_type": "uri"},
    )
    spatial_resolution: Optional[list[float]] = Field(
        default=None,
        description="""Minimum spatial separation resolvable in a dataset, measured in meters.""",
        json_schema_extra={"rdf_term": DCAT.spatialResolutionInMeters, "rdf_type": "xsd:decimal"},
    )
    temporal_resolution: Optional[Union[LiteralField, str]] = Field(
        default=None,
        description="""Minimum time period resolvable in the dataset.""",
        json_schema_extra={"rdf_term": DCAT.temporalResolution, "rdf_type": "xsd:duration"},
    )
    was_generated_by: Optional[list[Union[Activity, AnyHttpUrl]]] = Field(
        default=None,
        description="""An activity that generated, or provides the business context for, the creation of the dataset.""",
        json_schema_extra={"rdf_term": PROV.wasGeneratedBy, "rdf_type": "uri"},
    )
    access_rights_dataset: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""Information about who can access the dataset and under what conditions.""",
        json_schema_extra={"rdf_term": DCTERMS.accessRights, "rdf_type": "uri"},
    )
    access_rights: Optional[AccessRights] = Field(
        default=None,
        description="""Information about who can access the resource or an indication of its security status.""",
        json_schema_extra={"rdf_term": DCTERMS.accessRights, "rdf_type": "uri"},
    )
    conforms_to: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""An established standard to which the described resource conforms.""",
        json_schema_extra={"rdf_term": DCTERMS.conformsTo, "rdf_type": "uri"},
    )
    contact_point: Optional[list[DCATVCard]] = Field(
        default=None,
        description="""Relevant contact information for the cataloged resource. Use of vCard is recommended""",
        json_schema_extra={"rdf_term": DCAT.contactPoint, "rdf_type": "uri"},
    )
    creator: Optional[list[FOAFAgent]] = Field(
        default=None,
        description="""The entity responsible for producing the resource. Resources of type foaf:Agent are recommended as values for this property.""",
        json_schema_extra={"rdf_term": DCTERMS.creator, "rdf_type": "uri"},
    )
    description: list[Union[LiteralField, str]] = Field(
        default=...,
        description="""An account of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "rdfs_literal"},
    )
    has_part: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A related resource that is included either physically or logically in the described resource.""",
        json_schema_extra={"rdf_term": DCTERMS.hasPart, "rdf_type": "uri"},
    )
    has_policy: Optional[ODRLPolicy] = Field(
        default=None,
        description="""An ODRL conformant policy expressing the rights associated with the resource.""",
        json_schema_extra={"rdf_term": ODRL2.hasPolicy, "rdf_type": "uri"},
    )
    identifier: Optional[list[Union[LiteralField, str]]] = Field(
        default=None,
        description="""A unique identifier of the resource being described or cataloged.""",
        json_schema_extra={"rdf_term": DCTERMS.identifier, "rdf_type": "rdfs_literal"},
    )
    is_referenced_by: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A related resource, such as a publication, that references, cites, or otherwise points to the cataloged resource.""",
        json_schema_extra={"rdf_term": DCTERMS.isReferencedBy, "rdf_type": "uri"},
    )
    keyword: Optional[list[LiteralField]] = Field(
        default=None,
        description="""A keyword or tag describing the resource.""",
        json_schema_extra={"rdf_term": DCAT.keyword, "rdf_type": "rdfs_literal"},
    )
    landing_page: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A Web page that can be navigated to in a Web browser to gain access to the catalog, a dataset, its distributions and/or additional information.""",
        json_schema_extra={"rdf_term": DCAT.landingPage, "rdf_type": "uri"},
    )
    license: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""A legal document under which the resource is made available.""",
        json_schema_extra={"rdf_term": DCTERMS.license, "rdf_type": "uri"},
    )
    language: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A language of the resource. This refers to the natural language used for textual metadata (i.e., titles, descriptions, etc.) of a cataloged resource (i.e., dataset or service) or the textual values of a dataset distribution""",
        json_schema_extra={"rdf_term": DCTERMS.language, "rdf_type": "uri"},
    )
    relation: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A resource with an unspecified relationship to the cataloged resource.""",
        json_schema_extra={"rdf_term": DCTERMS.relation, "rdf_type": "uri"},
    )
    rights: Optional[Union[AnyHttpUrl, LiteralField]] = Field(
        default=None,
        description="""Information about rights held in and over the distribution. Recommended practice is to refer to a rights statement with a URI. If this is not possible or feasible, a literal value (name, label, or short text) may be provided.""",
        json_schema_extra={"rdf_term": DCTERMS.rights, "rdf_type": "uri"},
    )
    qualified_relation: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""Link to a description of a relationship with another resource""",
        json_schema_extra={"rdf_term": DCAT.qualifiedRelation, "rdf_type": "uri"},
    )
    publisher: Optional[list[Union[AnyHttpUrl, FOAFAgent]]] = Field(
        default=None,
        description="""The entity responsible for making the resource available.""",
        json_schema_extra={"rdf_term": DCTERMS.publisher, "rdf_type": "uri"},
    )
    release_date: Optional[Union[AwareDatetime, NaiveDatetime, date, datetime, str]] = Field(
        default=None,
        description="""Date of formal issuance (e.g., publication) of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.issued, "rdf_type": "datetime_literal"},
    )
    theme: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A main category of the resource. A resource can have multiple themes.""",
        json_schema_extra={"rdf_term": DCAT.theme, "rdf_type": "uri"},
    )
    title: list[Union[LiteralField, str]] = Field(
        default=...,
        description="""A name given to the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"},
    )
    type: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""The nature or genre of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.type, "rdf_type": "uri"},
    )
    modification_date: Optional[Union[AwareDatetime, NaiveDatetime, date, str]] = Field(
        default=None,
        description="""Most recent date on which the resource was changed, updated or modified.""",
        json_schema_extra={"rdf_term": DCTERMS.modified, "rdf_type": "datetime_literal"},
    )
    qualified_attribution: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""Link to an Agent having some form of responsibility for the resource""",
        json_schema_extra={"rdf_term": PROV.qualifiedAttribution, "rdf_type": "uri"},
    )
    has_current_version: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""This resource has a more specific, versioned resource with equivalent content [PAV].""",
        json_schema_extra={"rdf_term": DCATv3.hasCurrentVersion, "rdf_type": "uri"},
    )
    has_version: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""This resource has a more specific, versioned resource""",
        json_schema_extra={"rdf_term": DCTERMS.hasVersion, "rdf_type": "uri"},
    )
    previous_version: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The previous version of a resource in a lineage [PAV].""",
        json_schema_extra={"rdf_term": DCATv3.previousVersion, "rdf_type": "uri"},
    )
    replaces: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""A related resource that is supplanted, displaced, or superseded by the described resource""",
        json_schema_extra={"rdf_term": DCTERMS.replaces, "rdf_type": "uri"},
    )
    status: Optional[Status] = Field(
        default=None,
        description="""The status of the resource in the context of a particular workflow process [VOCAB-ADMS].""",
        json_schema_extra={"rdf_term": ADMS.status, "rdf_type": "uri"},
    )
    version: Optional[Union[LiteralField, str]] = Field(
        default=None,
        description="""The version indicator (name or identifier) of a resource.""",
        json_schema_extra={"rdf_term": DCATv3.version, "rdf_type": "rdfs_literal"},
    )
    version_notes: Optional[list[Union[LiteralField, str]]] = Field(
        default=None,
        description="""A description of changes between this version and the previous version of the resource [VOCAB-ADMS].""",
        json_schema_extra={"rdf_term": ADMS.versionNotes, "rdf_type": "rdfs_literal"},
    )
    first: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The first resource in an ordered collection or series of resources, to which the current resource belongs.""",
        json_schema_extra={"rdf_term": DCATv3.first, "rdf_type": "uri"},
    )
    last: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The last resource in an ordered collection or series of resources, to which the current resource belongs.""",
        json_schema_extra={"rdf_term": DCATv3.last, "rdf_type": "uri"},
    )
    previous: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""The previous resource (before the current one) in an ordered collection or series of resources.""",
        json_schema_extra={"rdf_term": DCATv3.prev, "rdf_type": "uri"},
    )
    temporal_coverage: Optional[list[PeriodOfTime]] = Field(
        default=None,
        description="""The temporal period that the dataset covers.""",
        json_schema_extra={"rdf_term": DCTERMS.temporal, "rdf_type": "DCTERMS.PeriodOfTime"},
    )
    geographical_coverage: Optional[list[Union[AnyHttpUrl, Location]]] = Field(
        default=None,
        description="""The geographical area covered by the dataset.""",
        json_schema_extra={"rdf_term": DCTERMS.spatial, "rdf_type": "uri"},
    )

    @field_validator("temporal_resolution", mode="after")
    @classmethod
    def validate_xsd_duration(cls, value: Union[str, LiteralField]) -> LiteralField:
        if isinstance(value, str):
            return LiteralField(value=value, datatype="xsd:duration")
        if isinstance(value, LiteralField) and value.datatype != "xsd:duration":
            return LiteralField(value=value.value, datatype="xsd:duration")
        return value
