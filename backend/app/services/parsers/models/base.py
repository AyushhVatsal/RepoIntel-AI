from pydantic import BaseModel, ConfigDict


class ParserBaseModel(BaseModel):
    """
    Base model for all parser domain models.

    Provides shared configuration and behavior for parser-related
    intermediate representation (IR) objects.
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )