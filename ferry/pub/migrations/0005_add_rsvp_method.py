# Generated by Django 5.1 on 2024-10-15 18:02

from django.apps.registry import Apps
from django.db import migrations, models, transaction
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def update_method_for_existing_rsvp(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Person = apps.get_model("accounts", "Person")
    PubEventRSVP = apps.get_model("pub", "PubEventRSVP")

    with transaction.atomic():
        if cm := Person.objects.filter(id="fbd84962-c151-49c5-9f72-e48f5e73ae61").first():
            for rsvp in PubEventRSVP.objects.filter(person=cm):
                rsvp.method = "W"
                rsvp.save(update_fields=["method"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_add_name_to_api_tokens"),
        ("pub", "0004_pub_event_rsvp"),
    ]

    operations = [
        migrations.AddField(
            model_name="pubeventrsvp",
            name="method",
            field=models.CharField(
                choices=[("A", "AutoPub"), ("D", "Discord"), ("W", "Web")],
                default="D",
                max_length=1,
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="pubeventrsvp",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("is_attending", True), ("method", "A")),
                    models.Q(("is_attending", True), ("method", "D")),
                    ("method", "W"),
                    _connector="OR",
                ),
                name="correct_value_for_method",
                violation_error_message="Invalid attendance value for RSVP method",
            ),
        ),
        migrations.RunPython(
            update_method_for_existing_rsvp,
            migrations.RunPython.noop,
        ),
    ]
