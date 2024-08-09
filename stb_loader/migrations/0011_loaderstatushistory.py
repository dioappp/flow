# Generated by Django 5.0.6 on 2024-08-09 07:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stb_loader", "0010_loaderid_ellipse"),
    ]

    operations = [
        migrations.CreateModel(
            name="LoaderStatusHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("add", "Add"),
                            ("update", "Update"),
                            ("delete", "Delete"),
                        ],
                        max_length=10,
                    ),
                ),
                ("loader_status_id", models.IntegerField()),
                ("data", models.JSONField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
