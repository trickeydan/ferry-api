# Generated by Django 4.2.10 on 2024-02-17 15:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("court", "0003_alter_person_discord_id_alter_person_display_name"),
        ("accounts", "0003_alter_apitoken_is_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="person",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="court.person",
            ),
        ),
    ]
