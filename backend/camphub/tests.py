from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from camphub.models import GymEvent, BubbleEvent, Event

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
