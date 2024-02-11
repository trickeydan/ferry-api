import uuid

from django.core.exceptions import ValidationError
from django.db import models


class Person(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=255, unique=True)
    discord_id = models.BigIntegerField(verbose_name="Discord ID", blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

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


class Consequence(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    content = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="consequences")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        ordering = ["content"]

    def __str__(self) -> str:
        return self.content


class Accusation(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    quote = models.TextField(
        help_text="A quote to use as evidence of the alleged crime", max_length=500, blank=False, null=False
    )
    suspect = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="accusations_suspected")
    created_by = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="accusations_created")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_prevent_self_accusation",
                check=~models.Q(suspect=models.F("created_by")),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.suspect} accused by {self.created_by} at {self.created_at}"

    def clean(self) -> None:
        if self.created_by == self.suspect:
            raise ValidationError("You cannot accuse yourself.")


class Ratification(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid4, editable=False)
    accusation = models.OneToOneField(Accusation, on_delete=models.CASCADE, related_name="ratification")
    consequence = models.ForeignKey(Consequence, on_delete=models.PROTECT, related_name="+")
    created_by = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="ratifications")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self) -> str:
        return f"ratified by {self.created_by} at {self.created_at}"

    def clean(self) -> None:
        if self.created_by == self.accusation.created_by:
            raise ValidationError("You cannot ratify an accusation that you made.")

        if self.created_by == self.accusation.suspect:
            raise ValidationError("You cannot ratify an accusation made against you.")
