# Generated by Django 5.0.6 on 2024-06-19 06:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stb_loader', '0002_remove_loaderstatus_timeend'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='UnitID',
            new_name='loaderID',
        ),
    ]
