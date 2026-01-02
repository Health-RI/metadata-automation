from typing import List, Optional, Union

import Logging
from pydantic import AnyHttpUrl, AnyUrl, ConfigDict, Field, field_validator
from sempyro import LiteralField
from sempyro.hri import HRI
from sempyro.utils.validator_functions import validate_convert_email
from sempyro.vcard import Kind, VCARD


metamodel_version = "None"
version = "None"

logger = logging.getLogger(__name__)


class HRIKind(Kind):
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
    contact_page: Optional[list[AnyHttpUrl]] = Field(
        default=None,
        description="""To specify a uniform resource locator associated with the object.""",
        json_schema_extra={"rdf_term": VCARD.hasURL, "rdf_type": "uri"},
    )

    has_email: AnyUrl = Field(
        description="""To specify the electronic mail address for communication with the object.""",
        json_schema_extra={"rdf_term": VCARD.hasEmail, "rdf_type": "uri"},
    )

    formatted_name: Union[LiteralField, str] = Field(
        description="""The formatted text corresponding to the name of the object.""",
        json_schema_extra={"rdf_term": VCARD.fn, "rdf_type": "rdfs_literal"},
    )

    @field_validator("hasEmail", mode="before")
    @classmethod
    def _validate_email(
        cls, value: Union[str, AnyUrl, List[Union[str, AnyUrl]]]
    ) -> List[AnyUrl]:
        """
        Checks if provided value is a valid email or mailto URI, fulfills an email to mailto URI
        """
        return validate_convert_email(value)
