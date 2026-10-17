from django.db import transaction
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
            'cohort_id', 'cohort_id__study_year_id', 'room_id'
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
            if study_year.isdigit():
                queryset = queryset.filter(cohort_id__study_year_id_id=int(study_year))
            else:
                year_map = {
                    'FRESHMAN': 'FRESH', 'FRESH': 'FRESH',
                    'SOPHOMORE': 'SOPH', 'SOPH': 'SOPH', 'SOF': 'SOPH',
                    'JUNIOR': 'JUN', 'JUN': 'JUN',
                    'SENIOR': 'SEN', 'SEN': 'SEN'
                }
                code = year_map.get(study_year.strip().upper(), study_year)
                queryset = queryset.filter(cohort_id__study_year_id__year_name__iexact=code)
        return queryset

class BubbleEventViewSet(viewsets.ModelViewSet):
    queryset = BubbleEvent.objects.select_related('event_id')
    serializer_class = BubbleEventSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]

class GymEventViewSet(viewsets.ModelViewSet):
    queryset = GymEvent.objects.select_related('event_id')
    serializer_class = GymEventSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]

class MealTimeViewSet(viewsets.ModelViewSet):
    queryset = MealTime.objects.select_related('event_id')
    serializer_class = MealTimeSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]

class ClassEventViewSet(viewsets.ModelViewSet):
    queryset = ClassEvent.objects.select_related(
        'event_id', 'subject_id', 'instructor_id', 'cohort_id', 'room_id'
    )
    serializer_class = ClassEventSerializer

    def get_queryset(self):
        # Start with all ClassEvents and optimize queries
        queryset = ClassEvent.objects.select_related(
            'event_id', 'subject_id', 'instructor_id',
            'cohort_id', 'cohort_id__study_year_id', 'room_id'
        ).all()

        # Extract optional query parameters from request URL
        study_year = self.request.query_params.get('study_year')
        sub_category = self.request.query_params.get('sub_category')
        course = self.request.query_params.get('course')
        day = self.request.query_params.get('day')

        # Apply study_year filter if passed
        if study_year:
            if study_year.isdigit():
                queryset = queryset.filter(cohort_id__study_year_id_id=int(study_year))
            else:
                year_map = {
                    'FRESHMAN': 'FRESH', 'FRESH': 'FRESH', 'FESH': 'FESH',
                    'SOPHOMORE': 'SOPH', 'SOPH': 'SOPH', 'SOF': 'SOPH',
                    'JUNIOR': 'JUN', 'JUN': 'JUN',
                    'SENIOR': 'SEN', 'SEN': 'SEN'
                }
                code = year_map.get(study_year.strip().upper(), study_year)
                queryset = queryset.filter(
                    Q(cohort_id__study_year_id__year_name__iexact=code) |
                    (Q(cohort_id__study_year_id__year_name__iexact='FESH') if code == 'FRESH' else Q())
                )

        # Apply course/cohort/subject filter if passed
        if course:
            if course.isdigit():
                queryset = queryset.filter(Q(cohort_id_id=int(course)) | Q(subject_id_id=int(course)))
            else:
                queryset = queryset.filter(
                    Q(cohort_id__cohort_name__iexact=course) |
                    Q(subject_id__name__icontains=course)
                )

        # Apply day filter if passed
        if day:
            queryset = queryset.filter(event_id__day=day.upper())

        # Apply sub_category filter ONLY if explicitly requested
        if sub_category:
            queryset = queryset.filter(
                Q(sub_category__iexact=sub_category) |
                Q(sub_category__isnull=True) |
                Q(sub_category='')
            )

        return queryset
    # permission_classes = [permissions.IsAdminUser]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]

    def perform_destroy(self, instance):
        # Deleting any row of a shared class deletes the whole class, plus its Event once
        # no lesson uses it any more (so it doesn't linger as an orphan).
        event = instance.event_id
        with transaction.atomic():
            instance.group_members().delete()
            if event and not ClassEvent.objects.filter(event_id=event).exists():
                event.delete()

    # Older endpoint for a class shared by several cohorts; POST /class-events/ with
    # cohort_ids does the same thing.
    @action(detail=False, methods=['post'], url_path='create-linked')
    def create_linked(self, request):
        cohort_ids = request.data.get('cohort_ids')
        if not cohort_ids or len(cohort_ids) < 2:
            return Response({"cohort_ids": "At least two cohort ids are required."}, status=400)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson = serializer.save()
        rows = self.get_serializer(lesson.group_members().order_by('id'), many=True)
        return Response(rows.data, status=201)


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
    queryset = TVBooking.objects.select_related('event_id', 'lounge_id', 'user_id')
    serializer_class = TVBookingSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Students and guests can SEE the lessons
            return [permissions.AllowAny()]
        # Only Admins can Add, Edit, or Delete
        return [permissions.IsAdminUser()]