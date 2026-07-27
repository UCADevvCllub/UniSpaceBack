import django.db.models.deletion
from django.db import migrations, models


def migrate_lounge_names_forward(apps, schema_editor):
    TVBooking = apps.get_model("camphub", "TVBooking")
    TVLounge = apps.get_model("camphub", "TVLounge")
    db_alias = schema_editor.connection.alias

    for booking in TVBooking.objects.using(db_alias).exclude(lounge_name=""):
        lounge, _ = TVLounge.objects.using(db_alias).get_or_create(name=booking.lounge_name)
        booking.lounge_id = lounge
        booking.save(update_fields=["lounge_id"])


def migrate_lounge_names_backward(apps, schema_editor):
    TVBooking = apps.get_model("camphub", "TVBooking")
    db_alias = schema_editor.connection.alias

    for booking in TVBooking.objects.using(db_alias).select_related("lounge_id"):
        if booking.lounge_id:
            booking.lounge_name = booking.lounge_id.name
            booking.save(update_fields=["lounge_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("camphub", "0013_remove_cohort_room_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="TVLounge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name="tvbooking",
            name="lounge_id",
            field=models.ForeignKey(
                blank=True,
                db_column="lounge_id",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="camphub.tvlounge",
            ),
        ),
        migrations.RunPython(migrate_lounge_names_forward, migrate_lounge_names_backward),
        migrations.RemoveField(
            model_name="tvbooking",
            name="lounge_name",
        ),
    ]
