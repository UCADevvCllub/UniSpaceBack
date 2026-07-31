from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camphub", "0014_tvlounge"),
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
