"""Schemas module."""

from typing import Any, Dict, Optional, Union

from fastapi_users.schemas import BaseUserCreate, BaseUserUpdate, CreateUpdateDictModel
from pydantic import HttpUrl, Json, model_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from typing_extensions import Self


class CreateUpdateFirebaseUserModel(CreateUpdateDictModel):
    """A base class to create or update a firebase user."""

    phone_number: Optional[PhoneNumber] = None
    display_name: Optional[str] = None
    photo_url: Optional[HttpUrl]
    custom_claims: Optional[Dict[str, Any]] = None


class CreateFirebaseUserModel(BaseUserCreate, CreateUpdateFirebaseUserModel):
    """Schema to create an user."""

    @model_validator(mode="after")
    def _check_data(self) -> Self:
        if self.email is None and self.phone_number is None:  # pragma: nocover
            error_msg = "Either email or phone number must be set."
            raise ValueError(error_msg)
        return self


class UpdateFirebaseUserModel(BaseUserUpdate, CreateUpdateFirebaseUserModel):
    """A pydantic schema to update an existing user."""

    custom_claims: Union[Json, Dict[str, Any], None] = None
