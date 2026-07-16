from asgiref.sync import sync_to_async
from django.conf import settings
from accounts.models import UserAccount
from camphub.models import (
    Cohort, Subject, ClassEvent, GymEvent, Event,
    Instructor, Contact, TVBooking, Reminder, StudyYear
)
from datetime import datetime, time, timedelta

day_mapping = {
    "Monday": "MON", "Tuesday": "TUE", "Wednesday": "WED", "Thursday": "THU",
    "Friday": "FRI", "Saturday": "SAT", "Sunday": "SUN",
    "MON": "MON", "TUE": "TUE", "WED": "WED", "THU": "THU", "FRI": "FRI", "SAT": "SAT", "SUN": "SUN"
}

day_reverse = {
    "MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday",
    "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"
}

# Compatibility wrappers to mimic SQLAlchemy model objects


class LessonWrapper:
    def __init__(self, entry):
        self.id = entry.id
        # ClassEvent fields are now accessed via FK relations
        self.academic_level = entry.cohort_id.cohort_name if entry.cohort_id else ""
        self.day_of_week = day_reverse.get(entry.event_id.day, entry.event_id.day) if entry.event_id else ""
        self.time_str = entry.event_id.start_time.strftime("%H:%M") if entry.event_id and entry.event_id.start_time else "09:00"
        self.subject_name = entry.subject_id.name.title() if entry.subject_id else ""


class GymSlotWrapper:
    def __init__(self, entry):
        self.id = entry.id
        # GymEvent time/day fields are now on the related Event
        self.day_of_week = day_reverse.get(entry.event_id.day, entry.event_id.day) if entry.event_id else ""
        self.start_time_str = entry.event_id.start_time.strftime("%H:%M") if entry.event_id and entry.event_id.start_time else ""
        self.end_time_str = entry.event_id.end_time.strftime("%H:%M") if entry.event_id and entry.event_id.end_time else ""
        self.session_type = entry.gender.title() if entry.gender else ""


class BubbleWrapper:
    def __init__(self, entry):
        self.id = entry.id
        self.day_of_week = day_reverse.get(entry.day, entry.day)
        self.sport_name = entry.status.replace(
            "_", " ").title() if entry.status else ""
        self.time_str = f"{entry.start_time.strftime('%H:%M')} – {entry.end_time.strftime('%H:%M')}"


class ContactWrapper:
    def __init__(self, entry):
        self.id = entry.id
        self.category = "On Campus" if entry.location == "ON_CAMPUS" else "Off Campus"
        self.name = entry.full_name
        self.phone = str(entry.phone_number)
        self.details = entry.role


class TVBookingWrapper:
    def __init__(self, entry):
        self.id = entry.id
        # FK field is named user_id, so the related object is entry.user_id
        self.user_id = entry.user_id.telegram_id if entry.user_id else None
        self.lounge_name = entry.lounge_name
        self.booker_name = entry.booker_name
        self.booking_date = entry.event_id.date.strftime("%d.%m") if (entry.event_id and entry.event_id.date) else ""
        self.booking_time = entry.event_id.start_time.strftime("%H:%M") if (entry.event_id and entry.event_id.start_time) else ""


class ReminderWrapper:
    def __init__(self, entry):
        self.id = entry.id
        # FK field is named user_id, so the related object is entry.user_id
        self.telegram_user_id = entry.user_id.telegram_id if entry.user_id else None
        self.reminder_offset = entry.reminder_offset
        self.event_time_str = entry.event_time_str
        self.event_id = entry.event_id.id if entry.event_id else None
        
        event = entry.event_id
        if event:
            # 1. Resolve reminder_type
            if event.status == 'CLASS':
                self.reminder_type = "lesson"
            elif event.status == 'GYM':
                self.reminder_type = "gym"
            elif event.status == 'BUBBLE':
                self.reminder_type = "bubble"
            elif event.status == 'TV':
                self.reminder_type = "tv"
            else:
                self.reminder_type = "unknown"
                
            # 2. Resolve day name (or date for TV lounge bookings)
            if event.status == 'TV' and event.date:
                self.day = event.date.strftime("%d.%m")
            else:
                self.day = day_reverse.get(event.day, event.day)
                
            # 3. Resolve subject_name dynamically based on the event status
            if event.status == 'CLASS':
                class_events = list(event.classevent_set.all())
                class_event = class_events[0] if class_events else None
                self.subject_name = class_event.subject_id.name.title() if class_event and class_event.subject_id else "Unknown"
            elif event.status == 'GYM':
                self.subject_name = "Gym Session"
            elif event.status == 'BUBBLE':
                self.subject_name = "Bubble Sports"
            elif event.status == 'TV':
                tv_bookings = list(event.tvbooking_set.all())
                tv_booking = tv_bookings[0] if tv_bookings else None
                self.subject_name = tv_booking.lounge_name if tv_booking else "TV Lounge"
            else:
                self.subject_name = "Unknown Event"
        else:
            self.reminder_type = "unknown"
            self.day = ""
            self.subject_name = "Unknown Event"


