from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import User

class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpassword',
            display_name='Test User'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.display_name, 'Test User')
        self.assertEqual(user.total_xp, 0)
        self.assertEqual(user.current_level, 1)
        self.assertEqual(user.location_privacy_mode, User.PrivacyMode.BLURRED)

    def test_superuser_creation(self):
        admin = User.objects.create_superuser(
            username='adminuser',
            password='adminpassword',
            email='admin@example.com'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)


class AuthApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('auth_register')
        self.login_url = reverse('auth_login')
        self.logout_url = reverse('auth_logout')
        self.me_url = reverse('me')
        self.csrf_url = reverse('auth_csrf')

    def test_csrf_endpoint(self):
        response = self.client.get(self.csrf_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('csrfToken', response.data)
        self.assertTrue(len(response.data['csrfToken']) > 0)
        # Check that the csrftoken cookie is set
        self.assertIn('csrftoken', response.cookies)

    def test_register_success(self):
        payload = {
            'username': 'runner123',
            'email': 'runner@example.com',
            'password': 'StrongPassword123!',
            'display_name': 'Speedy Runner',
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'runner123')
        self.assertEqual(response.data['display_name'], 'Speedy Runner')
        self.assertEqual(response.data['total_xp'], 0)
        self.assertEqual(response.data['current_level'], 1)
        self.assertEqual(response.data['location_privacy_mode'], User.PrivacyMode.BLURRED)
        self.assertNotIn('password', response.data)

        # Verify session was created and user is logged in
        me_resp = self.client.get(self.me_url)
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data['username'], 'runner123')

    def test_register_duplicate_username(self):
        User.objects.create_user(username='existinguser', password='password123')
        payload = {
            'username': 'existinguser',
            'password': 'anotherPassword123',
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_register_short_password(self):
        payload = {
            'username': 'newuser',
            'password': '123',
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_login_success_with_username(self):
        user = User.objects.create_user(
            username='gravityuser',
            email='gravity@example.com',
            password='securepassword',
            display_name='Gravity Star'
        )
        response = self.client.post(self.login_url, {
            'username': 'gravityuser',
            'password': 'securepassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'gravityuser')
        self.assertEqual(response.data['display_name'], 'Gravity Star')

        # Check authenticated endpoint works with session
        me_resp = self.client.get(self.me_url)
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data['id'], user.id)

    def test_login_success_with_email(self):
        User.objects.create_user(
            username='userbyemail',
            email='loginbyemail@example.com',
            password='securepassword',
        )
        response = self.client.post(self.login_url, {
            'username': 'loginbyemail@example.com',
            'password': 'securepassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'userbyemail')

    def test_login_invalid_password(self):
        User.objects.create_user(username='validuser', password='correctpassword')
        response = self.client.post(self.login_url, {
            'username': 'validuser',
            'password': 'wrongpassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user(self):
        response = self.client.post(self.login_url, {
            'username': 'nonexistent',
            'password': 'somepassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_me_rejected(self):
        response = self.client.get(self.me_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_patch_me_profile(self):
        user = User.objects.create_user(
            username='patchuser',
            password='patchpassword',
            display_name='Initial Name',
            location_privacy_mode=User.PrivacyMode.BLURRED,
        )
        self.client.force_login(user)

        update_payload = {
            'display_name': 'Updated Name',
            'location_privacy_mode': User.PrivacyMode.EXACT,
        }
        response = self.client.patch(self.me_url, update_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Name')
        self.assertEqual(response.data['location_privacy_mode'], User.PrivacyMode.EXACT)

        user.refresh_from_db()
        self.assertEqual(user.display_name, 'Updated Name')
        self.assertEqual(user.location_privacy_mode, User.PrivacyMode.EXACT)

    def test_patch_me_unauthenticated_rejected(self):
        response = self.client.patch(self.me_url, {'display_name': 'Hacker'}, format='json')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_logout_destroys_session(self):
        user = User.objects.create_user(username='logoutuser', password='password123')
        # Login via endpoint to establish session in test client
        login_resp = self.client.post(self.login_url, {
            'username': 'logoutuser',
            'password': 'password123',
        }, format='json')
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)

        # Confirm logged in
        me_resp1 = self.client.get(self.me_url)
        self.assertEqual(me_resp1.status_code, status.HTTP_200_OK)

        # Logout
        logout_resp = self.client.post(self.logout_url)
        self.assertEqual(logout_resp.status_code, status.HTTP_200_OK)

        # Confirm session is terminated
        me_resp2 = self.client.get(self.me_url)
        self.assertIn(me_resp2.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_csrf_protection_enforcement(self):
        csrf_client = APIClient(enforce_csrf_checks=True)
        user = User.objects.create_user(username='csrfuser', password='password123')

        # 1. First get CSRF cookie
        csrf_resp = csrf_client.get(self.csrf_url)
        csrf_token = csrf_resp.data['csrfToken']
        self.assertTrue(csrf_token)

        # 2. Attempt mutation without X-CSRFToken header -> should be rejected with 403
        no_csrf_login = csrf_client.post(self.login_url, {
            'username': 'csrfuser',
            'password': 'password123',
        }, format='json')
        self.assertEqual(no_csrf_login.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Attempt mutation with valid X-CSRFToken header -> should succeed
        csrf_client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
        valid_csrf_login = csrf_client.post(self.login_url, {
            'username': 'csrfuser',
            'password': 'password123',
        }, format='json')
        self.assertEqual(valid_csrf_login.status_code, status.HTTP_200_OK)
