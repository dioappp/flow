# Generated by Django 5.0.6 on 2024-07-12 02:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("distance", "0003_alter_distance_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="distance",
            name="elevasi_dumping",
            field=models.FloatField(),
        ),
    ]