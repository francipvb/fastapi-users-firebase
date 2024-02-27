import pytest
from phone_gen import PhoneNumber


@pytest.fixture()
def phone_gen() -> PhoneNumber:
    """Build a phone number generator.

    Returns:
        A phone number generator object.
    """
    return PhoneNumber("us")
