# Generated by Django 5.1 on 2024-09-13 17:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_move_person_table"),
        ("court", "0003_alter_person_discord_id_alter_person_display_name"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="consequence",
                    name="created_by",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="consequences",
                        to="accounts.person",
                    ),
                ),
                migrations.AlterField(
                    model_name="accusation",
                    name="suspect",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="accusations_suspected",
                        to="accounts.person",
                    ),
                ),
                migrations.AlterField(
                    model_name="ratification",
                    name="created_by",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ratifications",
                        to="accounts.person",
                    ),
                ),
                migrations.AlterField(
                    model_name="accusation",
                    name="created_by",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="accusations_created",
                        to="accounts.person",
                    ),
                ),
            ],
            database_operations=[],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name="Person",
                ),
            ],
            database_operations=[
                migrations.AlterModelTable(
                    name="Person",
                    table="accounts_person",
                )
            ],
        ),
    ]
