# Generated by Django 5.0.6 on 2024-06-22 00:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stb_loader', '0003_rename_unitid_loaderid'),
    ]

    operations = [
        migrations.AddField(
            model_name='loaderstatus',
            name='report_date',
            field=models.DateField(null=True),
        ),
    ]
