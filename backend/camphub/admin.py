from django.contrib import admin
from .models import (
    Room, Cohort, StudyYear, Subject, Event, GymEvent, ClassEvent,
    MealTime, Instructor, Contact, TVBooking, Reminder, BubbleEvent, APILog, APISQLLog
)

admin.site.register(Room)
admin.site.register(Cohort)
admin.site.register(StudyYear)
admin.site.register(Subject)
admin.site.register(Event)
admin.site.register(GymEvent)
admin.site.register(ClassEvent)
admin.site.register(MealTime)
admin.site.register(Instructor)
admin.site.register(Contact)
admin.site.register(TVBooking)
admin.site.register(Reminder)
admin.site.register(BubbleEvent)


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


