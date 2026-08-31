from django.db import migrations

# Cohort.room_id never made sense: a room belongs to a specific ClassEvent,
# not to a whole cohort. By this point (after 0011) the column is reliably
# named 'room_id' everywhere, so a plain RemoveField is safe.


class Migration(migrations.Migration):

    dependencies = [
        ("camphub", "0012_create_missing_tables"),
    ]

    operations = [
        # Cohort.room_id was already removed in 0007_remove_cohort_room_id...
        # Keeping this migration as a no-op to preserve the history chain.
    ]
