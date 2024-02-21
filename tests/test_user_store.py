from unittest.mock import Mock, create_autospec, sentinel

import firebase_admin
import pytest
from faker import Faker
from firebase_admin import auth

from fastapi_users_firebase import FirebaseUserDatabase
from fastapi_users_firebase.user_store import FirebaseUser


@pytest.fixture()
def firebase_app() -> firebase_admin.App:
    """Build a mocked firebase app object.

    Returns:
        A firebase app mock.
    """
    return create_autospec(firebase_admin.App)


@pytest.fixture()
def database(firebase_app: firebase_admin.App):
    """Builds a firebase user database.

    This is a fixture function to build a test object.

    Args:
        firebase_app: The app to assign to the database object

    Returns:
        An user database that interacts with Firebase.
    """
    return FirebaseUserDatabase(firebase_app)


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

    @pytest.fixture()
    def delete_user_mock(self, monkeypatch: pytest.MonkeyPatch) -> Mock:
        mock = Mock()
        monkeypatch.setattr(auth, auth.delete_user.__name__, mock)
        return mock

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

    @pytest.mark.anyio()
    async def test_delete_invalid(self, database: FirebaseUserDatabase, delete_user_mock: Mock) -> None:
        with pytest.raises(TypeError):
            await database.delete(sentinel)

        delete_user_mock.assert_not_called()

    @pytest.mark.anyio()
    async def test_delete_different_apps(self, database: FirebaseUserDatabase, delete_user_mock: Mock) -> None:
        user = FirebaseUser(create_autospec(auth.UserRecord), create_autospec(firebase_admin.App))
        with pytest.raises(AssertionError):
            await database.delete(user)

        delete_user_mock.assert_not_called()

    @pytest.mark.anyio()
    async def testdelete(
        self, database: FirebaseUserDatabase, delete_user_mock: Mock, firebase_app: firebase_admin.App
    ) -> None:
        record = create_autospec(auth.UserRecord)
        user = FirebaseUser(record, firebase_app)
        await database.delete(user)
        delete_user_mock.assert_called_once_with(user.id)


class TestFirebaseUser:
    @pytest.fixture
    def user_spec(self) -> Mock:
        return create_autospec(auth.UserRecord)

    @pytest.fixture()
    def is_superuser_mock(self) -> Mock:
        return Mock()

    @pytest.fixture()
    def user(self, user_spec: Mock, is_superuser_mock: Mock, firebase_app: firebase_admin.App) -> FirebaseUser:
        return FirebaseUser(user_spec, firebase_app, is_superuser_mock)

    def test_id(self, user: FirebaseUser, user_spec: Mock, faker: Faker) -> None:
        user_spec.uid = faker.pystr()
        assert user.id == user_spec.uid

    def test_email(self, user: FirebaseUser, user_spec: Mock):
        assert user.email is user_spec.email

    def test_is_verified_with_email(self, user: FirebaseUser, user_spec: Mock) -> None:
        user_spec.email_verified = True
        user_spec.phone_number = None
        assert user.is_verified

    def test_is_verified_with_phone(self, user: FirebaseUser, user_spec: Mock, faker: Faker) -> None:
        user_spec.phone_number = faker.phone_number()
        user_spec.email_verified = False
        assert user.is_verified

    def test_is_superuser(self, user: FirebaseUser, is_superuser_mock: Mock, user_spec: Mock) -> None:
        assert user.is_superuser is is_superuser_mock.return_value
        is_superuser_mock.assert_called_with(user_spec)
