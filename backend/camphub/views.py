from rest_framework import viewsets, permissions
from django.db.models import Q
from .serializers import EventSerializer, ContactSerializer, ScheduleSerializer, BubbleEventSerializer, GymEventSerializer, MealTimeSerializer, ClassEventSerializer, SubjectSerializer, InstructorSerializer, CohortSerializer, RoomSerializer, StudyYearSerializer, TVLoungeSerializer, TVBookingSerializer
from .models import Event, Contact, ClassEvent, BubbleEvent, GymEvent, MealTime, Subject, Instructor, Cohort, Room, StudyYear, TVLounge, TVBooking
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Allow everyone to see
            permission_classes = [permissions.AllowAny]
        else:
            # CHANGE THIS LINE BELOW FROM IsAdminUser TO AllowAny
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Allow everyone to see
            permission_classes = [permissions.AllowAny]
        else:
            # Only admins can change
            permission_classes = [IsAdminUser]

        return [permission() for permission in permission_classes]


class ScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ScheduleSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]


    def get_queryset(self):
        queryset = ClassEvent.objects.select_related(
            'event_id', 'subject_id', 'instructor_id',
            'cohort_id', 'cohort_id__study_year_id'
        )
        day = self.request.query_params.get('day')
        course = self.request.query_params.get('course')
        study_year = self.request.query_params.get('study_year')

        if day:
            queryset = queryset.filter(event_id__day=day.upper())
        if course:
            if course.isdigit():
                queryset = queryset.filter(cohort_id=int(course))
            else:
                queryset = queryset.filter(cohort_id__cohort_name__iexact=course)
        if study_year:
            queryset = queryset.filter(cohort_id__study_year_id__year_name__iexact=study_year)
        return queryset

class BubbleEventViewSet(viewsets.ModelViewSet):
    queryset = BubbleEvent.objects.all()
    serializer_class = BubbleEventSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]

class GymEventViewSet(viewsets.ModelViewSet):
    queryset = GymEvent.objects.all()
    serializer_class = GymEventSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]

class MealTimeViewSet(viewsets.ModelViewSet):
    queryset = MealTime.objects.all()
    serializer_class = MealTimeSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]


class ClassEventViewSet(viewsets.ModelViewSet):
    queryset =ClassEvent.objects.all()
    serializer_class = ClassEventSerializer


    # permission_classes = [permissions.IsAdminUser]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]

    # Creates a class shared by two cohorts (e.g. CS + CM taking it together) as one
    # linked pair: two ClassEvent rows sharing the same Event (day/time), each with
    # its own cohort, pointing at each other via linked_event_id so deleting either
    # one cascades to delete the other (see ClassEvent.linked_event_id, on_delete=CASCADE).
    @action(detail=False, methods=['post'], url_path='create-linked')
    def create_linked(self, request):
        data = request.data
        cohort_ids = data.get('cohort_ids')
        event_data = data.get('event_data')

        if not cohort_ids or len(cohort_ids) != 2:
            return Response({"cohort_ids": "Exactly two cohort ids are required."}, status=400)
        if not event_data:
            return Response({"event_data": "event_data is required."}, status=400)

        subject_id = data.get('subject_id')
        instructor_id = data.get('instructor_id')
        room_id = data.get('room_id')

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
            if instructor_id:
                conflict = ClassEvent.objects.filter(
                    event_id__in=overlapping_events,
                    instructor_id=instructor_id
                ).select_related('event_id').first()

                if conflict:
                    return Response({
                        "instructor_id": f"Instructor already busy: existing class #{conflict.id} "
                        f"on {conflict.event_id.day} {conflict.event_id.start_time}-{conflict.event_id.end_time}"
                    }, status=400)
            if room_id:
                if ClassEvent.objects.filter(event_id__in=overlapping_events, room_id=room_id).exists():
                    return Response({"room_id": "This room is already booked for another class."}, status=400)
            for cohort_id in cohort_ids:
                if ClassEvent.objects.filter(event_id__in=overlapping_events, cohort_id=cohort_id).exists():
                    return Response({"cohort_id": "This cohort already has a class scheduled at this time."}, status=400)

        event, created = Event.objects.get_or_create(
            day=day,
            start_time=start_time,
            end_time=end_time,
            status='CLASS'
        )

        first = ClassEvent.objects.create(
            event_id=event,
            subject_id_id=subject_id,
            instructor_id_id=instructor_id,
            room_id_id=room_id,
            cohort_id_id=cohort_ids[0],
        )
        second = ClassEvent.objects.create(
            event_id=event,
            subject_id_id=subject_id,
            instructor_id_id=instructor_id,
            room_id_id=room_id,
            cohort_id_id=cohort_ids[1],
            linked_event_id_id=first.id,
        )
        first.linked_event_id_id = second.id
        first.save(update_fields=['linked_event_id'])

        serializer = self.get_serializer([first, second], many=True)
        return Response(serializer.data, status=201)


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]


class InstructorViewSet(viewsets.ModelViewSet):
    queryset = Instructor.objects.all()
    serializer_class = InstructorSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]


class CohortViewSet(viewsets.ModelViewSet):
    queryset = Cohort.objects.all()
    serializer_class = CohortSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]


class StudyYearViewSet(viewsets.ModelViewSet):
    queryset = StudyYear.objects.all()
    serializer_class = StudyYearSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]


class TVLoungeViewSet(viewsets.ModelViewSet):
    queryset = TVLounge.objects.all()
    serializer_class = TVLoungeSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]


class TVBookingViewSet(viewsets.ModelViewSet):
    queryset = TVBooking.objects.all()
    serializer_class = TVBookingSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]
