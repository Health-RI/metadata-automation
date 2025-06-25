from __future__ import annotations

import re
import sys
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, List, Literal, Optional, Union

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, RootModel, field_validator
from rdflib.namespace import DCAT, DCTERMS, PROV
from sempyro import LiteralField
from sempyro.dcat import DCATResource
from sempyro.namespaces import DCATv3, FREQ
from sempyro.prov import Activity


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class Status(Enum):
    """
    Status enumeration for ADMS
    """

    Completed = ADMSStatus.Completed
    Deprecated = ADMSStatus.Deprecated
    UnderDevelopment = ADMSStatus.UnderDevelopment
    Withdrawn = ADMSStatus.Withdrawn


class AccessRights(Enum):
    """
    Access rights enumeration
    """

    public = URIRef("http://publications.europa.eu/resource/authority/access-right/PUBLIC")
    restricted = URIRef("http://publications.europa.eu/resource/authority/access-right/RESTRICTED")
    non_public = URIRef("http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC")


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

    @field_validator("temporal_resolution", mode="after")
    @classmethod
    def validate_xsd_duration(cls, value: Union[str, LiteralField]) -> LiteralField:
        if isinstance(value, str):
            return LiteralField(value=value, datatype="xsd:duration")
        if isinstance(value, LiteralField) and value.datatype != "xsd:duration":
            return LiteralField(value=value.value, datatype="xsd:duration")
        return value
