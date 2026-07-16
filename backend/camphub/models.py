from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
# Create your models here.
#  new section


class Room(models.Model):
    room_number = models.CharField(
        max_length=15, unique=True)

    def __str__(self):
        return self.room_number


class StudyYear(models.Model):
    CHOICES = [
        ('FESH', 'Fresh'),
        ('SOPH', 'Soph'),
        ('JUN', 'Jun'),
        ('SEN', 'Sen'),
    ]
    year_name = models.CharField(max_length=50, choices=CHOICES, default='SOF')

    def __str__(self):
        return self.year_name


class Subject(models.Model):
    CHOICES = [
        ('MATH', 'Math'),
        ('ENGLISH', 'English'),
        ('PHYSICS', 'Physics'),
        ('KYRGIZ', 'Kyrgiz'),
    ]
    name = models.CharField(max_length=50, choices=CHOICES)

    def __str__(self):
        return self.name


class Cohort(models.Model):
<<<<<<< HEAD
    study_year_id = models.ForeignKey(StudyYear, on_delete=models.CASCADE, null=True, blank=True, db_column='study_year_id')
    cohort_name = models.CharField(max_length=50)
    room_id = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True, db_column='room_id')
=======
    CHOICES = [
        ('CM', 'CM'),
        ('CS', 'CS'),
    ]
    study_year_id = models.ForeignKey(
        StudyYear, on_delete=models.CASCADE, null=True, blank=True, db_column='study_year_id')
    cohort_name = models.CharField(max_length=50, choices=CHOICES)

    def __str__(self):
        return self.cohort_name

>>>>>>> origin/main

class Event(models.Model):
    CHOICES = [
        ('GYM', 'Gym'),
        ('CLASS', 'Class'),
        ('BUBBLE', 'Bubble'),
        ('MEAL_TIME', 'Meal_Time'),
        ('TV', 'TV'),
    ]
    DAYS = [
        ('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'),
        ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday'), ('SUN', 'Sunday')
    ]
    day = models.CharField(max_length=3, choices=DAYS, default='MON')
    start_time = models.TimeField()
    end_time = models.TimeField()
<<<<<<< HEAD
=======

>>>>>>> origin/main
    status = models.CharField(
        max_length=50, choices=CHOICES, default='GYM')
    date = models.DateField(null=True, blank=True)


    def __str__(self):
        return f"{self.get_status_display()} ({self.get_day_display()} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"


class GymEvent(models.Model):
    CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),

    ]
    gender = models.CharField(
        max_length=50, choices=CHOICES, default='MALE')
    event_id = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, blank=True, db_column='event_id')


class Instructor(models.Model):
    STATUS_TYPE = [
        ('ON_CAMPUS', 'on_campus'),
        ('OFF_CAMPUS', 'off_campus'),
    ]

    first_name = models.CharField(max_length=15)
    last_name = models.CharField(max_length=15)
    status = models.CharField(
        max_length=20, choices=STATUS_TYPE, default='ON_CAMPUS')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class ClassEvent(models.Model):

    subject_id = models.ForeignKey(
        Subject, on_delete=models.CASCADE, null=True, blank=True, db_column='subject_id')
    instructor_id = models.ForeignKey(
        Instructor, on_delete=models.CASCADE, null=True, blank=True, db_column='instructor_id')
    cohort_id = models.ForeignKey(
        Cohort, on_delete=models.CASCADE, null=True, blank=True, db_column='cohort_id')
    event_id = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, blank=True, db_column='event_id')
    room_id = models.ForeignKey(
        Room, on_delete=models.CASCADE, null=True, blank=True, db_column='room_id')

    def clean(self):
        super().clean()

        if not self.event_id:
            return

        target_status = self.event_id.status
        target_day = self.event_id.day
        target_start = self.event_id.start_time
        target_end = self.event_id.end_time

        conflicts = ClassEvent.objects.filter(
            event_id__status=target_status,  # same type
            event_id__day=target_day,
            event_id__start_time__lt=target_end,
            event_id__end_time__gt=target_start
        )

        # prevent self-collision
        if self.pk:
            conflicts = conflicts.exclude(pk=self.pk)

        if self.room_id and conflicts.filter(room_id=self.room_id).exists():
            raise ValidationError(
                f"Conflict: Room {self.room_id} already has a {target_status} event during this time."
            )

        # Instructor Conflict
        if self.instructor_id and conflicts.filter(instructor_id=self.instructor_id).exists():
            raise ValidationError(
                f"Conflict: Instructor {self.instructor_id} is already busy with another {target_status} event."
            )

        if self.cohort_id and conflicts.filter(cohort_id=self.cohort_id).exists():
            raise ValidationError(
                f"Conflict: Cohort {self.cohort_id} is already attending a {target_status} event."
            )


class MealTime(models.Model):
    meal_name = models.CharField(max_length=50)
    event_id = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, blank=True, db_column='event_id')


class BubbleEvent(models.Model):
    name = models.CharField(max_length=100)
    event_id = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, blank=True, db_column='event_id')



# end of new section


class Contact(models.Model):
    CATEGORY_CHOICES = [
        ('MEDICAL', 'Medical'),
        ('FOOD', 'Food/Shop'),
        ('SECURITY', 'Security'),
        ('ADMIN', 'Administration'),
        ('TAXI', 'Taxi/Transport')

    ]

    LOCATION_CHOICES = [
        ('ON_CAMPUS', 'On Campus'),
        ('OFF_CAMPUS', 'Off Campus'),
    ]

    full_name = models.CharField(
        max_length=50)
    role = models.CharField(
        max_length=50)
    phone_number = models.CharField(max_length=20)
    sector = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="FOOD")

    location = models.CharField(
        max_length=20, choices=LOCATION_CHOICES, null=True, blank=True)

class TVBooking(models.Model):
    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, db_column='user_id')
    lounge_name = models.CharField(max_length=50)
    booker_name = models.CharField(max_length=100)
    event_id = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, blank=True, db_column='event_id')
    def __str__(self):
        event_str = f"{self.event_id.day} {self.event_id.start_time}" if self.event_id else "No Event"
        return f"{self.booker_name} - {self.lounge_name} ({event_str})"


class Reminder(models.Model):
    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, db_column='user_id')
    event_time_str = models.CharField(max_length=10)
    reminder_offset = models.IntegerField()
    event_id = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, blank=True, db_column='event_id')
    
    def __str__(self):
        event_str = f" ({self.event_id.day} {self.event_id.start_time})" if self.event_id else ""
        return f"Reminder {self.id} for {self.user_id}{event_str}"
