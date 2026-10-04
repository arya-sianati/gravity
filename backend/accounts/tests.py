from django.test import TestCase
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
