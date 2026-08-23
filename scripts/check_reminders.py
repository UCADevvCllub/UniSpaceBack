#!/usr/bin/env python
import os
import sys
import django

# Add backend directory to Python path
sys.path.insert(0, '/home/student/Desktop/UniSpaceBack/backend')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_system.settings')
os.environ.setdefault('USE_SQLITE', 'False')
django.setup()

from camphub.models import Reminder, Event, BubbleEvent
from accounts.models import UserAccount

user = UserAccount.objects.get(telegram_id=1658352530)
reminders = Reminder.objects.filter(user_id=user)
print(f'Total reminders for user: {reminders.count()}')

bubble_count = 0
for r in reminders:
    event = r.event_id
    if event:
        if event.status == 'BUBBLE':
            bubble_count += 1
            bubble_events = event.bubbleevent_set.all()
            sport_name = bubble_events[0].name if bubble_events else 'Unknown'
            print(f'  - BUBBLE: {sport_name} (event_id: {event.id}, day: {event.day}, time: {event.start_time})')
        else:
            print(f'  - {event.status} (event_id: {event.id}, day: {event.day}, time: {event.start_time})')

print(f'\nBubble reminders count: {bubble_count}')

# Check all bubble events in database
print('\n--- All Bubble Events in Database ---')
from camphub.models import Event, BubbleEvent
bubble_events = Event.objects.filter(status='BUBBLE')
print(f'Total BUBBLE events in database: {bubble_events.count()}')
for e in bubble_events:
    be = e.bubbleevent_set.first()
    sport_name = be.name if be else 'Unknown'
    print(f'  - {sport_name} (event_id: {e.id}, day: {e.day}, time: {e.start_time})')

# Check all meal time events in database
print('\n--- All Meal Time Events in Database ---')
from camphub.models import MealTime
meal_events = Event.objects.filter(status='MEAL_TIME')
print(f'Total MEAL_TIME events in database: {meal_events.count()}')
for e in meal_events:
    me = e.mealtime_set.first()
    meal_name = me.meal_name if me else 'Unknown'
    print(f'  - {meal_name} (event_id: {e.id}, day: {e.day}, time: {e.start_time})')

# Check all MealTime objects directly
print('\n--- All MealTime Objects in Database ---')
meal_times = MealTime.objects.all()
print(f'Total MealTime objects: {meal_times.count()}')
for mt in meal_times:
    event_str = f"event_id: {mt.event_id.id}" if mt.event_id else "no event"
    print(f'  - {mt.meal_name} ({event_str})')
