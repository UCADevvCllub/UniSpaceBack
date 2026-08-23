#!/usr/bin/env python
import os
import sys
import django

sys.path.insert(0, '/home/student/Desktop/UniSpaceBack/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_system.settings')
os.environ.setdefault('USE_SQLITE', 'False')
django.setup()

from camphub.models import Event, MealTime
from datetime import time

# Define meal times
meal_config = [
    {"name": "Breakfast", "start": "08:00", "end": "09:00"},
    {"name": "Lunch", "start": "13:00", "end": "14:00"},
    {"name": "Dinner", "start": "19:00", "end": "20:00"},
]

days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

print("Creating meal time events...")
for meal in meal_config:
    for day in days:
        existing = Event.objects.filter(
            day=day,
            start_time=time.fromisoformat(meal["start"]),
            end_time=time.fromisoformat(meal["end"]),
            status="MEAL_TIME"
        ).first()
        
        if existing:
            print(f"  - {meal['name']} on {day} already exists")
            continue
        
        event = Event.objects.create(
            day=day,
            start_time=time.fromisoformat(meal["start"]),
            end_time=time.fromisoformat(meal["end"]),
            status="MEAL_TIME"
        )
        
        MealTime.objects.create(
            meal_name=meal["name"],
            event_id=event
        )
        
        print(f"  - Created {meal['name']} on {day}")

print("\nDone! Meal time events created successfully.")
