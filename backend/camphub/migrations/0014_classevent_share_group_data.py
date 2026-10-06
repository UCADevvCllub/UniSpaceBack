import uuid

from django.db import migrations


def pairs_to_groups(apps, schema_editor):
    """Turn each linked_event_id pair into a share_group."""
    ClassEvent = apps.get_model('camphub', 'ClassEvent')
    for ce in ClassEvent.objects.filter(linked_event_id__isnull=False, share_group__isnull=True):
        group = uuid.uuid4()
        ids = [ce.id, ce.linked_event_id_id]
        ClassEvent.objects.filter(id__in=ids).update(share_group=group)


def split_shared_events(apps, schema_editor):
    """Give every lesson (or share group) its own Event row.

    Lessons used to get_or_create one Event per day/time, so unrelated lessons at the
    same slot shared a row and editing one moved all of them.
    """
    ClassEvent = apps.get_model('camphub', 'ClassEvent')
    Event = apps.get_model('camphub', 'Event')
    for event in Event.objects.filter(classevent__isnull=False).distinct():
        lessons = list(ClassEvent.objects.filter(event_id=event).order_by('id'))
        buckets = {}
        for ce in lessons:
            key = ce.share_group or f'single-{ce.id}'
            buckets.setdefault(key, []).append(ce)
        for members in list(buckets.values())[1:]:
            clone = Event.objects.create(
                day=event.day, start_time=event.start_time, end_time=event.end_time,
                status=event.status, date=event.date,
            )
            ClassEvent.objects.filter(id__in=[m.id for m in members]).update(event_id=clone)


class Migration(migrations.Migration):

    dependencies = [
        ('camphub', '0013_classevent_share_group'),
    ]

    operations = [
        migrations.RunPython(pairs_to_groups, migrations.RunPython.noop),
        migrations.RunPython(split_shared_events, migrations.RunPython.noop),
    ]
