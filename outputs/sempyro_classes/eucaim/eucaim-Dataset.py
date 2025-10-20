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


class EUCAIMDataset(DCATDataset):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_schema_extra={"$ontology": "nan", "$namespace": str(EUCAIM), "$IRI": "nan", "$prefix": "eucaim"},
    )
    title: list[Union[LiteralField, str]] = Field(
        description="""A clear and concise name for the dataset.""",
        json_schema_extra={"rdf_term": DCTERMS.title, "rdf_type": "nan"},
    )
    description: list[AnyHttpUrl] = Field(
        description="""A detailed description of the dataset's content, purpose, and scope.""",
        json_schema_extra={"rdf_term": DCTERMS.description, "rdf_type": "nan"},
    )
    provenance: list[AnyHttpUrl] = Field(
        description="""A statement about the lineage of a Dataset.""",
        json_schema_extra={"rdf_term": DCTERMS.provenance, "rdf_type": "nan"},
    )
    intendedPurpose: list[AnyHttpUrl] = Field(
        description="""The primary objective for which the dataset was created.""",
        json_schema_extra={"rdf_term": DPV.hasPurpose, "rdf_type": "nan"},
    )
    imageCreationYear: list[AnyHttpUrl] = Field(
        description="""A temporal period that the dataset covers. This corresponds to the year range that the actual (DICOM) images were created/acquired.""",
        json_schema_extra={"rdf_term": DCTERMS.temporal, "rdf_type": "nan"},
    )
    geographicalCoverage: list[AnyHttpUrl] = Field(
        description="""A geographic region that is covered by the Dataset.""",
        json_schema_extra={"rdf_term": DCTERMS.spatial, "rdf_type": "nan"},
    )
    contact_Point: list[AnyHttpUrl] = Field(
        description="""Contact information of the individual/managing organization of the Dataset for sending comments about the Dataset.""",
        json_schema_extra={"rdf_term": DCAT.contactPoint, "rdf_type": "nan"},
    )
    publisher: list[AnyHttpUrl] = Field(
        description="""An entity (organisation) responsible for making the Dataset available. (Name and URL (landing page) of the organisation should be given)""",
        json_schema_extra={"rdf_term": DCTERMS.publisher, "rdf_type": "nan"},
    )
    publisherType: list[AnyHttpUrl] = Field(
        description="""A type of organisation that makes the Dataset available.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.publishertype, "rdf_type": "nan"},
    )
    applicableLegislation: list[AnyHttpUrl] = Field(
        description="""The legislation that mandates the creation or management of the Dataset.""",
        json_schema_extra={"rdf_term": DCATAP.applicableLegislation, "rdf_type": "nan"},
    )
    theme: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""A category of the dataset.""",
        json_schema_extra={"rdf_term": DCAT.theme, "rdf_type": "nan"},
    )
    type: list[AnyHttpUrl] = Field(
        description="""A type of the Dataset.""", json_schema_extra={"rdf_term": DCTERMS.type, "rdf_type": "nan"}
    )
    age_low: Optional[int] = Field(
        default=None,
        description="""The minimum age of subjects within the dataset.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.minTypicalAge, "rdf_type": "nan"},
    )
    age_high: Optional[int] = Field(
        default=None,
        description="""The maximum age of subjects within the dataset.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.maxTypicalAge, "rdf_type": "nan"},
    )
    birthsex: list[AnyHttpUrl] = Field(
        description="""BirthSex of subjects in the dataset.""",
        json_schema_extra={"rdf_term": EUCAIM.hasBirthSex, "rdf_type": "nan"},
    )
    number_of_studies: Optional[int] = Field(
        default=None,
        description="""Total count of DICOM studies.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.numberOfRecords, "rdf_type": "nan"},
    )
    number_of_subjects: Optional[int] = Field(
        default=None,
        description="""Total count of unique individuals in the dataset.""",
        json_schema_extra={"rdf_term": HEALTHDCATAP.numberOfUniqueIndividuals, "rdf_type": "nan"},
    )
    collection_method: list[AnyHttpUrl] = Field(
        description="""This attribute defines the scope of data aggregation within the dataset. It specifies how data records are organized based on different criteria, allowing users to understand the context in which the data was collected.""",
        json_schema_extra={"rdf_term": EUCAIM.collectionMethod, "rdf_type": "nan"},
    )
    quality_label: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""A statement related to quality of the Dataset, including rating, quality certificate as per the EHDS requirements.""",
        json_schema_extra={"rdf_term": DQV.hasQualityAnnotation, "rdf_type": "nan"},
    )
    legal_basis: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""Legal basis used to justify processing of data or use of technology in accordance with a law.""",
        json_schema_extra={"rdf_term": DPV.hasLegalBasis, "rdf_type": "nan"},
    )
    condition: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The primary cancer condition of individuals in the dataset.""",
        json_schema_extra={"rdf_term": EUCAIM.hasCondition, "rdf_type": "nan"},
    )
    image_modality: list[AnyHttpUrl] = Field(
        description="""The set of modalities for the images in the dataset.""",
        json_schema_extra={"rdf_term": EUCAIM.hasImageModality, "rdf_type": "nan"},
    )
    image_equipmentManufacturer: list[AnyHttpUrl] = Field(
        description="""Manufacturer of the imaging device as it is defined in DICOM tag (0008,0070).""",
        json_schema_extra={"rdf_term": EUCAIM.hasEquipmentManufacturer, "rdf_type": "nan"},
    )
    image_body_part: list[AnyHttpUrl] = Field(
        description="""Anatomical areas captured in the images.""",
        json_schema_extra={"rdf_term": EUCAIM.hasImageBodyPart, "rdf_type": "nan"},
    )
    accessURL: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""A URL that gives information about accessing the dataset.""",
        json_schema_extra={"rdf_term": DCAT.accessURL, "rdf_type": "nan"},
    )
    accessRights: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The accessRights of the dataset.""",
        json_schema_extra={"rdf_term": DCTERMS.accessRights, "rdf_type": "nan"},
    )
    accessConditions: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""A statement about the conditions of access and usage of the dataset.""",
        json_schema_extra={"rdf_term": DCTERMS.rights, "rdf_type": "nan"},
    )
    imageSize: Optional[float] = Field(
        default=None,
        description="""The total size of all Distributions in the dataset, which is mainly the image size.""",
        json_schema_extra={"rdf_term": DCAT.byteSize, "rdf_type": "nan"},
    )
    format: list[AnyHttpUrl] = Field(
        description="""The file format of the Distributions included in the Dataset.""",
        json_schema_extra={"rdf_term": DCTERMS.format, "rdf_type": "nan"},
    )
    sample: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""A sample distribution of the dataset.""",
        json_schema_extra={"rdf_term": ADMS.sample, "rdf_type": "nan"},
    )
    identifier: Optional[str] = Field(
        default=None,
        description="""A unique identifier for the dataset, i.e. the URI in the context of the EUCAIM Public Catalogue. ((in compliance with the findability aspect of the FAIR principles))""",
        json_schema_extra={"rdf_term": DCTERMS.identifier, "rdf_type": "nan"},
    )
    version: Optional[str] = Field(
        default=None,
        description="""The version of the dataset.""",
        json_schema_extra={"rdf_term": DCAT.version, "rdf_type": "nan"},
    )
    interoperabilityTier: Optional[AnyHttpUrl] = Field(
        default=None,
        description="""The EUCAIM data federation and interoperability tier the specific dataset belongs to.""",
        json_schema_extra={"rdf_term": ADMS.interoperabilityLevel, "rdf_type": "nan"},
    )
