from django.urls import re_path
from django.views.generic import TemplateView
from django.urls import path, include
from camphub import views
from rest_framework.routers import DefaultRouter
from django.contrib import admin

router = DefaultRouter()
router.register(r'schedule-entries', views.EventViewSet)
router.register(r'contacts', views.ContactViewSet)
router.register(r'contact-entries', views.ContactViewSet, basename='contact-entries')
router.register(r'schedule', views.ScheduleViewSet, basename='schedule')
router.register(r'bubble-events', views.BubbleEventViewSet)
router.register(r'gym-events', views.GymEventViewSet)
router.register(r'meal-times', views.MealTimeViewSet)
router.register(r'class-events', views.ClassEventViewSet)

router.register(r'subject-entries', views.SubjectViewSet)
router.register(r'instructor-entries', views.InstructorViewSet)
router.register(r'cohort-entries', views.CohortViewSet)
router.register(r'room-entries', views.RoomViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('api/', include(router.urls)),
]

urlpatterns += [re_path(r'^.*', TemplateView.as_view(template_name='index.html'))]