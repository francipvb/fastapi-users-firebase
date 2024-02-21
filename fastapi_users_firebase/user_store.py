"""User store implementation.

This module contains the user database store.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, NewType, Optional, cast

import firebase_admin
from anyio import to_thread
from fastapi_users.db.base import BaseUserDatabase
from fastapi_users.models import UserProtocol
from firebase_admin import auth
from pydantic import BaseModel, EmailStr, HttpUrl, SecretStr, model_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from typing_extensions import Self

UID = NewType("UID", str)

IsSuperuser = Callable[[auth.UserRecord], bool]


class FirebaseUser(UserProtocol[UID]):
    """A firebase user instance."""

    def __init__(
        self,
        user: auth.UserRecord,
        app: Optional[firebase_admin.App] = None,
        is_superuser_func: Optional[IsSuperuser] = None,
    ) -> None:
        """Initialyze the user object.

        The user must be a firebase user record object to be successfully wrapped.

        Args:
            user: A firebase user object
            app: a firebase app, if any. Defaults to None.
            is_superuser_func: A function to determine whether the user is a superuser. Defaults to None.
        """
        super().__init__()
        self._user = user
        self._app = app
        self._is_superuser: IsSuperuser = is_superuser_func or (lambda _: False)  # pragma: nocover

    @property
    def id(self) -> UID:  # type: ignore[override]
        """Retrieve the user unique ID.

        Returns:
            The UID string
        """
        return UID(str(self._user.uid))

    @property
    def email(self) -> str:  # type: ignore[override]
        """Retrieve the user email.

        The email may be `None`. For this case, the email will be an empty string.

        Returns:
            The user email, or an empty string
        """
        return self._user.email or ""

    @property
    def hashed_password(self) -> str:  # type: ignore[override] # pragma: nocover
        """Retrieve an empty string.

        As we don't have the hability to pull the password hash, we have to retrieve an empty string.

        Returns:
            An empty string
        """
        return ""

    @property
    def is_active(self) -> bool:  # type: ignore[override] # pragma: nocover
        """Indicate whether the user is active.

        An user is active if it is not disabled in the firebase service.

        Returns:
            A boolean value to indicate whether the user is active or not
        """
        return not self._user.disabled

    @property
    def is_superuser(self) -> bool:  # type: ignore[override]
        """Return whether the user is a superuser.

        As of now, we don't have a way to detect whether the user is a superuser or not.

        A way may be through firebase custom claims, but for now, this just returns `False`.

        Returns:
            A boolean value to indicate whether the user is a superuser or not
        """
        return self._is_superuser(self._user)

    @property
    def is_verified(self) -> bool:  # type: ignore[override]
        """Retrieve whether the user is verified.

        An user is verified in these conditions:
            - The user email is verified.
            - The user has a phone number.

        The second cawse is because the phone number is verified at the link time.

        Returns:
            A boolean value indicating whether the user was verified or not
        """
        user = self._user
        return bool(user.email_verified) or bool(user.phone_number)

    @property
    def name(self) -> Optional[str]:  # pragma: nocover
        """Get the user display name.

        Returns:
            The user display name
        """
        return self._user.display_name

    @property
    def phone_number(self) -> Optional[str]:  # pragma: nocover
        """Retrieve the user phone number.

        Returns:
            The phone number string.
        """
        return self._user.phone_number


class FirebaseUserDatabase(BaseUserDatabase[FirebaseUser, UID]):
    """A database of firebase users."""

    def __init__(
        self, firebase_app: Optional[firebase_admin.App] = None, is_superuser_func: Optional[IsSuperuser] = None
    ) -> None:
        """Initialyze the firebase user store.

        Args:
            firebase_app (optional): The firebase app object. Defaults to None.
            is_superuser_func: A function to determine whether the user is a superuser. Defaults to None.
        """
        super().__init__()
        self._app = firebase_app
        self._is_superuser = is_superuser_func

    async def get(self, id: UID) -> Optional[FirebaseUser]:  # noqa: A002
        """Retrieve an user from firebase.

        Args:
            id: The ID of the user to retrieve

        Returns:
            The user object, or `None` if not found.
        """
        try:
            user = cast(
                auth.UserRecord,
                await to_thread.run_sync(auth.get_user, id, self._app),
            )
        except auth.UserNotFoundError:
            return None
        else:
            return self._map_user(user)

    def _map_user(self, user: auth.UserRecord):
        return FirebaseUser(user, self._app, self._is_superuser)

    async def get_by_email(self, email: str) -> Optional[FirebaseUser]:
        """Get an user by email.

        This method just calls the firebase authentication service to retrieve an user by it's email and wraps it in a specialyzed object.

        Args:
            email: the email to look up

        Returns:
            An user if the email was found, or `None`.
        """
        try:
            user = await to_thread.run_sync(
                auth.get_user_by_email,
                email,
                self._app,
            )
        except auth.UserNotFoundError:
            return None
        else:
            return self._map_user(user)

    async def delete(self, user: FirebaseUser) -> None:
        """Delete an user from the database.

        Args:
            user: the user to be deleted

        Raises:
            ValueError: Raised if the user ID is not valid
            FirebaseError: Raised by Firebase Auth if something occurs.
        """
        if not isinstance(user, FirebaseUser):
            error_msg = f"Object {user!r} is not a valid user object."
            raise TypeError(error_msg)
        if self._app != user._app:
            error_msg = "Provided object does not belong to the same app."
            raise AssertionError(error_msg)

        await to_thread.run_sync(auth.delete_user, user.id)

    async def create(self, create_dict: Dict[str, Any]) -> FirebaseUser:
        """Create a new user.

        Args:
            create_dict: a dict containing data for the new user

        Returns:
            A new `FirebaseUser` object
        """
        data = _CreateUpdateFirebaseUserModel.model_validate(create_dict)
        return self._map_user(await to_thread.run_sync(self._create, data))

    def _create(self, data: _CreateUpdateFirebaseUserModel) -> auth.UserRecord:
        return auth.create_user(app=self._app, **data.model_dump(mode="json", exclude_unset=True))


class _CreateUpdateFirebaseUserModel(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    email_verified: bool = False
    phone_number: Optional[PhoneNumber] = None
    photo_url: Optional[HttpUrl] = None
    password: Optional[SecretStr] = None
    disabled: bool = False

    @model_validator(mode="after")
    def _check_data(self) -> Self:
        if self.email is None and self.phone_number is None:  # pragma: nocover
            error_msg = "Either email or phone number must be set."
            raise ValueError(error_msg)
        return self
