import secrets
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    person = models.OneToOneField("court.Person", blank=True, null=True, on_delete=models.PROTECT)

    @property
    def display_name(self) -> str:
        if self.person:
            return self.person.display_name
        else:
            return self.get_full_name()


class APIToken(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_tokens")
    token = models.CharField(max_length=128, unique=True, editable=False, default=secrets.token_urlsafe)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self) -> str:
        return f"API Token for {self.user}"
