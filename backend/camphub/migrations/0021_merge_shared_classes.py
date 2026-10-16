from django.db import migrations


def drop_stale_linked_event_id(apps, schema_editor):
    # 0020 can run after 0016 on a fresh Postgres database and re-add the column
    # 0016 just removed; ClassEvent no longer has it, so make sure it is gone.
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("ALTER TABLE camphub_classevent DROP COLUMN IF EXISTS linked_event_id;")


class Migration(migrations.Migration):

    dependencies = [
        ('camphub', '0016_remove_classevent_linked_event_id'),
        ('camphub', '0020_add_linked_event_id_if_not_exists'),
    ]

    operations = [
        migrations.RunPython(
            drop_stale_linked_event_id,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