def parse_time_str(t_str):
    t_str = t_str.strip()
    dt = datetime.strptime(t_str, "%H:%M")
    return time(dt.hour, dt.minute)

# --- User CRUD ---


@sync_to_async
def get_user(telegram_id: int):
    try:
        u = UserAccount.objects.select_related(
            'cohort').get(telegram_id=telegram_id)
        u.academic_level = u.cohort.cohort_name if u.cohort else None
        return u
    except UserAccount.DoesNotExist:
        return None


@sync_to_async
def create_user(telegram_id: int, name: str = None, gender: str = None, cohort_name: str = None):
    email = f"tg_{telegram_id}@unispace.com"
    cohort = None
    if cohort_name:
        study_year, _ = StudyYear.objects.get_or_create(year_name="2025-2026")
        cohort, _ = Cohort.objects.get_or_create(cohort_name=cohort_name, defaults={'study_year_id': study_year})
    u = UserAccount.objects.create(
        email=email,
        name=name or "Student",
        telegram_id=telegram_id,
        gender=gender.upper() if gender else None,
        cohort=cohort
    )
    u.academic_level = cohort_name
    return u


@sync_to_async
def update_user_level(telegram_id: int, level: str):
    try:
        study_year, _ = StudyYear.objects.get_or_create(year_name="2025-2026")
        cohort, _ = Cohort.objects.get_or_create(cohort_name=level, defaults={'study_year_id': study_year})
        u = UserAccount.objects.get(telegram_id=telegram_id)
        u.cohort = cohort
        u.save()
        u.academic_level = level
        return u
    except UserAccount.DoesNotExist:
        return None


@sync_to_async
def update_user_gender(telegram_id: int, gender: str):
    try:
        u = UserAccount.objects.get(telegram_id=telegram_id)
        u.gender = gender.upper()
        u.save()
        return u
    except UserAccount.DoesNotExist:
        return None

# --- Lessons CRUD (ClassEvent + Event) ---
@sync_to_async
def get_lessons_for_day(level: str, day: str):
    day_code = day_mapping.get(day, day)
    entries = ClassEvent.objects.filter(
        cohort_id__cohort_name=level,
        event_id__day=day_code,
    ).select_related('cohort_id', 'subject_id', 'event_id').order_by('event_id__start_time')
    return [LessonWrapper(e) for e in entries]


@sync_to_async
def get_weekly_lessons(level: str):
    entries = ClassEvent.objects.filter(
        cohort_id__cohort_name=level,
    ).select_related('cohort_id', 'subject_id', 'event_id').order_by('event_id__day', 'event_id__start_time')
    return [LessonWrapper(e) for e in entries]


@sync_to_async
def add_lesson(level: str, day: str, time_str: str, subject_name: str):
    study_year, _ = StudyYear.objects.get_or_create(year_name="2025-2026")
    cohort, _ = Cohort.objects.get_or_create(study_year_id=study_year, cohort_name=level)
    subject, _ = Subject.objects.get_or_create(name=subject_name.title()[:50])
    instructor, _ = Instructor.objects.get_or_create(
        first_name="TBD", last_name="TBD",
        defaults={"status": "ON_CAMPUS"}
    )
    day_code = day_mapping.get(day, "MON")
    start_time = parse_time_str(time_str)
    start_dt = datetime.combine(datetime.today(), start_time)
    end_time = (start_dt + timedelta(hours=1, minutes=30)).time()

    # Create the parent Event first, then link ClassEvent to it
    event, _ = Event.objects.get_or_create(
        day=day_code,
        start_time=start_time,
        end_time=end_time,
        defaults={"status": "CLASS"}
    )
    entry, _ = ClassEvent.objects.get_or_create(
        cohort_id=cohort,
        subject_id=subject,
        instructor_id=instructor,
        event_id=event,
    )
    return LessonWrapper(entry)


@sync_to_async
def remove_lesson(lesson_id: int):
    ClassEvent.objects.filter(id=lesson_id).delete()

# --- Gym Slots CRUD (GymEvent + Event) ---

