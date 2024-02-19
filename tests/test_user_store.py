from unittest.mock import Mock, sentinel

import pytest
from faker import Faker
from firebase_admin import auth

from fastapi_users_firebase import FirebaseUserDatabase


@pytest.fixture()
def database():
    """Builds a firebase user database.

    This is a fixture function to build a test object.

    Returns:
        An user database that interacts with Firebase.
    """
    return FirebaseUserDatabase()


class TestFirebaseUserDatabase:
    @pytest.fixture()
    def get_user_mock(self, monkeypatch: pytest.MonkeyPatch):
        mock_obj = Mock()
        monkeypatch.setattr(auth, auth.get_user.__name__, mock_obj)
        return mock_obj

    @pytest.fixture()
    def get_user_by_email_mock(self, monkeypatch: pytest.MonkeyPatch):
        mock_obj = Mock()
        monkeypatch.setattr(auth, auth.get_user_by_email.__name__, mock_obj)
        return mock_obj

    @pytest.mark.anyio()
    async def test_get(self, faker: Faker, get_user_mock: Mock, database: FirebaseUserDatabase) -> None:
        user_id = faker.pystr()
        get_user_mock.return_value = sentinel
        result = await database.get(user_id)
        assert result is not None
        assert result._user is sentinel
        get_user_mock.assert_called_with(user_id, database._app)

    @pytest.mark.anyio()
    async def test_get_user_by_email(
        self, get_user_by_email_mock: Mock, database: FirebaseUserDatabase, faker: Faker
    ) -> None:
        email = faker.email()
        get_user_by_email_mock.return_value = sentinel
        result = await database.get_by_email(email)
        assert result is not None
        assert result._user is sentinel
        get_user_by_email_mock.assert_called_with(email, database._app)

    @pytest.mark.anyio()
    async def test_get_not_found(self, faker: Faker, get_user_mock: Mock, database: FirebaseUserDatabase) -> None:
        user_id = faker.pystr()
        get_user_mock.side_effect = auth.UserNotFoundError("User not found.")
        result = await database.get(user_id)
        assert result is None
        get_user_mock.assert_called_with(user_id, database._app)

    @pytest.mark.anyio()
    async def test_get_user_by_email_not_found(
        self, get_user_by_email_mock: Mock, database: FirebaseUserDatabase, faker: Faker
    ) -> None:
        email = faker.email()
        get_user_by_email_mock.side_effect = auth.UserNotFoundError("User not found")
        result = await database.get_by_email(email)
        assert result is None
        get_user_by_email_mock.assert_called_with(email, database._app)
