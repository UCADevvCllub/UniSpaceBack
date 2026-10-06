from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from camphub.models import (GymEvent, BubbleEvent, Event, ClassEvent, Cohort, StudyYear,
                            Subject, Instructor, Room)

from accounts.models import UserAccount

class EndpointFixesTestCase(TestCase):
    databases = {'default', 'logs_db'}

    def setUp(self):
        self.client = APIClient()
        self.user = UserAccount.objects.create_user(
            email='testuser@example.com',
            password='testpassword123',
            name='Test User'
        )
        self.user.is_staff = True
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_bubble_event_accepts_football(self):
        payload = {
            "name": "football",
            "event_data": {
                "day": "MON",
                "start_time": "14:00:00",
                "end_time": "16:00:00"
            }
        }
        response = self.client.post('/api/bubble-events/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BubbleEvent.objects.count(), 1)
        self.assertIn(response.data['name'].upper(), ['FOOTBALL', 'ALTAI-NARYN FOOTBALL'])

    def test_gym_event_back_to_back_and_overlap(self):
        # Slot 1: 06:00 - 08:00 (MALE)
        slot1 = {
            "gender": "MALE",
            "event_data": {
                "day": "MON",
                "start_time": "06:00:00",
                "end_time": "08:00:00"
            }
        }
        resp1 = self.client.post('/api/gym-events/', slot1, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)

        # Slot 2: 08:00 - 10:00 (MALE) - Back-to-back, touching boundary at 08:00
        slot2 = {
            "gender": "MALE",
            "event_data": {
                "day": "MON",
                "start_time": "08:00:00",
                "end_time": "10:00:00"
            }
        }
        resp2 = self.client.post('/api/gym-events/', slot2, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)

        # Slot 3: 07:00 - 09:00 (MALE) - Actual overlap with 06:00-08:00 and 08:00-10:00
        slot3 = {
            "gender": "MALE",
            "event_data": {
                "day": "MON",
                "start_time": "07:00:00",
                "end_time": "09:00:00"
            }
        }
        resp3 = self.client.post('/api/gym-events/', slot3, format='json')
        self.assertEqual(resp3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", resp3.data)

        # Slot 4: 06:00 - 08:00 (FEMALE) - Different gender, same time slot
        slot4 = {
            "gender": "FEMALE",
            "event_data": {
                "day": "MON",
                "start_time": "06:00:00",
                "end_time": "08:00:00"
            }
        }
        resp4 = self.client.post('/api/gym-events/', slot4, format='json')
        self.assertEqual(resp4.status_code, status.HTTP_201_CREATED)

    def test_gym_event_update_does_not_self_collide(self):
        slot = {
            "gender": "MALE",
            "event_data": {
                "day": "TUE",
                "start_time": "10:00:00",
                "end_time": "12:00:00"
            }
        }
        resp = self.client.post('/api/gym-events/', slot, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        event_id = resp.data['id']

        # Update the same gym event
        update_data = {
            "gender": "MALE",
            "event_data": {
                "day": "TUE",
                "start_time": "10:00:00",
                "end_time": "12:00:00"
            }
        }
        resp_update = self.client.put(f'/api/gym-events/{event_id}/', update_data, format='json')
        self.assertEqual(resp_update.status_code, status.HTTP_200_OK)


class SharedClassTestCase(TestCase):
    databases = {'default', 'logs_db'}

    def setUp(self):
        self.client = APIClient()
        admin = UserAccount.objects.create_user(email='admin@example.com', password='testpassword123', name='Admin')
        admin.is_staff = True
        admin.save()
        self.client.force_authenticate(user=admin)

        years = {name: StudyYear.objects.create(year_name=name) for name in ('FRESH', 'SOPH', 'JUN', 'SEN')}
        self.soph_cs = Cohort.objects.create(cohort_name='CS', study_year_id=years['SOPH'])
        self.soph_cm = Cohort.objects.create(cohort_name='CM', study_year_id=years['SOPH'])
        self.sen_cs = Cohort.objects.create(cohort_name='CS', study_year_id=years['SEN'])
        self.fresh_a = Cohort.objects.create(cohort_name='CS_A', study_year_id=years['FRESH'])
        self.fresh_b = Cohort.objects.create(cohort_name='CS_B', study_year_id=years['FRESH'])
        self.subject = Subject.objects.create(name='Data Structures')
        self.teacher = Instructor.objects.create(first_name='Ada', last_name='Lovelace')
        self.room = Room.objects.create(room_number='204')

    def lesson(self, cohort_ids, day='MON', start='09:00:00', end='10:30:00', **extra):
        payload = {
            'subject_id': self.subject.id, 'instructor_id': self.teacher.id, 'room_id': self.room.id,
            'cohort_ids': cohort_ids,
            'event_data': {'day': day, 'start_time': start, 'end_time': end},
            **extra,
        }
        return self.client.post('/api/class-events/', payload, format='json')

    def test_shared_class_across_years_saves_without_clash(self):
        resp = self.lesson([self.soph_cs.id, self.sen_cs.id, self.fresh_a.id, self.fresh_b.id])
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        rows = ClassEvent.objects.filter(share_group=resp.data['share_group'])
        self.assertEqual(rows.count(), 4)
        self.assertEqual(len({r.event_id_id for r in rows}), 1)

    def test_real_clash_is_still_blocked(self):
        self.assertEqual(self.lesson([self.soph_cs.id, self.sen_cs.id]).status_code, 201)
        # Same teacher, overlapping time, unrelated class
        resp = self.lesson([self.soph_cm.id], start='10:00:00', end='11:00:00')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('instructor_id', resp.data)

    def test_editing_a_lesson_does_not_move_an_unrelated_one(self):
        other_teacher = Instructor.objects.create(first_name='Alan', last_name='Turing')
        other_room = Room.objects.create(room_number='205')
        a = self.lesson([self.soph_cs.id])
        b = self.lesson([self.soph_cm.id], instructor_id=other_teacher.id, room_id=other_room.id)
        self.assertEqual((a.status_code, b.status_code), (201, 201))

        resp = self.client.patch(f"/api/class-events/{a.data['id']}/", {
            'event_data': {'day': 'FRI', 'start_time': '15:00:00', 'end_time': '16:30:00'},
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        unrelated = ClassEvent.objects.select_related('event_id').get(id=b.data['id'])
        self.assertEqual(unrelated.event_id.day, 'MON')

    def test_editing_a_shared_class_moves_and_regroups_all_years(self):
        resp = self.lesson([self.soph_cs.id, self.sen_cs.id])
        group = resp.data['share_group']
        # Drop Senior, add Freshman (CS_A + CS_B), and move the time - all in one edit
        resp = self.client.patch(f"/api/class-events/{resp.data['id']}/", {
            'cohort_ids': [self.soph_cs.id, self.fresh_a.id, self.fresh_b.id],
            'event_data': {'day': 'WED', 'start_time': '11:00:00', 'end_time': '12:00:00'},
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        rows = ClassEvent.objects.filter(share_group=group).select_related('event_id')
        self.assertEqual({r.cohort_id_id for r in rows}, {self.soph_cs.id, self.fresh_a.id, self.fresh_b.id})
        self.assertEqual({(r.event_id.day, str(r.event_id.start_time)) for r in rows}, {('WED', '11:00:00')})

    def test_online_room_can_host_overlapping_classes(self):
        online = Room.objects.create(room_number='Online')
        other_teacher = Instructor.objects.create(first_name='Grace', last_name='Hopper')
        self.assertEqual(self.lesson([self.soph_cs.id], room_id=online.id).status_code, 201)
        resp = self.lesson([self.sen_cs.id], room_id=online.id, instructor_id=other_teacher.id)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_edit_into_a_clash_is_rejected(self):
        self.lesson([self.soph_cs.id])
        other = self.lesson([self.sen_cs.id], day='TUE',
                            instructor_id=Instructor.objects.create(first_name='X', last_name='Y').id,
                            room_id=Room.objects.create(room_number='301').id)
        resp = self.client.patch(f"/api/class-events/{other.data['id']}/", {
            'room_id': self.room.id,
            'event_data': {'day': 'MON', 'start_time': '09:30:00', 'end_time': '10:00:00'},
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deleting_a_shared_class_removes_every_year_and_its_event(self):
        resp = self.lesson([self.soph_cs.id, self.sen_cs.id])
        event_id = ClassEvent.objects.get(id=resp.data['id']).event_id_id
        self.assertEqual(self.client.delete(f"/api/class-events/{resp.data['id']}/").status_code, 204)
        self.assertFalse(ClassEvent.objects.filter(share_group=resp.data['share_group']).exists())
        self.assertFalse(Event.objects.filter(id=event_id).exists())

    def test_create_linked_endpoint_still_works(self):
        resp = self.client.post('/api/class-events/create-linked/', {
            'subject_id': self.subject.id, 'instructor_id': self.teacher.id, 'room_id': self.room.id,
            'cohort_ids': [self.soph_cs.id, self.soph_cm.id],
            'event_data': {'day': 'THU', 'start_time': '09:00:00', 'end_time': '10:00:00'},
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(len(resp.data), 2)
