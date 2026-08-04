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
    day         = serializers.CharField(source='event_id.day')
    start_time  = serializers.TimeField(source='event_id.start_time')
    end_time    = serializers.TimeField(source='event_id.end_time')
    subject     = serializers.CharField(source='subject_id.name')
    instructor  = serializers.SerializerMethodField()
    cohort      = serializers.CharField(source='cohort_id.cohort_name')
    course_year = serializers.CharField(source='cohort_id.study_year_id.year_name')
    class Meta:
        model = ClassEvent
        fields = ['id', 'day', 'start_time', 'end_time', 'subject', 'instructor', 'cohort', 'course_year']
    def get_instructor(self, obj):
        if obj.instructor_id:
            return f"{obj.instructor_id.first_name} {obj.instructor_id.last_name}"
        return None

# class EventWriteSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Event
#         fields = ['day', 'start_time', 'end_time']

class BubbleEventSerializer(serializers.ModelSerializer):
    event = EventSerializer(source='event_id', read_only=True)

    event_data = EventSerializer(write_only=True)

    class Meta:
        model = BubbleEvent
        fields = ['id', 'name', 'event', 'event_data']

    def create(self, validated_data):
        event_data = validated_data.pop('event_data')

        day=event_data['day']
        start_time=event_data['start_time']
        end_time=event_data['end_time']

        overlapping = Event.objects.filter(
            day=day,
            status='BUBBLE',
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        if overlapping.exists():
            raise serializers.ValidationError(
                {"error":"This time slot overlaps with an existing bubble event."}
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

class MealTimeSerializer(serializers.ModelSerializer):
    event = EventSerializer(source='event_id', read_only=True)

    event_data = EventSerializer(write_only=True)

    class Meta:
        model = MealTime
        fields = ['id', 'meal_name', 'event', 'event_data']

    def create(self, validated_data):
        event_data = validated_data.pop('event_data')

        day=event_data['day']
        start_time=event_data['start_time']
        end_time=event_data['end_time']

        overlapping = Event.objects.filter(
           day=day,
            status='MEAL_TIME',
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        if overlapping.exists():
            raise serializers.ValidationError(
                {"error":"This time slot overlaps with an existing meal time event."}
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

class GymEventSerializer(serializers.ModelSerializer):
    event = EventSerializer(source='event_id', read_only=True)

    event_data = EventSerializer(write_only=True)

    class Meta:
        model = GymEvent
        fields = ['id', 'gender', 'event', 'event_data']

    def create(self, validated_data):
        event_data = validated_data.pop('event_data')


        day=event_data['day']
        start_time=event_data['start_time']
        end_time=event_data['end_time']

        overlapping = Event.objects.filter(
            day=day,
            status='GYM',
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        if overlapping.exists():
            raise serializers.ValidationError(
                {"error":"This time slot overlaps with an existing gym event."}
            )

        event, created = Event.objects.get_or_create(
            day=day,
            start_time=start_time,
            end_time=end_time,
            status='GYM'
        )

        if GymEvent.objects.filter(event_id=event).exists():
            raise serializers.ValidationError(
                {"error": "This slot is already booked."}
            )

        return GymEvent.objects.create(
            event_id=event,
            **validated_data
        )


class ClassEventSerializer(serializers.ModelSerializer):
    subject_detail = SubjectSerializer(source='subject_id', read_only=True)
    instructor_detail = InstructorSerializer(source='instructor_id', read_only=True)
    cohort_detail = CohortSerializer(source='cohort_id', read_only=True)
    room_detail = RoomSerializer(source='room_id', read_only=True)
    event_detail = EventSerializer(source='event_id', read_only=True)


    event_data = EventSerializer(write_only=True)

    def update(self, instance, validated_data):
        # 1. Extract the nested event_data
        event_data = validated_data.pop('event_data', None)

        # 2. If event_data exists, update the linked Event model
        if event_data:
            event_instance = instance.event_id  # This is the FK to the Event model
            for attr, value in event_data.items():
                setattr(event_instance, attr, value)
            event_instance.save()

        # 3. Update the rest of the ClassEvent fields (subject, room, etc.)
        return super().update(instance, validated_data)
    
    class Meta:
        model = ClassEvent
        
        fields = [
            'id', 'subject_id', 'instructor_id', 'cohort_id', 'event_id',  'room_id', 'event_data',
            'subject_detail', 'instructor_detail', 'cohort_detail', 'room_detail', 'event_detail'
        ]
    def create(self, validated_data):
        event_data = validated_data.pop('event_data')
        instructor = validated_data.get('instructor_id')
        room = validated_data.get('room_id')
        cohort = validated_data.get('cohort_id')

        day = event_data['day']
        start_time = event_data['start_time']
        end_time = event_data['end_time']

        overlapping_events = Event.objects.filter(
            day=day,
            status='CLASS',
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if overlapping_events.exists():
            
            
            if instructor:
                conflict = ClassEvent.objects.filter(
                    event_id__in=overlapping_events,
                    instructor_id=instructor
                ).select_related('event_id').first()

                if conflict:
                    raise serializers.ValidationError({
                        "instructor_id": f"Instructor already busy: existing class #{conflict.id} "
                        f"on {conflict.event_id.day} {conflict.event_id.start_time}-{conflict.event_id.end_time}"
                    })
            if room:
                room_busy = ClassEvent.objects.filter(
                    event_id__in=overlapping_events,
                    room_id= room
                ).exists()

                if room_busy: 
                   raise serializers.ValidationError(
                       {"room_id": "This room is already booked for another class."})
            if cohort:
                is_in_class = ClassEvent.objects.filter(
                    event_id__in=overlapping_events,
                    cohort_id=cohort
                ).exists()
                if is_in_class:
                    raise serializers.ValidationError(
                        {"cohort_id": "This cohort already has a class scheduled at this time."})

        new_event, created = Event.objects.get_or_create(
            day=day,
            start_time=start_time,
            end_time=end_time,
            status='CLASS'
        )
        
        return ClassEvent.objects.create(
            event_id=new_event,
            **validated_data
        )
