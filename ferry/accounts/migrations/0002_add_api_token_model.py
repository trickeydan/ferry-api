# Generated by Django 4.2.9 on 2024-02-04 16:55

import secrets
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="APIToken",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "token",
                    models.CharField(
                        default=secrets.token_urlsafe,
                        editable=False,
                        max_length=128,
                        unique=True,
                    ),
                ),
                ("is_active", models.BooleanField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
