import pytest
from django.db import IntegrityError

from ferry.pub.models import Pub


def make_pub(name: str, *, is_default: bool = False) -> Pub:
    return Pub.objects.create(name=name, emoji="🍺", map_url="https://example.com/map", is_default=is_default)


@pytest.mark.django_db
class TestPubIsDefault:
    def test_saving_new_default_demotes_previous_default(self) -> None:
        first = make_pub("First", is_default=True)
        second = make_pub("Second", is_default=True)

        first.refresh_from_db()
        assert not first.is_default
        assert second.is_default

    def test_saving_non_default_leaves_default_alone(self) -> None:
        default = make_pub("Default", is_default=True)
        make_pub("Other")

        default.refresh_from_db()
        assert default.is_default

    def test_database_rejects_two_defaults(self) -> None:
        make_pub("First", is_default=True)
        other = make_pub("Second")

        with pytest.raises(IntegrityError):
            Pub.objects.filter(pk=other.pk).update(is_default=True)
