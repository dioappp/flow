# Generated by Django 5.0.6 on 2024-07-11 06:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("distance", "0002_distance_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="distance",
            name="date",
            field=models.DateField(),
        ),
    ]