@sync_to_async
def get_gym_slots_for_day(day: str):
    day_code = day_mapping.get(day, day)
    entries = GymEvent.objects.filter(
        event_id__day=day_code,
    ).select_related('event_id').order_by('event_id__start_time')
    return [GymSlotWrapper(e) for e in entries]


@sync_to_async
def get_all_gym_slots():
    entries = GymEvent.objects.all().select_related('event_id').order_by('event_id__day', 'event_id__start_time')
    return [GymSlotWrapper(e) for e in entries]


@sync_to_async
def add_gym_slot(day: str, start_str: str, end_str: str, session_type: str = "MALE"):
    day_code = day_mapping.get(day, "MON")
    start_time = parse_time_str(start_str)
    end_time = parse_time_str(end_str)

    # Create the parent Event first, then link GymEvent to it
    event = Event.objects.create(
        day=day_code,
        start_time=start_time,
        end_time=end_time,
        status="GYM"
    )
    entry = GymEvent.objects.create(
        event_id=event,
        gender=session_type.upper()
    )
    return entry

# --- Bubble Sports CRUD (Event with status=BUBBLE) ---

@sync_to_async
def get_bubble_sports_for_day(day: str):
    day_code = day_mapping.get(day, day)
    entries = Event.objects.filter(
        day=day_code,
        status="BUBBLE",
    ).order_by('start_time')
    return [BubbleWrapper(e) for e in entries]


@sync_to_async
def get_all_bubble_sports():
    entries = Event.objects.filter(
        status="BUBBLE",
    ).order_by('day', 'start_time')
    return [BubbleWrapper(e) for e in entries]


@sync_to_async
def add_bubble_sport(day: str, sport: str, time_range_str: str):
    import re
    day_code = day_mapping.get(day, "MON")
    parts = re.split(r'[–-]', time_range_str)
    start_time = parse_time_str(parts[0].strip())
    end_time = parse_time_str(parts[1].strip()) if len(parts) > 1 else start_time
    entry = Event.objects.create(
        day=day_code,
        start_time=start_time,
        end_time=end_time,
        status="BUBBLE"
    )
    return entry

# --- Contacts CRUD ---


@sync_to_async
def get_contacts_by_category(category: str):
    loc = "ON_CAMPUS" if category == "On Campus" else "OFF_CAMPUS"
    entries = Contact.objects.filter(location=loc)
    return [ContactWrapper(e) for e in entries]

# --- TV Bookings CRUD ---


@sync_to_async
def get_tv_bookings(user_id: int):
    # FK field named user_id → lookup is user_id__telegram_id
    entries = TVBooking.objects.filter(user_id__telegram_id=user_id).select_related('user_id', 'event_id')
    return [TVBookingWrapper(e) for e in entries]


@sync_to_async
def get_tv_booking_by_id(booking_id: int):
    try:
        b = TVBooking.objects.select_related('user_id', 'event_id').get(id=booking_id)
        return TVBookingWrapper(b)
    except TVBooking.DoesNotExist:
        return None


@sync_to_async
def add_tv_booking(user_id: int, lounge_name: str, booker_name: str, booking_date: str, booking_time: str):
    u = UserAccount.objects.get(telegram_id=user_id)
    try:
        parsed_date = datetime.strptime(booking_date, "%d.%m").date().replace(year=datetime.now().year)
        day_of_week = parsed_date.strftime("%a").upper()
    except ValueError:
        parsed_date = None
        day_of_week = "MON"
        
    start_time = parse_time_str(booking_time)
    start_dt = datetime.combine(datetime.today(), start_time)
    end_time = (start_dt + timedelta(hours=2)).time()
    
    event = Event.objects.create(
        day=day_of_week,
        start_time=start_time,
        end_time=end_time,
        status="TV",
        date=parsed_date
    )
    
    b = TVBooking.objects.create(
        user_id=u,
        lounge_name=lounge_name,
        booker_name=booker_name,
        event_id=event
    )
    return TVBookingWrapper(b)


@sync_to_async
def update_tv_booking(booking_id: int, lounge_name: str, booker_name: str, booking_date: str, booking_time: str):
    try:
        b = TVBooking.objects.select_related('event_id').get(id=booking_id)
        b.lounge_name = lounge_name
        b.booker_name = booker_name
        
        try:
            parsed_date = datetime.strptime(booking_date, "%d.%m").date().replace(year=datetime.now().year)
            day_of_week = parsed_date.strftime("%a").upper()
        except ValueError:
            parsed_date = None
            day_of_week = "MON"
            
        start_time = parse_time_str(booking_time)
        start_dt = datetime.combine(datetime.today(), start_time)
        end_time = (start_dt + timedelta(hours=2)).time()
        
        if b.event_id:
            event = b.event_id
            event.day = day_of_week
            event.start_time = start_time
            event.end_time = end_time
            event.date = parsed_date
            event.save()
        else:
            event = Event.objects.create(
                day=day_of_week,
                start_time=start_time,
                end_time=end_time,
                status="TV",
                date=parsed_date
            )
            b.event_id = event
            
        b.save()
        return TVBookingWrapper(b)
    except TVBooking.DoesNotExist:
        return None


