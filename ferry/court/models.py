from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, F, Value, When
from django.utils import timezone

if TYPE_CHECKING:
    from ferry.accounts.models import User

SCORE_FIELD: models.DecimalField = models.DecimalField(max_digits=3, decimal_places=2)


class ConsequenceQuerySet(models.QuerySet):
    def for_user(self, user: User) -> ConsequenceQuerySet:
        if user.is_superuser:
            return self

        # If the user has a person, filter to consequences that they own.
        if user.person_id:
            return self.filter(created_by_id=user.person_id)
        return self.none()


ConsequenceManager = models.Manager.from_queryset(ConsequenceQuerySet)


class Consequence(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    content = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey("accounts.Person", on_delete=models.PROTECT, related_name="consequences")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = ConsequenceManager()

    class Meta:
        ordering = ["content"]

    def __str__(self) -> str:
        return self.content


class AccusationQuerySet(models.QuerySet):
    def for_user(self, user: User) -> AccusationQuerySet:
        # All users can read all accusations
        return self


AccusationManager = models.Manager.from_queryset(AccusationQuerySet)


class Accusation(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    quote = models.TextField(
        help_text="A quote to use as evidence of the alleged crime", max_length=500, blank=False, null=False
    )
    suspect = models.ForeignKey("accounts.Person", on_delete=models.PROTECT, related_name="accusations_suspected")
    created_by = models.ForeignKey("accounts.Person", on_delete=models.PROTECT, related_name="accusations_created")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = AccusationManager()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_prevent_self_accusation",
                check=~models.Q(suspect=F("created_by")),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.suspect} accused by {self.created_by} at {self.created_at}"

    def clean(self) -> None:
        if self.created_by == self.suspect:
            raise ValidationError("Unable to create accusation that suspects the creator.")


class RatificationQuerySet(models.QuerySet):
    def with_score_value(self) -> RatificationQuerySet:
        now = timezone.now()
        most_recent_september_year = now.year - 1 if now.month < 9 else now.year
        most_recent_september = datetime(
            year=most_recent_september_year, month=9, day=1, hour=0, minute=0, tzinfo=timezone.get_current_timezone()
        )
        return self.annotate(
            score_value=Case(
                When(accusation__created_at__gt=most_recent_september, then=Value(1, output_field=SCORE_FIELD)),
                When(
                    accusation__created_at__gt=most_recent_september.replace(year=most_recent_september_year - 1),
                    then=Value(0.75, output_field=SCORE_FIELD),
                ),
                When(
                    accusation__created_at__gt=most_recent_september.replace(year=most_recent_september_year - 2),
                    then=Value(0.5, output_field=SCORE_FIELD),
                ),
                When(
                    accusation__created_at__gt=most_recent_september.replace(year=most_recent_september_year - 3),
                    then=Value(0.25, output_field=SCORE_FIELD),
                ),
                default=Value(0, output_field=SCORE_FIELD),
            ),
        )


RatificationManager = models.Manager.from_queryset(RatificationQuerySet)


class Ratification(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    accusation = models.OneToOneField(Accusation, on_delete=models.CASCADE, related_name="ratification")
    consequence = models.ForeignKey(Consequence, on_delete=models.PROTECT, related_name="+")
    created_by = models.ForeignKey("accounts.Person", on_delete=models.PROTECT, related_name="ratifications")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = RatificationManager()

    def __str__(self) -> str:
        return f"ratified by {self.created_by} at {self.created_at}"

    def clean(self) -> None:
        if self.created_by == self.accusation.created_by:
            raise ValidationError("You cannot ratify an accusation that you made.")

        if self.created_by == self.accusation.suspect:
            raise ValidationError("You cannot ratify an accusation made against you.")
