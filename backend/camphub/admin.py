from django.contrib import admin
from .models import (
    Room, Cohort, StudyYear, Subject, Event, GymEvent, ClassEvent,
    MealTime, Instructor, Contact, TVBooking, TVLounge, Reminder, BubbleEvent,
    APILog, APISQLLog
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


@admin.register(TVLounge)
class TVLoungeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(TVBooking)
class TVBookingAdmin(admin.ModelAdmin):
    list_display = ('booker_name', 'lounge_id', 'event_id', 'user_id')
    list_filter = ('lounge_id',)
    search_fields = ('booker_name', 'lounge_id__name')
    autocomplete_fields = ('event_id', 'user_id', 'lounge_id')


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'event_id', 'reminder_offset')
    autocomplete_fields = ('event_id', 'user_id')


class APISQLLogInline(admin.TabularInline):
    model = APISQLLog
    extra = 0
    readonly_fields = ('sql', 'params', 'duration_ms', 'created_at')
    can_delete = False

    def get_queryset(self, request):
        return super().get_queryset(request).using('logs_db')


@admin.register(APILog)
class APILogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'method', 'endpoint', 'status_code', 'execution_time_ms')
    list_filter = ('method', 'status_code')
    search_fields = ('endpoint', 'request_body', 'response_body')
    readonly_fields = ('created_at', 'method', 'endpoint', 'status_code', 'request_body', 'response_body', 'execution_time_ms')
    inlines = [APISQLLogInline]

    def get_queryset(self, request):
        return super().get_queryset(request).using('logs_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='logs_db')

    def delete_model(self, request, obj):
        obj.delete(using='logs_db')


@admin.register(APISQLLog)
class APISQLLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'api_log', 'duration_ms', 'created_at')
    search_fields = ('sql', 'params')
    readonly_fields = ('api_log', 'sql', 'params', 'duration_ms', 'created_at')

    def get_queryset(self, request):
        return super().get_queryset(request).using('logs_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='logs_db')

    def delete_model(self, request, obj):
        obj.delete(using='logs_db')
