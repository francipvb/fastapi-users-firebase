"""The user object wrapper."""

from dataclasses import dataclass
from typing import Callable, NewType, Optional

from fastapi_users.models import UserProtocol
from firebase_admin import auth
from typing_extensions import Self

IsSuperuser = Callable[[auth.UserRecord], bool]
UID = NewType("UID", str)


@dataclass(frozen=True)
class FirebaseUser(UserProtocol[UID]):
    """A firebase user instance."""

    id: UID
    email: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    phone_number: Optional[str]
    name: Optional[str]
    hashed_password: str
    record: auth.UserRecord

    @classmethod
    def from_record(
        cls,
        user: auth.UserRecord,
        is_superuser_func: Optional[IsSuperuser] = None,
    ) -> Self:
        """Initialyze the user object.

        The user must be a firebase user record object to be successfully wrapped.

        Args:
            user: A firebase user object
            app: a firebase app, if any. Defaults to None.
            is_superuser_func: A function to determine whether the user is a superuser. Defaults to None.
        """
        return cls(
            email=str(user.email or ""),
            id=UID(str(user.uid)),
            is_active=not user.disabled,
            is_verified=user.email_verified or bool(user.phone_number),
            phone_number=user.phone_number,
            name=user.display_name,
            is_superuser=is_superuser_func(user) if is_superuser_func is not None else False,
            hashed_password="",
            record=user,
        )
