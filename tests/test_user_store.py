from typing import Any, cast
from unittest.mock import Mock, create_autospec, sentinel

import firebase_admin
import pytest
from faker import Faker
from firebase_admin import auth
from phone_gen import PhoneNumber

from fastapi_users_firebase import FirebaseUserDatabase
from fastapi_users_firebase.schemas import CreateFirebaseUserModel, UpdateFirebaseUserModel
from fastapi_users_firebase.user import UID, FirebaseUser


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


@pytest.fixture
def user_spec() -> Mock:
    """Build a compatible user record object.

    The user record is a firebase construct that owns all user-related information.

    Returns:
        A mocked user record object
    """
    return create_autospec(auth.UserRecord)


@pytest.fixture()
def is_superuser_mock() -> Mock:
    """Build a mock for `is_superuser` property.

    The `FirebaseUser.is_superuser` property is backed by a callable. The callable accepts an user record object to check whether the user is a superuser or not.

    Returns:
        A callable mock object.
    """
    return Mock()


@pytest.fixture()
def user(faker: Faker, user_spec: Mock, phone_gen: PhoneNumber) -> FirebaseUser:
    """Build an object instance.

    An user instance has an user record coming from firebase authentication.

    Args:
        faker: The faker instance to be used.
        user_spec: A mock user record object.v
        phone_gen: A phone number generator.

    Returns:
        The user object
    """
    return FirebaseUser(
        email=faker.email(),
        hashed_password="",
        id=UID(faker.pystr()),
        is_active=faker.boolean(),
        is_superuser=faker.boolean(),
        is_verified=faker.boolean(),
        name=faker.name(),
        phone_number=phone_gen.get_number(),
        record=user_spec,
    )


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

    @pytest.fixture()
    def create_model(self, faker: Faker, phone_gen: PhoneNumber) -> CreateFirebaseUserModel:
        return CreateFirebaseUserModel(
            is_active=faker.boolean(),
            email=faker.email(),
            display_name=faker.name(),
            is_verified=faker.boolean(),
            photo_url=faker.image_url(),
            phone_number=cast(
                Any,
                phone_gen.get_number(),
            ),
            password=faker.pystr(),
        )

    @pytest.fixture()
    def update_model(self, faker: Faker, phone_gen: PhoneNumber) -> UpdateFirebaseUserModel:
        return UpdateFirebaseUserModel(
            is_active=faker.boolean(),
            email=faker.email(),
            display_name=faker.name(),
            is_verified=faker.boolean(),
            photo_url=faker.image_url(),
            phone_number=cast(
                Any,
                phone_gen.get_number(),
            ),
            password=faker.pystr(),
        )

    @pytest.fixture()
    def create_mock(self, monkeypatch: pytest.MonkeyPatch) -> Mock:
        mock = Mock()
        monkeypatch.setattr(auth, auth.create_user.__name__, mock)
        return mock

    @pytest.fixture()
    def update_mock(self, monkeypatch: pytest.MonkeyPatch) -> Mock:
        mock = Mock()
        monkeypatch.setattr(auth, auth.update_user.__name__, mock)
        return mock

    @pytest.mark.anyio()
    async def test_get(self, faker: Faker, get_user_mock: Mock, database: FirebaseUserDatabase) -> None:
        user_id = faker.pystr()
        get_user_mock.return_value = sentinel
        result = await database.get(user_id)
        assert result is not None
        assert result.record is sentinel
        get_user_mock.assert_called_with(user_id, database._app)

    @pytest.mark.anyio()
    async def test_get_user_by_email(
        self, get_user_by_email_mock: Mock, database: FirebaseUserDatabase, faker: Faker
    ) -> None:
        email = faker.email()
        get_user_by_email_mock.return_value = sentinel
        result = await database.get_by_email(email)
        assert result is not None
        assert result.record is sentinel
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
    async def test_delete(
        self,
        database: FirebaseUserDatabase,
        delete_user_mock: Mock,
        firebase_app: firebase_admin.App,
        user: FirebaseUser,
    ) -> None:
        await database.delete(user)
        delete_user_mock.assert_called_once_with(user.id)

    @pytest.mark.anyio()
    async def test_create(
        self,
        create_mock: Mock,
        create_model: CreateFirebaseUserModel,
        database: FirebaseUserDatabase,
        firebase_app: firebase_admin.App,
    ) -> None:
        create_mock.return_value = create_autospec(auth.UserRecord)
        create_dict = create_model.model_dump(exclude_unset=True, mode="json")
        result = await database.create(create_dict)
        assert result.record == create_mock.return_value
        create_mock.assert_called()

    @pytest.mark.anyio()
    async def test_update(
        self,
        database: FirebaseUserDatabase,
        user: FirebaseUser,
        user_spec: Mock,
        update_model: UpdateFirebaseUserModel,
        firebase_app: firebase_admin.App,
        update_mock: Mock,
    ):
        update_mock.return_value = create_autospec(auth.UserRecord)
        update_dict = update_model.model_dump(exclude_unset=True, mode="json")
        result = await database.update(user, update_dict)
        assert result.record == update_mock.return_value
        update_mock.assert_called()
