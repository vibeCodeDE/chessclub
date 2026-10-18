from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from members.models import Member, MemberStatusChange


def make_member(**kwargs):
    defaults = {
        "vorname": "Anna",
        "nachname": "Meier",
        "eintrittsdatum": date(2020, 1, 15),
    }
    defaults.update(kwargs)
    return Member.objects.create(**defaults)


class MemberModelTests(TestCase):
    def test_new_member_defaults_to_aktiv(self):
        member = make_member()
        self.assertEqual(member.status, Member.Status.AKTIV)

    def test_str_is_nachname_comma_vorname(self):
        member = make_member()
        self.assertEqual(str(member), "Meier, Anna")

    def test_soft_delete_deactivates_instead_of_removing(self):
        member = make_member()
        member.delete()
        self.assertTrue(Member.objects.filter(pk=member.pk).exists())
        member.refresh_from_db()
        self.assertEqual(member.status, Member.Status.AUSGETRETEN)
        self.assertEqual(member.austrittsdatum, timezone.localdate())

    def test_soft_delete_is_historized(self):
        member = make_member()
        member.delete()
        change = member.status_history.get()
        self.assertEqual(change.von, Member.Status.AKTIV)
        self.assertEqual(change.nach, Member.Status.AUSGETRETEN)

    def test_no_history_on_creation(self):
        make_member()
        self.assertEqual(MemberStatusChange.objects.count(), 0)

    def test_status_change_writes_history(self):
        member = make_member()
        member.status = Member.Status.PASSIV
        member.save()
        change = member.status_history.get()
        self.assertEqual(change.von, Member.Status.AKTIV)
        self.assertEqual(change.nach, Member.Status.PASSIV)
        self.assertIsNone(change.geaendert_von)
        self.assertIsNotNone(change.zeitpunkt)

    def test_status_change_records_acting_user_when_provided(self):
        user = User.objects.filter(username="vorstand_model_test").first() or User.objects.create_user("vorstand_model_test", password="x")
        member = make_member()
        member._changed_by = user
        member.status = Member.Status.PASSIV
        member.save()
        self.assertEqual(member.status_history.get().geaendert_von, user)

    def test_non_status_save_writes_no_history(self):
        member = make_member()
        member.vorname = "Berta"
        member.save()
        self.assertEqual(MemberStatusChange.objects.count(), 0)


class MemberValidationTests(TestCase):
    def test_austritt_muss_nach_eintritt_liegen(self):
        member = Member(
            vorname="Anna",
            nachname="Meier",
            eintrittsdatum=date(2020, 1, 15),
            austrittsdatum=date(2019, 1, 1),
            status=Member.Status.AUSGETRETEN,
        )
        with self.assertRaises(ValidationError):
            member.full_clean()

    def test_status_ausgetreten_requires_austrittsdatum(self):
        member = Member(
            vorname="Anna",
            nachname="Meier",
            eintrittsdatum=date(2020, 1, 15),
            status=Member.Status.AUSGETRETEN,
        )
        with self.assertRaises(ValidationError):
            member.full_clean()

    def test_status_aktiv_rejects_austrittsdatum(self):
        member = Member(
            vorname="Anna",
            nachname="Meier",
            eintrittsdatum=date(2020, 1, 15),
            austrittsdatum=date(2024, 6, 1),
            status=Member.Status.AKTIV,
        )
        with self.assertRaises(ValidationError):
            member.full_clean()
