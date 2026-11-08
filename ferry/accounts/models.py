from __future__ import annotations

import math
import secrets
import uuid
from collections.abc import Collection
from datetime import UTC, datetime

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Exists, F, Func, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from ferry.accounts.repository import ferrify
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
    name = models.CharField(max_length=100)
    token = models.CharField(max_length=128, unique=True, editable=False, default=secrets.token_urlsafe)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                violation_error_message="Please choose a unique name for the token.",
                name="unique_name_for_token_per_user",
            )
        ]

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

    def with_pub_streak(self, *, now: datetime | None = None) -> PersonQuerySet:
        """Annotate `pub_streak`: how many past pub events in a row each person is marked as attending.

        A streak is the number of past events since the most recent one the person wasn't attending.
        Events that haven't happened yet don't count.
        """
        from ferry.pub.models import PubEvent, PubEventRSVP  # noqa: PLC0415

        past_events = PubEvent.objects.filter(timestamp__lte=now or timezone.now())
        attended = PubEventRSVP.objects.filter(
            pub_event=OuterRef("pk"), person=OuterRef(OuterRef("pk")), is_attending=True
        )
        last_missed_event = (
            past_events.annotate(attended=Exists(attended))
            .filter(attended=False)
            .order_by("-timestamp")
            .values("timestamp")[:1]
        )
        events_since_last_miss = (
            past_events.filter(timestamp__gt=OuterRef("last_missed_at"))
            .order_by()
            .annotate(count=Func(F("id"), function="Count", output_field=IntegerField()))
            .values("count")
        )
        return self.annotate(
            last_missed_at=Coalesce(Subquery(last_missed_event), Value(datetime(1970, 1, 1, tzinfo=UTC))),
        ).annotate(pub_streak=Coalesce(Subquery(events_since_last_miss, output_field=IntegerField()), 0))


PersonManager = models.Manager.from_queryset(PersonQuerySet)


class Person(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=255, unique=True)
    discord_id = models.BigIntegerField(verbose_name="Discord ID", blank=True, null=True, unique=True)
    autopub = models.BooleanField(default=False, verbose_name="AutoPub enabled")
    pub_booking_priority = models.SmallIntegerField(
        default=0,
        verbose_name="Pub booking priority",
        help_text="Higher numbers are higher priority. This is used to determine who gets reminded to book a table.",
    )

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

        if self.discord_id and not settings.DEBUG:
            discord_client = get_discord_client()
            try:
                discord_client.get_guild_member_by_id(settings.DISCORD_GUILD, self.discord_id)
            except NoSuchGuildMemberError:
                raise ValidationError("Unknown discord ID. Is the user part of the guild?") from None

    @property
    def ferry_sequence(self) -> str:
        if not hasattr(self, "current_score"):
            raise ValueError("current_score is not annotated.")
        return ferrify(math.ceil(self.current_score), seed=self.id.int)
