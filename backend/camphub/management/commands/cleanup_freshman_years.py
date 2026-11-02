from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from accounts.models import UserAccount
from camphub.models import ClassEvent, Cohort, Event, StudyYear

NON_FRESHMAN_COHORTS = {'CS', 'CM'}


class Command(BaseCommand):
    help = ("Removes the duplicate FRESH study year (and its lessons), renames the real Freshman "
            "year from FESH to FRESH, and drops unused cohorts other years shouldn't have.")

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help="Show what would change without saving.")

    def handle(self, *args, dry_run=False, **options):
        with transaction.atomic():
            self.cleanup()
            if dry_run:
                self.stdout.write(self.style.WARNING("Dry run: rolling back."))
                transaction.set_rollback(True)

    def cleanup(self):
        fesh = StudyYear.objects.filter(year_name='FESH').first()
        fresh = StudyYear.objects.filter(year_name='FRESH').first()

        if fesh and fresh:
            lessons = ClassEvent.objects.filter(cohort_id__study_year_id=fresh)
            groups = set(lessons.exclude(share_group=None).values_list('share_group', flat=True))
            events = set(lessons.values_list('event_id', flat=True))
            for ce in lessons.select_related('subject_id', 'cohort_id'):
                self.stdout.write(f"Delete lesson #{ce.id} {ce.subject_id} ({ce.cohort_id})")
            lessons.delete()

            # A shared class left with one row is no longer shared.
            for group in groups:
                rest = ClassEvent.objects.filter(share_group=group)
                if rest.count() == 1:
                    rest.update(share_group=None)
            Event.objects.filter(id__in=events, classevent__isnull=True).delete()

            for cohort in Cohort.objects.filter(study_year_id=fresh):
                self.stdout.write(f"Delete cohort #{cohort.id} FRESH {cohort.cohort_name}")
                cohort.delete()
            self.stdout.write(f"Delete study year #{fresh.id} FRESH")
            fresh.delete()

        if fesh:
            self.stdout.write(f"Rename study year #{fesh.id} FESH -> FRESH")
            fesh.year_name = 'FRESH'
            fesh.save(update_fields=['year_name'])

        freshman = StudyYear.objects.filter(year_name='FRESH')
        extras = (Cohort.objects.exclude(study_year_id__in=freshman)
                  .exclude(cohort_name__in=NON_FRESHMAN_COHORTS)
                  .annotate(lessons=Count('classevent')))
        for cohort in extras.select_related('study_year_id'):
            year = cohort.study_year_id.year_name if cohort.study_year_id else 'no year'
            users = UserAccount.objects.filter(cohort=cohort).count()
            if cohort.lessons or users:
                self.stdout.write(self.style.WARNING(
                    f"Keep cohort #{cohort.id} {year} {cohort.cohort_name}: "
                    f"{cohort.lessons} lesson(s), {users} user(s) still use it"))
                continue
            self.stdout.write(f"Delete cohort #{cohort.id} {year} {cohort.cohort_name}")
            cohort.delete()
