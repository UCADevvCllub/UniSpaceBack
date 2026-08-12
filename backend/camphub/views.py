import os
import json
import datetime

from rest_framework import viewsets, permissions, views, response, status
from django.db.models import Q
from django.shortcuts import redirect
from django.conf import settings
from .serializers import (EventSerializer, ContactSerializer, ScheduleSerializer,
                          BubbleEventSerializer, GymEventSerializer, MealTimeSerializer,
                          ClassEventSerializer, SubjectSerializer, InstructorSerializer,
                          CohortSerializer, RoomSerializer, StudyYearSerializer,
                          TVLoungeSerializer, TVBookingSerializer)

from .models import (Event, Contact, ClassEvent, BubbleEvent, GymEvent,
                     MealTime, Subject, Instructor, Cohort, Room,
                     StudyYear, TVLounge, TVBooking, GoogleCredential)

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
SCOPES = ['https://www.googleapis.com/auth/calendar']

DAY_MAP = {
    'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6
}


def get_or_create_unispace_calendar(service, user_creds):
    if user_creds.unispace_calendar_id:
        try:
            service.calendars().get(calendarId=user_creds.unispace_calendar_id).execute()
            return user_creds.unispace_calendar_id
        except:
            user_creds.unispace_calendar_id = None
            user_creds.save()

    calendar_list = service.calendarList().list().execute()
    for entry in calendar_list.get('items', []):
        if entry.get('summary') == 'UniSpace Lessons':
            user_creds.unispace_calendar_id = entry['id']
            user_creds.save()
            return entry['id']

    new_calendar = {'summary': 'UniSpace Lessons', 'timeZone': 'UTC'}
    created_calendar = service.calendars().insert(body=new_calendar).execute()
    user_creds.unispace_calendar_id = created_calendar['id']
    user_creds.save()
    return created_calendar['id']


def google_login(request):
    client_secrets_path = os.path.join(settings.BASE_DIR, 'client_secret.json')
    flow = Flow.from_client_secrets_file(client_secrets_path, scopes=SCOPES,
                                         redirect_uri='http://localhost:8000/api/google/callback/')
    auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
    request.session['google_oauth_state'] = state
    request.session['google_oauth_verifier'] = flow.code_verifier
    return redirect(auth_url)


def google_callback(request):
    client_secrets_path = os.path.join(settings.BASE_DIR, 'client_secret.json')
    state = request.session.get('google_oauth_state') or request.GET.get('state')
    flow = Flow.from_client_secrets_file(client_secrets_path, scopes=SCOPES,
                                         redirect_uri='http://localhost:8000/api/google/callback/', state=state)
    flow.code_verifier = request.session.get('google_oauth_verifier')
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    creds_data = json.loads(flow.credentials.to_json())
    user = User.objects.first()
    GoogleCredential.objects.update_or_create(user=user, defaults={'token': creds_data})
    return redirect('http://localhost:3000/?sync=success')


class CalendarEventList(views.APIView):

    def get(self, request):
        data = []
        local_events = Event.objects.all()
        for e in local_events:
            event_date = e.date or (datetime.date.today() - datetime.timedelta(
                days=datetime.date.today().weekday()) + datetime.timedelta(days=DAY_MAP.get(e.day, 0)))

            start_dt = datetime.datetime.combine(event_date, e.start_time).isoformat()
            end_dt = datetime.datetime.combine(event_date, e.end_time).isoformat()

            data.append({
                "id": f"local_{e.id}",
                "title": e.get_status_display(),
                "start": start_dt,
                "end": end_dt,
                "backgroundColor": "#10b981",
            })

        try:
            user_creds = GoogleCredential.objects.first()
            if user_creds:
                creds = Credentials.from_authorized_user_info(user_creds.token)
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    user_creds.token = json.loads(creds.to_json());
                    user_creds.save()

                service = build('calendar', 'v3', credentials=creds)
                unispace_id = get_or_create_unispace_calendar(service, user_creds)
                res = service.events().list(calendarId=unispace_id, singleEvents=True).execute()
                for ge in res.get('items', []):
                    data.append({
                        "id": f"google_{ge.get('id')}",
                        "title": f" {ge.get('summary')}",
                        "start": ge['start'].get('dateTime') or ge['start'].get('date'),
                        "end": ge['end'].get('dateTime') or ge['end'].get('date'),
                        "backgroundColor": "#4285F4",  # Blue for Google
                    })
        except:
            pass
        return response.Response(data)

    def post(self, request):
        target = request.data.get('target', 'local')
        if target == 'local':
            return response.Response({"status": "created local"}, status=201)
        else:
            user_creds = GoogleCredential.objects.first()
            creds = Credentials.from_authorized_user_info(user_creds.token)
            service = build('calendar', 'v3', credentials=creds)
            unispace_id = get_or_create_unispace_calendar(service, user_creds)
            g_event = {'summary': request.data['title'], 'start': {'dateTime': request.data['start']},
                       'end': {'dateTime': request.data['end']}}
            service.events().insert(calendarId=unispace_id, body=g_event).execute()
            return response.Response({"status": "created Google"}, status=201)


