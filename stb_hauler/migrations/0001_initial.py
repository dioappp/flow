# Generated by Django 5.0.6 on 2024-06-29 00:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('ritase', '0007_ritase_report_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='HaulerStatus',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(null=True)),
                ('date', models.DateField()),
                ('hour', models.SmallIntegerField()),
                ('shift', models.SmallIntegerField()),
                ('timeStart', models.DateTimeField()),
                ('standby_code', models.CharField(max_length=10)),
                ('remarks', models.CharField(max_length=200, null=True)),
                ('report_date', models.DateField()),
                ('unit', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='ritase.truckid')),
            ],
        ),
    ]
