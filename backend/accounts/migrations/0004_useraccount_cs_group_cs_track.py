from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_useraccount_major'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraccount',
            name='cs_group',
            field=models.CharField(
                blank=True,
                choices=[('CS_A', 'CS A'), ('CS_B', 'CS B')],
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='useraccount',
            name='cs_track',
            field=models.CharField(
                blank=True,
                choices=[('CS_DIRECT', 'Direct'), ('POST_PREP', 'Post Prep')],
                max_length=15,
                null=True,
            ),
        ),
    ]
