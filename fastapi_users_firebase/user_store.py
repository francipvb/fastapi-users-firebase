"""User store implementation.

This module contains the user database store.
"""

from typing import NewType, cast

import firebase_admin  # type: ignore[import-untyped]
from anyio import to_thread
from fastapi_users.db.base import BaseUserDatabase
from fastapi_users.models import UserProtocol
from firebase_admin import auth  # type: ignore[import-untyped]

UID = NewType("UID", str)


class FirebaseUser(UserProtocol[UID]):
    """A firebase user instance."""

    def __init__(self, user: auth.UserRecord, app: firebase_admin.App | None = None) -> None:
        """Initialyze the user object.

        The user must be a firebase user record object to be successfully wrapped.

        Args:
            user: A firebase user object
            app: a firebase app, if any. Defaults to None.
        """
        super().__init__()
        self._user = user
        self._app = app

    @property
    def id(self) -> UID:  # type: ignore[override]
        """Retrieve the user unique ID.

        Returns:
            The UID string
        """
        return UID(str(self._user.uid))  # type: ignore[]

    @property
    def email(self) -> str:  # type: ignore[override]
        """Retrieve the user email.

        The email may be `None`. For this case, the email will be an empty string.

        Returns:
            The user email, or an empty string
        """
        return self._user.email or ""  # type: ignore[]

    @property
    def hashed_password(self) -> str:  # type: ignore[override]
        """Retrieve an empty string.

        As we don't have the hability to pull the password hash, we have to retrieve an empty string.

        Returns:
            An empty string
        """
        return ""

    @property
    def is_active(self) -> bool:  # type: ignore[override]
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
        return False

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
        return bool(user.email_verified) or bool(user.phone_number)  # type: ignore[]

    @property
    def name(self) -> str | None:
        """Get the user display name.

        Returns:
            The user display name
        """
        return self._user.display_name  # type: ignore[]

    @property
    def phone_number(self) -> str | None:
        """Retrieve the user phone number.

        Returns:
            The phone number string.
        """
        return self._user.phone_number  # type: ignore[]


class FirebaseUserDatabase(BaseUserDatabase[FirebaseUser, UID]):
    """A database of firebase users."""

    def __init__(self, firebase_app: firebase_admin.App | None = None) -> None:
        """Initialyze the firebase user store.

        Args:
            firebase_app (optional): The firebase app object. Defaults to None.

        """
        super().__init__()
        self._app = firebase_app

    async def get(self, id: UID) -> FirebaseUser | None:  # noqa: A002
        """Retrieve an user from firebase.

        Args:
            id: The ID of the user to retrieve

        Returns:
            The user object, or `None` if not found.
        """
        try:
            user = cast(
                auth.UserRecord,
                await to_thread.run_sync(auth.get_user, id, self._app),  # type: ignore[]
            )
        except auth.UserNotFoundError:
            return None
        else:
            return FirebaseUser(user, self._app)

    async def get_by_email(self, email: str) -> FirebaseUser | None:
        """Get an user by email.

        This method just calls the firebase authentication service to retrieve an user by it's email and wraps it in a specialyzed object.

        Args:
            email: the email to look up

        Returns:
            An user if the email was found, or `None`.
        """
        try:
            user: auth.UserRecord = await to_thread.run_sync(  # type: ignore[]
                auth.get_user_by_email,  # type: ignore[]
                email,
                self._app,
            )
        except auth.UserNotFoundError:
            return None
        else:
            return FirebaseUser(user, self._app)  # type: ignore[]

    async def delete(self, user: FirebaseUser) -> None:
        """Delete an user from the database.

        Args:
            user: the user to be deleted

        Raises:
            ValueError: Raised if the user ID is not valid
            FirebaseError: Raised by Firebase Auth if something occurs.
        """
        await to_thread.run_sync(auth.delete_user, user.id)  # type: ignore[]