class CalendarEventDetail(views.APIView):
    def patch(self, request, pk):
        if pk.isdigit():  # Local
            return response.Response({"status": "local update logic here"})
        else:
            user_creds = GoogleCredential.objects.first()
            creds = Credentials.from_authorized_user_info(user_creds.token)
            service = build('calendar', 'v3', credentials=creds)
            unispace_id = get_or_create_unispace_calendar(service, user_creds)
            g_event = service.events().get(calendarId=unispace_id, eventId=pk).execute()
            if 'title' in request.data: g_event['summary'] = request.data['title']
            if 'start' in request.data: g_event['start'] = {'dateTime': request.data['start']}
            if 'end' in request.data: g_event['end'] = {'dateTime': request.data['end']}
            service.events().update(calendarId=unispace_id, eventId=pk, body=g_event).execute()
            return response.Response({"status": "google updated"})

    def delete(self, request, pk):
        if not pk.isdigit():  # Google
            user_creds = GoogleCredential.objects.first()
            creds = Credentials.from_authorized_user_info(user_creds.token)
            service = build('calendar', 'v3', credentials=creds)
            unispace_id = get_or_create_unispace_calendar(service, user_creds)
            service.events().delete(calendarId=unispace_id, eventId=pk).execute()
        return response.Response(status=204)


class SyncClassToGoogle(views.APIView):
    def post(self, request, class_id):
        try:
            cls = ClassEvent.objects.get(id=class_id)
            user_creds = GoogleCredential.objects.first()
            creds = Credentials.from_authorized_user_info(user_creds.token)
            service = build('calendar', 'v3', credentials=creds)
            unispace_id = get_or_create_unispace_calendar(service, user_creds)

            now = datetime.datetime.now()
            days_until = (DAY_MAP.get(cls.event_id.day, 0) - now.weekday() + 7) % 7
            if days_until == 0 and cls.event_id.start_time < now.time(): days_until = 7
            target_date = now.date() + datetime.timedelta(days=days_until)

            start_iso = datetime.datetime.combine(target_date, cls.event_id.start_time).strftime('%Y-%m-%dT%H:%M:%SZ')
            end_iso = datetime.datetime.combine(target_date, cls.event_id.end_time).strftime('%Y-%m-%dT%H:%M:%SZ')

            g_event = {
                'summary': f"🎓 {cls.subject_id.name}",
                'location': f"Room {cls.room_id.room_number}",
                'description': f"Instructor: {cls.instructor_id.first_name}",
                'start': {'dateTime': start_iso, 'timeZone': 'UTC'},
                'end': {'dateTime': end_iso, 'timeZone': 'UTC'},
                'colorId': '9',
            }
            service.events().insert(calendarId=unispace_id, body=g_event).execute()
            return response.Response({"status": "Synced to Google!"})
        except Exception as e:
            return response.Response({"error": str(e)}, status=400)

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
    queryset =ClassEvent.objects.all()
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


class StudyYearViewSet(viewsets.ModelViewSet):
    queryset = StudyYear.objects.all()
    serializer_class = StudyYearSerializer
    permission_classes = [permissions.AllowAny]


class TVLoungeViewSet(viewsets.ModelViewSet):
    queryset = TVLounge.objects.all()
    serializer_class = TVLoungeSerializer
    permission_classes = [permissions.AllowAny]


class TVBookingViewSet(viewsets.ModelViewSet):
    queryset = TVBooking.objects.all()
    serializer_class = TVBookingSerializer
    permission_classes = [permissions.AllowAny]
