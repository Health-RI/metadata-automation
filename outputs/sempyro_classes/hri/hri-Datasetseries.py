from pathlib import Path
from typing import List, Union

from pydantic import AnyHttpUrl, ConfigDict, Field
from rdflib import DCAT, DCTERMS
from sempyro.dcat import DCATDatasetSeries
from sempyro.foaf import Agent
from sempyro.namespaces import DCATAPv3, DCATv3
from sempyro.vcard import VCard


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIDatasetseries(DCATDatasetseries):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vocab-dcat-3/",
            "$namespace": str(HRI),
            "$IRI": "DCATv3.DatasetSeries",
            "$prefix": "hri",
        },
    )
    applicable_legislation: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""The legislation that is applicable to this resource.""",
        json_schema_extra={"rdf_term": DCATAPv3.applicableLegislation, "rdf_type": "uri"},
    )

    contact_point: list[Union[AnyHttpUrl, VCard]] = Field(
        description="""Relevant contact information for the cataloged resource.""",
        json_schema_extra={"rdf_term": DCAT.contactPoint, "rdf_type": "uri"},
    )

    description: list[Union[LiteralField, str]] = Field(
        description="""An account of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "rdfs_literal"},
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

    modification_date: Optional[Union[AwareDatetime, NaiveDatetime, date, str]] = Field(
        default=None,
        description="""Date on which the resource was changed.""",
        json_schema_extra={"rdf_term": DCTERMS.modified, "rdf_type": "datetime_literal"},
    )

    publisher: Optional[Union[Agent, AnyHttpUrl]] = Field(
        default=None,
        description="""An entity responsible for making the resource available.""",
        json_schema_extra={"rdf_term": DCTERMS.publisher, "rdf_type": "uri"},
    )

    release_date: Optional[Union[AwareDatetime, NaiveDatetime, date, str]] = Field(
        default=None,
        description="""Date of formal issuance of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.issued, "rdf_type": "datetime_literal"},
    )

    temporal_coverage: Optional[list[PeriodOfTime]] = Field(
        default=None,
        description="""Temporal characteristics of the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.temporal, "rdf_type": "DCTERMS.PeriodOfTime"},
    )

    title: list[Union[LiteralField, str]] = Field(
        description="""A name given to the resource.""",
        json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "rdfs_literal"},
    )
