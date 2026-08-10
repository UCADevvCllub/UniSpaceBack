from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camphub", "0016_apilog"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bubbleevent",
            name="name",
            field=models.CharField(
                max_length=100,
                default="CLEANING",
                choices=[
                    ("CLEANING", "CLEANING & DISINFECTION"),
                    ("MCHS", "MCHS"),
                    ("ALTAI-NARYN FOOTBALL", "ALTAI-NARYN FOOTBALL SCHOOL"),
                    ("FOOTBALL", "FOOTBALL"),
                    ("football", "football"),
                    ("PE", "PHYSICAL EDUCATION"),
                    ("SECURITY", "UCA SECURITY"),
                    ("VOLLEYBALL", "VOLLEYBALL"),
                    ("BASKETBALL", "BASKETBALL"),
                    ("CRICKET", "CRICKET"),
                    ("JUDO GRAPPLING", "JUDO GRAPPLING"),
                    ("MEP&KITCHEN", "MEP&KITCHEN"),
                    ("TENNIS", "TENNIS"),
                ],
            ),
        ),
    ]
