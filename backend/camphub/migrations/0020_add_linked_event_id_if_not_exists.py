from django.db import migrations

def add_column_if_postgres(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE camphub_classevent 
                ADD COLUMN IF NOT EXISTS linked_event_id bigint NULL 
                CONSTRAINT camphub_classevent_linked_event_id_fk 
                REFERENCES camphub_classevent(id) DEFERRABLE INITIALLY DEFERRED;
            """)

class Migration(migrations.Migration):

    dependencies = [
        ('camphub', '0019_alter_bubbleevent_name_alter_studyyear_year_name'),
    ]

    operations = [
        migrations.RunPython(
            add_column_if_postgres,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
