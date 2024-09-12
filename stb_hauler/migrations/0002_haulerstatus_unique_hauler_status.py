# Generated by Django 5.0.6 on 2024-09-12 04:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ritase", "0012_material_remove_cek_ritase_material_and_more"),
        ("stb_hauler", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="haulerstatus",
            constraint=models.UniqueConstraint(
                fields=("date", "shift", "hour", "timeStart", "unit", "report_date"),
                name="unique_hauler_status",
            ),
        ),
    ]
