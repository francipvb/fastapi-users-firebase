from fastapi_users_firebase.foo import foo


def test_foo():
    assert foo() == "foo"
