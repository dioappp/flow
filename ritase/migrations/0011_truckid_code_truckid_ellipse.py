# Generated by Django 5.0.6 on 2024-07-19 03:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ritase", "0010_remove_cek_ritase_nrp_remove_cek_ritase_hm_end_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="truckid",
            name="code",
            field=models.CharField(max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="truckid",
            name="ellipse",
            field=models.CharField(max_length=20, null=True),
        ),
    ]
