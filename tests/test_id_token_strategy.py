from http import HTTPStatus
from unittest.mock import Mock, create_autospec

import firebase_admin
import pytest
from fastapi import HTTPException
from firebase_admin import auth

from fastapi_users_firebase.id_token import FirebaseIdTokenStrategy
from fastapi_users_firebase.manager import FirebaseUserManager
from fastapi_users_firebase.user import FirebaseUser


@pytest.fixture()
def firebase_app() -> firebase_admin.App:
    """Build and return a mocked firebase app object.

    Returns:
        A firebase app object mock.
    """
    return create_autospec(firebase_admin.App)


@pytest.fixture()
def strategy(firebase_app) -> FirebaseIdTokenStrategy:
    """Build a strategy object for testing purposes.

    A strategy is a way to retrieve and encode tokens from an user instance. For firebase instances, there is no way to sign in to the server, so the write process is never used.

    Args:
        firebase_app: A firebase app object

    Returns:
        The stretegy object being tested.
    """
    return FirebaseIdTokenStrategy(firebase_app)


@pytest.fixture()
def manager() -> Mock:
    """Build and retrieve a mock object to be used as an user manager.

    This is just a mock to be used as a parameter in some calls.

    Returns:
        A mock object to be used as a manager.
    """
    return create_autospec(FirebaseUserManager)


@pytest.fixture()
def verify_mock(monkeypatch: pytest.MonkeyPatch):
    """The mock being called when calling `firebase_admin.auth.verify_id_token`.

    This mock is set as an attribute in the firebase_admin.auth` module by monkeypatching it.

    Args:
        monkeypatch: The pytest monkeypatch object instance.

    Returns:
        A mock object.
    """
    mock = Mock()
    monkeypatch.setattr(auth, auth.verify_id_token.__name__, mock)
    return mock


class TestRead:
    @pytest.mark.anyio()
    async def test_read(self, strategy: FirebaseIdTokenStrategy, manager: Mock, verify_mock: Mock) -> None:
        data = {"uid": "testuid"}
        user = create_autospec(FirebaseUser)
        verify_mock.return_value = data
        manager.get.return_value = user
        result = await strategy.read_token("mytoken", manager)
        assert result is user
        verify_mock.assert_called_with("mytoken", strategy._app, True)
        manager.get.assert_called_with(manager.parse_id(data["uid"]))

    @pytest.mark.anyio()
    async def test_read_invalid(self, strategy: FirebaseIdTokenStrategy, manager: Mock, verify_mock: Mock) -> None:
        verify_mock.side_effect = auth.InvalidIdTokenError("Token is invalid")
        result = await strategy.read_token("mytoken", manager)
        verify_mock.assert_called_with("mytoken", strategy._app, True)
        assert result is None

    @pytest.mark.anyio()
    @pytest.mark.parametrize(
        argnames="exc",
        argvalues=(
            auth.ExpiredIdTokenError("Id token expired.", "Token expired"),
            auth.RevokedIdTokenError("Id token revoked."),
        ),
    )
    async def test_read_expired_or_revoked(
        self, strategy: FirebaseIdTokenStrategy, manager: Mock, verify_mock: Mock, exc: BaseException
    ) -> None:
        verify_mock.side_effect = exc
        with pytest.raises(HTTPException) as raised_exc:
            await strategy.read_token("mytoken", manager)
        verify_mock.assert_called_with("mytoken", strategy._app, True)
        assert raised_exc.value.__cause__ is exc
        assert raised_exc.value.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.anyio()
    async def test_read_none(self, strategy: FirebaseIdTokenStrategy, manager: Mock, verify_mock: Mock) -> None:
        result = await strategy.read_token(None, manager)
        assert result is None
        verify_mock.assert_not_called()
