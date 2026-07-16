from django.contrib import admin
from .models import (
    Room, Cohort, StudyYear, Subject, Event, GymEvent, ClassEvent,
    MealTime, Instructor, Contact, TVBooking, Reminder, BubbleEvent
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
