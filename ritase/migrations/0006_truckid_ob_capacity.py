# Generated by Django 5.0.6 on 2024-06-21 03:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ritase', '0005_ritase_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='truckid',
            name='OB_capacity',
            field=models.IntegerField(null=True),
        ),
    ]
