"""An specialyzed manager object."""

from http import HTTPStatus
from typing import Any, Optional

import firebase_admin
from fastapi import HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import exceptions
from fastapi_users.manager import BaseUserManager
from fastapi_users.schemas import BaseUserCreate, BaseUserUpdate

from fastapi_users_firebase.user import UID, FirebaseUser
from fastapi_users_firebase.user_database import FirebaseUserDatabase


class FirebaseUserManager(BaseUserManager[FirebaseUser, UID]):  # pragma: nocover
    """A specialyzed user manager for firebase authentication store."""

    def __init__(
        self,
        user_db: Optional[FirebaseUserDatabase],
        app: Optional[firebase_admin.App] = None,
    ):
        """Initialyze a firebase user manager.

        This is a specialyzed user manger for firebase authentication. It does some operations different than default implementation.

        Args:
            user_db: The user database object
            app: A Firebase app. Defaults to None.
        """
        user_db = user_db or FirebaseUserDatabase(app or firebase_admin.get_app())
        super().__init__(user_db)
        self._app = user_db._app

    def parse_id(self, value: Any) -> UID:
        """Parse the ID value.

        This just returns an string wrapped for typing purposes.

        Args:
            value: the value to be parsed

        Returns:
            The parsed user ID
        """
        return UID(str(value))

    async def create(
        self, user_create: BaseUserCreate, safe: bool = False, request: Optional[Request] = None
    ) -> FirebaseUser:
        """Create a new user.

        Thisa method just delegates the creation to the database and raises an exception if the user already exists.

        Args:
            user_create: The data of the new user
            safe: Whether the user data should be parsed without modifications. Defaults to False.
            request: The HTTP request. Defaults to None.

        Raises:
            exceptions.UserAlreadyExists: If another user with the same email already exists.

        Returns:
            A new user object.
        """
        # Copied from base implementation with some minor changes:
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()

        user_dict = user_create.create_update_dict() if safe else user_create.create_update_dict_superuser()

        created_user = await self.user_db.create(user_dict)

        await self.on_after_register(created_user, request)

        return created_user

    async def update(
        self, user_update: BaseUserUpdate, user: FirebaseUser, safe: bool = False, request: Optional[Request] = None
    ) -> FirebaseUser:
        """Update the provided user.

        Args:
            user_update: The user data
            user: The user being updated
            safe: Whether to do a safe update or a full one
            request: The current HTTP request

        Returns:
            The new, updated user.
        """
        # Copied from default implementation and added some tweaks:
        updated_user_data = user_update.create_update_dict() if safe else user_update.create_update_dict_superuser()
        updated_user = await self.user_db.update(user, updated_user_data)
        await self.on_after_update(updated_user, updated_user_data, request)
        return updated_user

    async def request_verify(self, user: FirebaseUser, request: Optional[Request] = None) -> None:  # noqa: D102
        self._raise_firebase_client_required()

    async def verify(self, token: str, request: Optional[Request] = None) -> FirebaseUser:  # noqa: D102
        self._raise_firebase_client_required()
        return await super().verify(token, request)

    async def forgot_password(self, user: FirebaseUser, request: Optional[Request] = None) -> None:  # noqa: D102
        self._raise_firebase_client_required()
        return await super().forgot_password(user, request)

    async def reset_password(self, token: str, password: str, request: Optional[Request] = None) -> FirebaseUser:  # noqa: D102
        self._raise_firebase_client_required()
        return await super().reset_password(token, password, request)

    def _raise_firebase_client_required(self) -> None:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="This operation is not allowed, please use a Firebase Client SDK.",
        )

    async def authenticate(self, credentials: OAuth2PasswordRequestForm) -> Optional[FirebaseUser]:  # noqa: D102
        self._raise_firebase_client_required()
        return await super().authenticate(credentials)