@sync_to_async
def delete_tv_booking(booking_id: int):
    try:
        b = TVBooking.objects.get(id=booking_id)
        if b.event_id:
            b.event_id.delete()
        b.delete()
    except TVBooking.DoesNotExist:
        pass

# --- Reminders CRUD ---


@sync_to_async
def get_user_reminders(user_id: int):
    # FK field named user_id → lookup is user_id__telegram_id
    entries = Reminder.objects.filter(user_id__telegram_id=user_id).select_related(
        'user_id', 'event_id'
    ).prefetch_related(
        'event_id__classevent_set__subject_id',
        'event_id__tvbooking_set'
    )
    return [ReminderWrapper(e) for e in entries]


@sync_to_async
def get_all_reminders():
    entries = Reminder.objects.all().select_related(
        'user_id', 'event_id'
    ).prefetch_related(
        'event_id__classevent_set__subject_id',
        'event_id__tvbooking_set'
    )
    return [ReminderWrapper(e) for e in entries]


@sync_to_async
def add_reminder(user_id: int, r_type: str, subject: str, day: str, time_str: str, offset: int):
    u = UserAccount.objects.get(telegram_id=user_id)
    day_code = day_mapping.get(day, day)
    start_time = parse_time_str(time_str)
    
    event = None
    if r_type == "tv":
        try:
            parsed_date = datetime.strptime(day, "%d.%m").date().replace(year=datetime.now().year)
            event = Event.objects.filter(status="TV", start_time=start_time, date=parsed_date).first()
        except ValueError:
            pass
    else:
        event_status = "CLASS"
        if r_type == "gym":
            event_status = "GYM"
        elif r_type == "bubble":
            event_status = "BUBBLE"
        event = Event.objects.filter(day=day_code, start_time=start_time, status=event_status).first()
        
    if event:
        Reminder.objects.filter(user_id=u, event_id=event).delete()
        r = Reminder.objects.create(
            user_id=u,
            event_time_str=time_str,
            reminder_offset=offset,
            event_id=event
        )
        return ReminderWrapper(r)
    return None


@sync_to_async
def delete_reminder(user_id: int, r_type: str, subject: str, day: str, time_str: str):
    u = UserAccount.objects.get(telegram_id=user_id)
    day_code = day_mapping.get(day, day)
    start_time = parse_time_str(time_str)
    
    event = None
    if r_type == "tv":
        try:
            parsed_date = datetime.strptime(day, "%d.%m").date().replace(year=datetime.now().year)
            event = Event.objects.filter(status="TV", start_time=start_time, date=parsed_date).first()
        except ValueError:
            pass
    else:
        event_status = "CLASS"
        if r_type == "gym":
            event_status = "GYM"
        elif r_type == "bubble":
            event_status = "BUBBLE"
        event = Event.objects.filter(day=day_code, start_time=start_time, status=event_status).first()
        
    if event:
        Reminder.objects.filter(user_id=u, event_id=event).delete()

@sync_to_async
def add_all_lessons_reminders(user_id: int, level: str, offset: int):
    u = UserAccount.objects.get(telegram_id=user_id)
    class_events = ClassEvent.objects.filter(cohort_id__cohort_name=level).select_related('event_id')
    
    reminders_created = 0
    for ce in class_events:
        if ce.event_id:
            Reminder.objects.filter(user_id=u, event_id=ce.event_id).delete()
            time_str = ce.event_id.start_time.strftime("%H:%M")
            Reminder.objects.create(
                user_id=u,
                event_time_str=time_str,
                reminder_offset=offset,
                event_id=ce.event_id
            )
            reminders_created += 1
    return reminders_created

@sync_to_async
def delete_all_lessons_reminders(user_id: int, level: str):
    u = UserAccount.objects.get(telegram_id=user_id)
    class_events = ClassEvent.objects.filter(cohort_id__cohort_name=level).select_related('event_id')
    event_ids = [ce.event_id.id for ce in class_events if ce.event_id]
    
    deleted_count, _ = Reminder.objects.filter(user_id=u, event_id_id__in=event_ids).delete()
    return deleted_count
