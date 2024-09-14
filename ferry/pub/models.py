from __future__ import annotations

import uuid

from django.db import models

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


class PubEvent(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)

    timestamp = models.DateTimeField("Timestamp of Event")
    pub = models.ForeignKey(Pub, on_delete=models.PROTECT, related_name="events")
    table = models.ForeignKey(PubTable, on_delete=models.PROTECT, blank=True, null=True, related_name="events")
    attendees = models.ManyToManyField("accounts.Person", related_name="events_attended")

    created_by = models.ForeignKey("accounts.Person", on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        # TODO: validate table is at pub
        constraints = [
            models.UniqueConstraint(
                models.functions.TruncDate("timestamp"),
                "pub",
                name="unique_date_per_pub",
                violation_error_message="There is another event at that pub on that date.",
            ),
        ]

    def __str__(self) -> str:
        return f"Pub at {self.pub} on {self.timestamp.date()}"
