from django.contrib.auth.models import Group, User
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import path

from core.roles import role_required


@role_required("admin")
def secret(request):
    return HttpResponse("geheim")


urlpatterns = [path("secret/", secret)]


@override_settings(ROOT_URLCONF="core.tests.test_access")
class RoleAccessTests(TestCase):
    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get("/secret/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)
        self.assertIn("next=/secret/", response.url)

    def test_plain_user_is_forbidden(self):
        User.objects.create_user("u1", password="x")
        self.client.login(username="u1", password="x")
        response = self.client.get("/secret/")
        self.assertEqual(response.status_code, 403)

    def test_member_is_forbidden(self):
        group, _ = Group.objects.get_or_create(name="mitglied")
        user = User.objects.create_user("u2", password="x")
        user.groups.add(group)
        self.client.login(username="u2", password="x")
        response = self.client.get("/secret/")
        self.assertEqual(response.status_code, 403)

    def test_kapitaen_is_forbidden(self):
        group, _ = Group.objects.get_or_create(name="kapitaen")
        user = User.objects.create_user("u3", password="x")
        user.groups.add(group)
        self.client.login(username="u3", password="x")
        response = self.client.get("/secret/")
        self.assertEqual(response.status_code, 403)

    def test_admin_is_allowed(self):
        group, _ = Group.objects.get_or_create(name="admin")
        user = User.objects.create_user("u4", password="x")
        user.groups.add(group)
        self.client.login(username="u4", password="x")
        response = self.client.get("/secret/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"geheim")
