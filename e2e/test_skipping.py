import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.django_db(transaction=True)

scenarios("features/skipping.feature")
