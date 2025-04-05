import factory

from ferry.accounts.factories import PersonFactory

from .models import Accusation, Consequence, Ratification


class ConsequenceFactory(factory.django.DjangoModelFactory[Consequence]):
    content = factory.Faker("sentence")
    created_by = factory.SubFactory(PersonFactory)

    class Meta:
        model = Consequence


class RatificationFactory(factory.django.DjangoModelFactory[Ratification]):
    consequence = factory.SubFactory(ConsequenceFactory)
    created_by = factory.SubFactory(PersonFactory)

    class Meta:
        model = Ratification


class AccusationFactory(factory.django.DjangoModelFactory[Accusation]):
    quote = factory.Faker("sentence")
    suspect = factory.SubFactory(PersonFactory)
    created_by = factory.SubFactory(PersonFactory)
    ratification = factory.RelatedFactory(RatificationFactory, factory_related_name="accusation")

    class Meta:
        model = Accusation
