from rest_framework import serializers

from ferry.court.models import Person


class PersonSerializer(serializers.ModelSerializer[Person]):
    class Meta:
        model = Person
        fields = ("id", "display_name")
