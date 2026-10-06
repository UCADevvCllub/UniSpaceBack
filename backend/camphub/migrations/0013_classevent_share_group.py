from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('camphub', '0012_alter_cohort_cohort_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='classevent',
            name='share_group',
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
    ]
