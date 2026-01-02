import logging
import typing
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Union

from pydantic import (
    AnyHttpUrl,
    AwareDatetime,
    ConfigDict,
    Field,
    NaiveDatetime,
    field_validator,
    model_validator,
)
from rdflib import DCAT, DCTERMS, TIME, URIRef
from sempyro import LiteralField, RDFModel
from sempyro.namespaces import Greg
from sempyro.utils.constants import year_month_pattern, year_pattern
from sempyro.utils.validator_functions import force_literal_field


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIPeriodoftime(RDFModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={
            "$ontology": "https://www.w3.org/TR/vocab-dcat-3/#Class:Period_of_Time",
            "$namespace": str(HRI),
            "$IRI": "DCTERMS.PeriodOfTime",
            "$prefix": "hri",
        },
    )
    end_date: Optional[LiteralField] = Field(
        default=None,
        description="""The end of the period.""",
        json_schema_extra={
            "rdf_term": DCAT.startDate,
            "rdf_type": "rdfs_literal",
        },
    )

    start_date: Optional[LiteralField] = Field(
        default=None,
        description="""The start of the period.""",
        json_schema_extra={
            "rdf_term": DCAT.endDate,
            "rdf_type": "rdfs_literal",
        },
    )
