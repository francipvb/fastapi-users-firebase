"""User store implementation.

This module contains the user database store.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union, cast

import firebase_admin
from anyio import to_thread
from fastapi_users.db.base import BaseUserDatabase
from firebase_admin import auth

from fastapi_users_firebase.schemas import (
    CreateFirebaseUserModel,
    UpdateFirebaseUserModel,
)
from fastapi_users_firebase.user import UID, FirebaseUser, IsSuperuser


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

    def _map_user(self, user: auth.UserRecord) -> FirebaseUser:
        return FirebaseUser.from_record(user, self._app, self._is_superuser)

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

        await to_thread.run_sync(auth.delete_user, user.id)

    async def create(self, create_dict: Dict[str, Any]) -> FirebaseUser:
        """Create a new user.

        Args:
            create_dict: a dict containing data for the new user

        Returns:
            A new `FirebaseUser` object
        """
        data = CreateFirebaseUserModel.model_validate(create_dict)
        return self._map_user(await to_thread.run_sync(self._create, data))

    def _create(self, data: CreateFirebaseUserModel) -> auth.UserRecord:
        return auth.create_user(app=self._app, **self._get_create_update_dict(data, exclude_none=True))

    async def update(self, user: FirebaseUser, update_dict: Dict[str, Any]) -> FirebaseUser:
        """Perform an user update.

        The user is updated by calling firebase services with a dict containing the new user data.

        Args:
            user: the user being updated
            update_dict: the dictionary with the user data

        Returns:
            The updated user object.
        """
        data = UpdateFirebaseUserModel.model_validate(update_dict)
        return self._map_user(await to_thread.run_sync(self._update, str(user.id), data))

    def _update(self, uid: str, data: UpdateFirebaseUserModel) -> auth.UserRecord:
        return auth.update_user(uid=uid, app=self._app, **self._get_create_update_dict(data))

    def _get_create_update_dict(
        self, data: Union[CreateFirebaseUserModel, UpdateFirebaseUserModel], *, exclude_none: bool = True
    ) -> Dict[str, Any]:
        return {
            key: value if value is not None and not exclude_none else value
            for key, value in {
                "email": data.email,
                "password": data.password,
                "email_verified": data.is_verified,
                "display_name": data.display_name,
                "disabled": not data.is_active,
                "phone_number": data.phone_number,
                "photo_url": data.photo_url,
                "custom_claims": data.custom_claims,
            }.items()
        }
