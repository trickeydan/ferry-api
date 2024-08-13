from rest_framework import serializers

from ferry.accounts.models import User
from ferry.court.api.serializers import PersonLinkSerializer


class UserSerializer(serializers.ModelSerializer[User]):
    person = PersonLinkSerializer()

    class Meta:
        model = User
        fields = ("username", "person")
