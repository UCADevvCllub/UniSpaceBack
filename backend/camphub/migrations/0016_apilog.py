import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camphub", "0015_bubbleevent_name_choices"),
    ]

    operations = [
        migrations.CreateModel(
            name="APILog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("endpoint", models.CharField(max_length=255)),
                ("method", models.CharField(max_length=10)),
                ("status_code", models.IntegerField()),
                ("request_body", models.TextField(blank=True, null=True)),
                ("response_body", models.TextField(blank=True, null=True)),
                ("execution_time_ms", models.FloatField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "API Log",
                "verbose_name_plural": "API Logs",
                "db_table": "api_logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="APISQLLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sql", models.TextField()),
                ("params", models.TextField(blank=True, null=True)),
                ("duration_ms", models.FloatField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("api_log", models.ForeignKey(db_column="api_log_id", on_delete=django.db.models.deletion.CASCADE, related_name="sql_queries", to="camphub.apilog")),
            ],
            options={
                "verbose_name": "API SQL Log",
                "verbose_name_plural": "API SQL Logs",
                "db_table": "api_sql_logs",
                "ordering": ["id"],
            },
        ),
    ]
