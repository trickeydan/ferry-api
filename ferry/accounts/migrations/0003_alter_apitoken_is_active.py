# Generated by Django 4.2.9 on 2024-02-04 19:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_add_api_token_model"),
    ]

    operations = [
        migrations.AlterField(
            model_name="apitoken",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
