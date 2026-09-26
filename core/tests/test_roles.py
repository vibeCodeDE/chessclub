from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import TestCase

from core.roles import role_of


class RoleTests(TestCase):
    def test_anonymous_is_gast(self):
        self.assertEqual(role_of(AnonymousUser()), "gast")

    def test_plain_user_is_mitglied(self):
        user = User.objects.create_user("u1", password="x")
        self.assertEqual(role_of(user), "mitglied")

    def test_user_in_mitglied_group_is_mitglied(self):
        group, _ = Group.objects.get_or_create(name="mitglied")
        user = User.objects.create_user("u2", password="x")
        user.groups.add(group)
        self.assertEqual(role_of(user), "mitglied")

    def test_kapitaen_beats_mitglied(self):
        k, _ = Group.objects.get_or_create(name="kapitaen")
        m, _ = Group.objects.get_or_create(name="mitglied")
        user = User.objects.create_user("u3", password="x")
        user.groups.add(k, m)
        self.assertEqual(role_of(user), "kapitaen")

    def test_admin_beats_all(self):
        a, _ = Group.objects.get_or_create(name="admin")
        k, _ = Group.objects.get_or_create(name="kapitaen")
        user = User.objects.create_user("u4", password="x")
        user.groups.add(a, k)
        self.assertEqual(role_of(user), "admin")
