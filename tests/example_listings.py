import pytest


@pytest.fixture()
def brief_example_data():
    return {
        "essentialRequirements": [True, False, True, False]
    }
