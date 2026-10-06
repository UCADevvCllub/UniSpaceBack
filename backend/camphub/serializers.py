import uuid

from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from .bot.crud import day_mapping
from .models import Event, Contact, ClassEvent, StudyYear, GymEvent, MealTime, BubbleEvent, Subject, Instructor, Cohort, Room, TVLounge, TVBooking


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'


class StudyYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyYear
        fields = '__all__'

class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = '__all__'


class CohortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cohort
        fields = '__all__'


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'

class StudyYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyYear
        fields = '__all__'

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'

class TVLoungeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TVLounge
        fields = '__all__'

class TVBookingSerializer(serializers.ModelSerializer):
    lounge_detail = TVLoungeSerializer(source='lounge_id', read_only=True)
    event_detail = EventSerializer(source='event_id', read_only=True)
    event_data = EventSerializer(write_only=True, required=False)

    class Meta:
        model = TVBooking
        fields = [
            'id', 'user_id', 'lounge_id', 'booker_name', 'event_id',
            'lounge_detail', 'event_detail', 'event_data'
        ]

    def create(self, validated_data):
        event_data = validated_data.pop('event_data', None)
        if event_data:
            event = Event.objects.create(
                day=event_data.get('day', 'MON'),
                start_time=event_data['start_time'],
                end_time=event_data['end_time'],
                status='TV',
                date=event_data.get('date')
            )
            validated_data['event_id'] = event

        return TVBooking.objects.create(**validated_data)

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'

class ScheduleSerializer(serializers.ModelSerializer):
    day         = serializers.CharField(source='event_id.day', default='', read_only=True)
    start_time  = serializers.TimeField(source='event_id.start_time', default=None, read_only=True)
    end_time    = serializers.TimeField(source='event_id.end_time', default=None, read_only=True)
    subject     = serializers.SerializerMethodField()
    instructor  = serializers.SerializerMethodField()
    cohort      = serializers.SerializerMethodField()
    course_year = serializers.SerializerMethodField()
    class Meta:
        model = ClassEvent
        fields = ['id', 'day', 'start_time', 'end_time', 'subject', 'instructor', 'cohort', 'course_year']
    def get_subject(self, obj):
        if obj.subject_id and obj.subject_id.name:
            return obj.subject_id.name
        return "General Class"
    def get_instructor(self, obj):
        if obj.instructor_id:
            return f"{obj.instructor_id.first_name} {obj.instructor_id.last_name}"
        return None
    def get_cohort(self, obj):
        if obj.cohort_id:
            return obj.cohort_id.cohort_name
        return None
    def get_course_year(self, obj):
        if obj.cohort_id and obj.cohort_id.study_year_id:
            return obj.cohort_id.study_year_id.year_name
        return None

# class EventWriteSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Event
#         fields = ['day', 'start_time', 'end_time']

class BubbleEventSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    event = EventSerializer(source='event_id', read_only=True)
    event_data = EventSerializer(write_only=True, required=False)

    class Meta:
        model = BubbleEvent
        fields = ['id', 'name', 'event', 'event_data']

    def validate_name(self, value):
        if not value:
            return value
        cleaned = value.strip().upper()
        valid_keys = [choice[0] for choice in BubbleEvent.CHOICES]
        
        if cleaned in valid_keys:
            return cleaned
            
        # Check if matched against choice labels (display names)
        label_map = {choice[1].upper(): choice[0] for choice in BubbleEvent.CHOICES}
        if cleaned in label_map:
            return label_map[cleaned]

        raise serializers.ValidationError(f'"{value}" is not a valid choice.')

    def create(self, validated_data):
        event_data = validated_data.pop('event_data')

        day = event_data['day']
        start_time = event_data['start_time']
        end_time = event_data['end_time']

        overlapping = Event.objects.filter(
            day=day,
            status='BUBBLE',
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        if overlapping.exists():
            raise serializers.ValidationError(
                {"error": "This time slot overlaps with an existing bubble event."}
            )

        event, created = Event.objects.get_or_create(
            day=day,
            start_time=start_time,
            end_time=end_time,
            status='BUBBLE'
        )
        if BubbleEvent.objects.filter(event_id=event).exists():
            raise serializers.ValidationError(
                {"error": "This slot is already booked."}
            )

        return BubbleEvent.objects.create(
            event_id=event,
            **validated_data
        )

    def update(self, instance, validated_data):
        event_data = validated_data.pop('event_data', None)
        if event_data:
            day = event_data.get('day', instance.event_id.day if instance.event_id else 'MON')
            start_time = event_data.get('start_time', instance.event_id.start_time if instance.event_id else None)
            end_time = event_data.get('end_time', instance.event_id.end_time if instance.event_id else None)

            overlapping = Event.objects.filter(
                day=day,
                status='BUBBLE',
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            if instance.event_id:
                overlapping = overlapping.exclude(pk=instance.event_id.pk)

            if overlapping.exists():
                raise serializers.ValidationError(
                    {"error": "This time slot overlaps with an existing bubble event."}
                )

            if instance.event_id:
                instance.event_id.day = day
                instance.event_id.start_time = start_time
                instance.event_id.end_time = end_time
                instance.event_id.save()

        return super().update(instance, validated_data)


class MealTimeSerializer(serializers.ModelSerializer):
    event = EventSerializer(source='event_id', read_only=True)
    event_data = EventSerializer(write_only=True, required=False)

    class Meta:
        model = MealTime
        fields = ['id', 'meal_name', 'event', 'event_data']

    def create(self, validated_data):
        event_data = validated_data.pop('event_data')

        day = event_data['day']
        start_time = event_data['start_time']
        end_time = event_data['end_time']

        overlapping = Event.objects.filter(
            day=day,
            status='MEAL_TIME',
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        if overlapping.exists():
            raise serializers.ValidationError(
                {"error": "This time slot overlaps with an existing meal time event."}
            )

        event, created = Event.objects.get_or_create(
            day=day,
            start_time=start_time,
            end_time=end_time,
            status='MEAL_TIME'
        )

        if MealTime.objects.filter(event_id=event).exists():
            raise serializers.ValidationError(
                {"error": "This slot is already booked."}
            )

        return MealTime.objects.create(
            event_id=event,
            **validated_data
        )

    def update(self, instance, validated_data):
        event_data = validated_data.pop('event_data', None)
        if event_data:
            day = event_data.get('day', instance.event_id.day if instance.event_id else 'MON')
            start_time = event_data.get('start_time', instance.event_id.start_time if instance.event_id else None)
            end_time = event_data.get('end_time', instance.event_id.end_time if instance.event_id else None)

            overlapping = Event.objects.filter(
                day=day,
                status='MEAL_TIME',
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            if instance.event_id:
                overlapping = overlapping.exclude(pk=instance.event_id.pk)

            if overlapping.exists():
                raise serializers.ValidationError(
                    {"error": "This time slot overlaps with an existing meal time event."}
                )

            if instance.event_id:
                instance.event_id.day = day
                instance.event_id.start_time = start_time
                instance.event_id.end_time = end_time
                instance.event_id.save()

        return super().update(instance, validated_data)


class GymEventSerializer(serializers.ModelSerializer):
    event = EventSerializer(source='event_id', read_only=True)
    event_data = EventSerializer(write_only=True, required=False)

    class Meta:
        model = GymEvent
        fields = ['id', 'gender', 'event', 'event_data']

    def create(self, validated_data):
        event_data = validated_data.pop('event_data')
        gender = validated_data.get('gender', 'MALE')

        day = event_data['day']
        start_time = event_data['start_time']
        end_time = event_data['end_time']

        overlapping = GymEvent.objects.filter(
            gender=gender,
            event_id__day=day,
            event_id__status='GYM',
            event_id__start_time__lt=end_time,
            event_id__end_time__gt=start_time
        )

        if overlapping.exists():
            raise serializers.ValidationError(
                {"error": "This time slot overlaps with an existing gym event."}
            )

        event, created = Event.objects.get_or_create(
            day=day,
            start_time=start_time,
            end_time=end_time,
            status='GYM'
        )

        if GymEvent.objects.filter(event_id=event, gender=gender).exists():
            raise serializers.ValidationError(
                {"error": "This slot is already booked."}
            )

        return GymEvent.objects.create(
            event_id=event,
            **validated_data
        )

    def update(self, instance, validated_data):
        event_data = validated_data.pop('event_data', None)
        gender = validated_data.get('gender', instance.gender)

        if event_data:
            day = event_data.get('day', instance.event_id.day if instance.event_id else 'MON')
            start_time = event_data.get('start_time', instance.event_id.start_time if instance.event_id else None)
            end_time = event_data.get('end_time', instance.event_id.end_time if instance.event_id else None)

            overlapping = GymEvent.objects.filter(
                gender=gender,
                event_id__day=day,
                event_id__status='GYM',
                event_id__start_time__lt=end_time,
                event_id__end_time__gt=start_time
            ).exclude(pk=instance.pk)

            if overlapping.exists():
                raise serializers.ValidationError(
                    {"error": "This time slot overlaps with an existing gym event."}
                )

            if instance.event_id:
                instance.event_id.day = day
                instance.event_id.start_time = start_time
                instance.event_id.end_time = end_time
                instance.event_id.save()

        return super().update(instance, validated_data)


def find_class_clash(day, start_time, end_time, instructor=None, room=None, cohorts=(), exclude_ids=()):
    """Returns a {field: message} error for the first clash with an existing lesson, else None.

    Lessons in exclude_ids (the lesson's own share group) never clash with it.
    """
    overlapping = ClassEvent.objects.filter(
        event_id__day=day,
        event_id__status='CLASS',
        event_id__start_time__lt=end_time,
        event_id__end_time__gt=start_time,
    ).exclude(id__in=exclude_ids).select_related('event_id')

    if instructor:
        conflict = overlapping.filter(instructor_id=instructor).first()
        if conflict:
            return {"instructor_id": f"Instructor already busy: existing class #{conflict.id} "
                    f"on {conflict.event_id.day} {conflict.event_id.start_time}-{conflict.event_id.end_time}"}
    if room and overlapping.filter(room_id=room).exists():
        return {"room_id": "This room is already booked for another class."}
    if cohorts and overlapping.filter(cohort_id__in=cohorts).exists():
        return {"cohort_id": "This cohort already has a class scheduled at this time."}
    return None


class ClassEventSerializer(serializers.ModelSerializer):
    subject_detail = SubjectSerializer(source='subject_id', read_only=True)
    instructor_detail = InstructorSerializer(source='instructor_id', read_only=True)
    cohort_detail = CohortSerializer(source='cohort_id', read_only=True)
    room_detail = RoomSerializer(source='room_id', read_only=True)
    event_detail = EventSerializer(source='event_id', read_only=True)
    share_group = serializers.UUIDField(read_only=True)

    event_data = EventSerializer(write_only=True)
    # Every cohort the class is taught to. More than one makes it a shared class: one row
    # per cohort, all in the same share_group. On update it replaces the group's cohorts.
    cohort_ids = serializers.PrimaryKeyRelatedField(
        queryset=Cohort.objects.all(), many=True, write_only=True, required=False)

    class Meta:
        model = ClassEvent

        fields = [
            'id', 'subject_id', 'instructor_id', 'cohort_id', 'event_id', 'room_id', 'event_data',
            'cohort_ids', 'subject_detail', 'instructor_detail', 'cohort_detail', 'room_detail',
            'event_detail', 'share_group'
        ]
        read_only_fields = ['event_id']

    def validate(self, attrs):
        event_data = attrs.get('event_data') or {}
        start = event_data.get('start_time') or (self.instance and self.instance.event_id and self.instance.event_id.start_time)
        end = event_data.get('end_time') or (self.instance and self.instance.event_id and self.instance.event_id.end_time)
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs

    def create(self, validated_data):
        event_data = validated_data.pop('event_data')
        cohorts = list(dict.fromkeys(validated_data.pop('cohort_ids', None) or [validated_data.get('cohort_id')]))
        cohorts = [c for c in cohorts if c is not None]

        clash = find_class_clash(
            event_data['day'], event_data['start_time'], event_data['end_time'],
            instructor=validated_data.get('instructor_id'), room=validated_data.get('room_id'),
            cohorts=cohorts,
        )
        if clash:
            raise serializers.ValidationError(clash)

        with transaction.atomic():
            # Each lesson (or share group) owns its Event, so editing one never moves another.
            event = Event.objects.create(
                day=event_data['day'],
                start_time=event_data['start_time'],
                end_time=event_data['end_time'],
                status='CLASS',
            )
            group = uuid.uuid4() if len(cohorts) > 1 else None
            validated_data.pop('cohort_id', None)
            rows = [
                ClassEvent.objects.create(event_id=event, cohort_id=cohort, share_group=group, **validated_data)
                for cohort in (cohorts or [None])
            ]
        return rows[0]

    def update(self, instance, validated_data):
        event_data = validated_data.pop('event_data', None) or {}
        new_cohorts = validated_data.pop('cohort_ids', None)

        members = list(instance.group_members())
        member_ids = [m.id for m in members]
        if 'cohort_id' in validated_data:
            instance.cohort_id = validated_data.pop('cohort_id')
        if new_cohorts is None:
            new_cohorts = [instance.cohort_id if m.id == instance.id else m.cohort_id for m in members]
        # A lesson without any cohort stays a single row with no cohort.
        new_cohorts = [c for c in dict.fromkeys(new_cohorts) if c is not None] or [None]

        event = instance.event_id
        day = event_data.get('day', event.day if event else 'MON')
        start_time = event_data.get('start_time', event.start_time if event else None)
        end_time = event_data.get('end_time', event.end_time if event else None)
        shared = {f: validated_data.get(f, getattr(instance, f)) for f in ('subject_id', 'instructor_id', 'room_id')}

        clash = find_class_clash(
            day, start_time, end_time,
            instructor=shared['instructor_id'], room=shared['room_id'],
            cohorts=[c for c in new_cohorts if c is not None], exclude_ids=member_ids,
        )
        if clash:
            raise serializers.ValidationError(clash)

        with transaction.atomic():
            # Older rows may still share an Event with unrelated lessons; detach first.
            if event is None or ClassEvent.objects.filter(event_id=event).exclude(id__in=member_ids).exists():
                event = Event(status='CLASS')
            event.day, event.start_time, event.end_time = day, start_time, end_time
            event.save()

            group = (instance.share_group or uuid.uuid4()) if len(new_cohorts) > 1 else None
            keep = {}
            # The edited row goes first so it survives whenever its cohort is still wanted.
            for m in sorted(members, key=lambda m: m.id != instance.id):
                cohort = instance.cohort_id if m.id == instance.id else m.cohort_id
                if cohort in new_cohorts and cohort not in keep:
                    keep[cohort] = m
                else:
                    m.delete()
            for cohort in new_cohorts:
                row = keep.get(cohort) or ClassEvent(cohort_id=cohort)
                for f, value in shared.items():
                    setattr(row, f, value)
                row.cohort_id = cohort
                row.event_id = event
                row.share_group = group
                row.save()
                keep[cohort] = row

        return keep.get(instance.cohort_id) or next(iter(keep.values()), instance)
