from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('camphub', '0012_alter_cohort_cohort_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gymevent',
            name='gender',
            field=models.CharField(
                choices=[
                    ('MALE', 'Male'),
                    ('FEMALE', 'Female'),
                    ('CLEANING', 'Cleaning'),
                    ('FACULTY', 'Faculty / Ops'),
                ],
                default='MALE',
                max_length=50
            ),
        ),
    ]
