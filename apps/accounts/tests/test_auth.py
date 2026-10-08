from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class AuthenticationTests(TestCase):
    def setUp(self):
        self.agent = User.objects.create_user(
            username="claire", password="Mot-de-passe-test-1", first_name="Claire", last_name="Martin"
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('dashboard:home')}")

    def test_agent_can_log_in(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "claire", "password": "Mot-de-passe-test-1"}
        )
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_wrong_password_is_rejected(self):
        response = self.client.post(reverse("accounts:login"), {"username": "claire", "password": "faux"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_requires_post(self):
        self.client.force_login(self.agent)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_str_uses_full_name(self):
        self.assertEqual(str(self.agent), "Claire Martin")
