import factory

from .models import Person


class PersonFactory(factory.django.DjangoModelFactory):
    display_name = factory.Faker("name")

    class Meta:
        model = Person
