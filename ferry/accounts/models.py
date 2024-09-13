from __future__ import annotations

import secrets
import uuid
from collections.abc import Collection

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Func, Value
from django.db.models.functions import Coalesce

from ferry.core.discord import NoSuchGuildMemberError, get_discord_client
from ferry.court.models import SCORE_FIELD, Ratification


class User(AbstractUser):
    person = models.OneToOneField("Person", blank=True, null=True, on_delete=models.PROTECT)

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


class PersonQuerySet(models.QuerySet["Person"]):
    def for_user(self, user: User) -> PersonQuerySet:
        # All users can read all people
        return self

    def with_num_ratified_accusations(self) -> PersonQuerySet:
        ratifications = (
            Ratification.objects.filter(accusation__suspect_id=models.OuterRef("id"))
            .order_by()
            .annotate(count=Func(F("id"), function="Count"))
            .values("count")
        )
        return self.annotate(
            num_ratified_accusations=models.Subquery(ratifications, output_field=models.PositiveIntegerField())
        )

    def with_current_score(self) -> PersonQuerySet:
        ratifications = (
            Ratification.objects.filter(accusation__suspect_id=models.OuterRef("id"))
            .order_by()
            .with_score_value()
            .annotate(count=Func(F("score_value"), function="Sum"))
            .values("count")
        )
        return self.annotate(
            current_score=Coalesce(
                models.Subquery(ratifications, output_field=SCORE_FIELD),
                Value(0, output_field=SCORE_FIELD),
            )
        )


PersonManager = models.Manager.from_queryset(PersonQuerySet)


class Person(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=255, unique=True)
    discord_id = models.BigIntegerField(verbose_name="Discord ID", blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = PersonManager()

    class Meta:
        verbose_name_plural = "people"
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name

    def clean_fields(self, exclude: Collection[str] | None = None) -> None:
        super().clean_fields(exclude)

        if self.discord_id:
            discord_client = get_discord_client()
            try:
                discord_client.get_guild_member_by_id(settings.DISCORD_GUILD, self.discord_id)
            except NoSuchGuildMemberError:
                raise ValidationError("Unknown discord ID. Is the user part of the guild?") from None
