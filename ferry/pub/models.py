from __future__ import annotations

import uuid
from datetime import datetime

from django.db import models
from django.utils import timezone

from ferry.accounts.models import User


class PubQuerySet(models.QuerySet):
    def for_user(self, user: User) -> PubQuerySet:
        return self.all()


PubManager = models.Manager.from_queryset(PubQuerySet)


class Pub(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, max_length=50)
    emoji = models.CharField(max_length=1)
    map_url = models.URLField()
    menu_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = PubManager()

    def __str__(self) -> str:
        return f"{self.name} {self.emoji}"


class PubTable(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    pub = models.ForeignKey(Pub, on_delete=models.PROTECT, related_name="tables")
    number = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "pub",
                "number",
                name="unique_table_number_within_pub",
                violation_error_message="Another table has that number at that pub",
            )
        ]

    def __str__(self) -> str:
        return f"Table {self.number} @ {self.pub}"


class PubEventQuerySet(models.QuerySet):
    def for_user(self, user: User) -> PubEventQuerySet:
        return self.all()

    def get_next(self, *, timestamp: datetime | None = None) -> PubEvent | None:
        if timestamp is None:
            timestamp = timezone.now()
        upcoming_pubs = PubEvent.objects.filter(timestamp__gte=timestamp).order_by("timestamp")
        return upcoming_pubs.first()


PubEventManager = models.Manager.from_queryset(PubEventQuerySet)


class PubEvent(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)

    timestamp = models.DateTimeField("Timestamp of Event")
    pub = models.ForeignKey(Pub, on_delete=models.PROTECT, related_name="events")
    discord_id = models.BigIntegerField(verbose_name="Discord Scheduled Event ID", blank=True, null=True, unique=True)
    table = models.ForeignKey(PubTable, on_delete=models.PROTECT, blank=True, null=True, related_name="events")

    created_by = models.ForeignKey("accounts.Person", on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = PubEventManager()

    # TODO: validate table is at pub

    class Meta:
        ordering = ("-timestamp",)

    def __str__(self) -> str:
        return f"Pub at {self.pub} on {self.timestamp.date()}"

    @property
    def is_past(self) -> bool:
        return timezone.now().date() > self.timestamp.date()


class PubEventRSVPMethod(models.TextChoices):
    AUTO = "A", "AutoPub"
    DISCORD = "D", "Discord"
    MANUAL = "M", "Manual Entry"  # aka. criminals
    WEB = "W", "Web"


class PubEventRSVP(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)

    person = models.ForeignKey("accounts.Person", on_delete=models.PROTECT, related_name="pub_event_rsvps")
    pub_event = models.ForeignKey(PubEvent, on_delete=models.CASCADE, related_name="pub_event_rsvps")
    is_attending = models.BooleanField()  # Can be false for an opt-out.
    method = models.CharField(max_length=1, choices=PubEventRSVPMethod)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("person", "pub_event"), name="one_rsvp_per_person_per_event"),
            models.CheckConstraint(
                check=(
                    models.Q(method=PubEventRSVPMethod.AUTO, is_attending=True)
                    | models.Q(method=PubEventRSVPMethod.DISCORD, is_attending=True)
                    | models.Q(method=PubEventRSVPMethod.MANUAL, is_attending=True)
                    | models.Q(method=PubEventRSVPMethod.WEB)
                ),
                name="correct_value_for_method",
                violation_error_message="Invalid attendance value for RSVP method",
            ),
        ]

    def __str__(self) -> str:
        if self.is_attending:
            return f"{self.person} is attending {self.pub_event}"
        else:
            return f"{self.person} is not attending {self.pub_event}"


class PubEventBooking(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    pub_event = models.OneToOneField(PubEvent, on_delete=models.CASCADE, related_name="booking")

    table_size = models.PositiveSmallIntegerField(verbose_name="Table size")

    created_by = models.ForeignKey("accounts.Person", on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self) -> str:
        return f"Booking made for {self.pub_event}"
