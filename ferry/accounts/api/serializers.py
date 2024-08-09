from rest_framework import serializers

from ferry.accounts.models import User
from ferry.court.api.serializers import PersonSerializer


class UserSerializer(serializers.ModelSerializer[User]):
    person = PersonSerializer()

    class Meta:
        model = User
        fields = ("username", "person")
