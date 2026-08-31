from django.db import migrations


class Migration(migrations.Migration):
    """
    Merge migration joining two parallel 0007 branches:
    - 0007_remove_cohort_room_id_alter_bubbleevent_name_and_more (our chain)
    - 0007_remove_tvbooking_booking_date_and_more (teammate's chain)
    """

    dependencies = [
        ('camphub', '0007_remove_cohort_room_id_alter_bubbleevent_name_and_more'),
        ('camphub', '0007_remove_tvbooking_booking_date_and_more'),
    ]

    operations = []
