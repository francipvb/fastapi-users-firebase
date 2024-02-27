"""The ID token processing strategy."""

from http import HTTPStatus
from typing import Any, Dict, Optional

import firebase_admin
from anyio import to_thread
from fastapi import HTTPException
from fastapi_users import BaseUserManager
from fastapi_users.authentication.strategy import Strategy
from firebase_admin import auth

from fastapi_users_firebase.user import UID, FirebaseUser


class FirebaseIdTokenStrategy(Strategy[FirebaseUser, UID]):
    """Firebase ID Token strategy.

    This strategy class is a strategy to verify Firebase Authentication client-side id tokens.
    """

    def __init__(
        self, app: Optional[firebase_admin.App] = None, developer_claims: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialyze a new token strategy object.

        Args:
            app: The firebase app to use.
            developer_claims: Custom claims to attach to the custom tokens
        """
        super().__init__()
        self._app = app
        self._developer_claims = developer_claims

    async def read_token(  # noqa: D102
        self, token: Optional[str], user_manager: BaseUserManager[FirebaseUser, UID]
    ) -> Optional[FirebaseUser]:
        if token is None:
            return None
        try:
            data = await to_thread.run_sync(auth.verify_id_token, token, self._app, True)
        except (auth.RevokedIdTokenError, auth.ExpiredIdTokenError) as exc:
            raise HTTPException(HTTPStatus.FORBIDDEN, str(exc)) from exc
        except auth.InvalidIdTokenError:
            return None

        return await user_manager.get(user_manager.parse_id(data["uid"]))

    async def write_token(self, user: FirebaseUser) -> str:  # noqa: D102 # pragma: nocover
        raise NotImplementedError()

    async def destroy_token(self, token: str, user: FirebaseUser) -> None:  # noqa: D102 # pragma: nocover
        raise NotImplementedError()
