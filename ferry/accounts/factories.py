import factory

from .models import Person


class PersonFactory(factory.django.DjangoModelFactory[Person]):
    # Display names are unique, so random names would occasionally collide in tests that create many people.
    display_name = factory.Sequence(lambda n: f"Person {n}")

    class Meta:
        model = Person
