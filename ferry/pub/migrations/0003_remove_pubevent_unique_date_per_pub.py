# Generated by Django 5.1 on 2024-09-19 16:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_move_person_table"),
        ("pub", "0002_add_discord_id_to_pub_event"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="pubevent",
            name="unique_date_per_pub",
        ),
        migrations.AlterField(
            model_name="pubevent",
            name="attendees",
            field=models.ManyToManyField(blank=True, related_name="events_attended", to="accounts.person"),
        ),
    ]