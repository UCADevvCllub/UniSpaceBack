from rest_framework import viewsets, permissions
from django.db.models import Q
from .serializers import EventSerializer, ContactSerializer, ScheduleSerializer, BubbleEventSerializer, GymEventSerializer, MealTimeSerializer, ClassEventSerializer, SubjectSerializer, InstructorSerializer, CohortSerializer, RoomSerializer
from .models import Event, Contact, ClassEvent, BubbleEvent, GymEvent, MealTime, Subject, Instructor, Cohort, Room

<<<<<<< HEAD
=======

>>>>>>> origin/main
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Allow everyone to see
            permission_classes = [permissions.AllowAny]
        else:
            # CHANGE THIS LINE BELOW FROM IsAdminUser TO AllowAny
            permission_classes = [permissions.AllowAny] 
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
            permission_classes = [permissions.IsAdminUser]

        return [permission() for permission in permission_classes]


class ScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.AllowAny]
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
    permission_classes = [permissions.AllowAny]

class GymEventViewSet(viewsets.ModelViewSet):
    queryset = GymEvent.objects.all()
    serializer_class = GymEventSerializer
    permission_classes = [permissions.AllowAny]

class MealTimeViewSet(viewsets.ModelViewSet):
    queryset = MealTime.objects.all()
    serializer_class = MealTimeSerializer
    permission_classes = [permissions.AllowAny]


class ClassEventViewSet(viewsets.ModelViewSet):
    queryset = ClassEvent.objects.all()
    serializer_class = ClassEventSerializer


    # permission_classes = [permissions.IsAdminUser]
    permission_classes = [permissions.AllowAny]





class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.AllowAny]


class InstructorViewSet(viewsets.ModelViewSet):
    queryset = Instructor.objects.all()
    serializer_class = InstructorSerializer
    permission_classes = [permissions.AllowAny]


class CohortViewSet(viewsets.ModelViewSet):
    queryset = Cohort.objects.all()
    serializer_class = CohortSerializer
    permission_classes = [permissions.AllowAny]


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]
