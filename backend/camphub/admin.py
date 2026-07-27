from django.contrib import admin
from .models import (
    Room, Cohort, StudyYear, Subject, Event, GymEvent, ClassEvent,
    MealTime, Instructor, Contact, TVBooking, Reminder, BubbleEvent
)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number',)
    search_fields = ('room_number',)
    ordering = ('room_number',)


@admin.register(StudyYear)
class StudyYearAdmin(admin.ModelAdmin):
    list_display = ('year_name',)
    list_filter = ('year_name',)
    search_fields = ('year_name',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ('cohort_name', 'study_year_id')
    list_filter = ('cohort_name', 'study_year_id')
    search_fields = ('cohort_name',)
    autocomplete_fields = ('study_year_id',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('status', 'day', 'start_time', 'end_time', 'date')
    list_filter = ('status', 'day')
    search_fields = ('status', 'day')
    date_hierarchy = 'date'
    ordering = ('day', 'start_time')


@admin.register(GymEvent)
class GymEventAdmin(admin.ModelAdmin):
    list_display = ('gender', 'event_id')
    list_filter = ('gender',)
    autocomplete_fields = ('event_id',)


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'status')
    list_filter = ('status',)
    search_fields = ('first_name', 'last_name')
    ordering = ('last_name', 'first_name')


@admin.register(ClassEvent)
class ClassEventAdmin(admin.ModelAdmin):
    list_display = ('subject_id', 'instructor_id', 'cohort_id', 'room_id', 'event_id')
    list_filter = ('cohort_id', 'room_id')
    autocomplete_fields = ('subject_id', 'instructor_id', 'cohort_id', 'event_id', 'room_id')


@admin.register(MealTime)
class MealTimeAdmin(admin.ModelAdmin):
    list_display = ('meal_name', 'event_id')
    search_fields = ('meal_name',)
    autocomplete_fields = ('event_id',)


@admin.register(BubbleEvent)
class BubbleEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_id')
    search_fields = ('name',)
    autocomplete_fields = ('event_id',)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'role', 'sector', 'location', 'phone_number')
    list_filter = ('sector', 'location')
    search_fields = ('full_name', 'role', 'phone_number')


@admin.register(TVBooking)
class TVBookingAdmin(admin.ModelAdmin):
    list_display = ('booker_name', 'lounge_name', 'event_id', 'user_id')
    list_filter = ('lounge_name',)
    search_fields = ('booker_name', 'lounge_name')
    autocomplete_fields = ('event_id', 'user_id')


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'event_id', 'reminder_offset')
    autocomplete_fields = ('event_id', 'user_id')
