"""The user object wrapper."""

from typing import Callable, NewType, Optional

import firebase_admin
from fastapi_users.models import UserProtocol
from firebase_admin import auth

IsSuperuser = Callable[[auth.UserRecord], bool]
UID = NewType("UID", str)


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
