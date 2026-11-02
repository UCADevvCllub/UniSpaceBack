from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('camphub', '0013_alter_gymevent_gender'),
    ]

    operations = [
        migrations.AddField(
            model_name='classevent',
            name='share_group',
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
    ]
