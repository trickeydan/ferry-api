import factory

from .models import Consequence, Person


class PersonFactory(factory.django.DjangoModelFactory):
    display_name = factory.Faker("name")

    class Meta:
        model = Person


class ConsequenceFactory(factory.django.DjangoModelFactory):
    content = factory.Faker("sentence")
    created_by = factory.SubFactory(PersonFactory)

    class Meta:
        model = Consequence
