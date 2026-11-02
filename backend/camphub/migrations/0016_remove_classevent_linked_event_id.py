from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('camphub', '0015_classevent_share_group_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='classevent',
            name='linked_event_id',
        ),
    ]
