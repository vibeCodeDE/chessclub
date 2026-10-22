from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase

from core.models import AuditLog
from core.roles import ADMIN_GROUP
from members.models import ChangeRequest, Member


def make_user(username, group_name=None):
    user = User.objects.create_user(username, password="x")
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


def make_member(user=None, **kwargs):
    defaults = {
        "vorname": "Anna",
        "nachname": "Meier",
        "eintrittsdatum": date(2020, 1, 15),
        "telefon": "030 123456",
        "email": "anna@example.org",
        "user": user,
    }
    defaults.update(kwargs)
    return Member.objects.create(**defaults)


def submit_change(client, feld, wunschwert):
    return client.post("/profil/", {"feld": feld, "wunschwert": wunschwert})


class ProfilSelbstbedienungTests(TestCase):
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        self.user = make_user("p1", "mitglied")
        self.client.login(username="p1", password="x")

    def test_profil_requires_login(self):
        self.client.logout()
        response = self.client.get("/profil/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_profil_shows_own_data(self):
        make_member(user=self.user)

        response = self.client.get("/profil/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meier")
        self.assertContains(response, "anna@example.org")
        self.assertContains(response, "030 123456")

    def test_profil_zeigt_verbandsdaten_und_dwz(self):
        make_member(
            user=self.user,
            dwz=1850,
            dwz_index=45,
            zps_nummer="C0101-042",
            fide_id=1234567,
            pkz="998877",
        )
        response = self.client.get("/profil/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1850-45")
        self.assertContains(response, "C0101-042")
        self.assertContains(response, "1234567")
        self.assertContains(response, "998877")

    def test_negativ_profil_ohne_dwz_zeigt_fallback(self):
        make_member(user=self.user, dwz=None)
        response = self.client.get("/profil/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "keine DWZ")

    def test_profil_zeigt_dsgvo_links_und_stat_cards(self):
        member = make_member(user=self.user)
        response = self.client.get("/profil/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"/mitglieder/{member.pk}/auskunft.pdf")
        self.assertContains(response, f"/mitglieder/{member.pk}/auskunft/")
        self.assertContains(response, "Mitgliedsstatus")
        self.assertContains(response, "Wertungszahl (DWZ)")

    def test_profil_without_linked_member_shows_hint(self):
        response = self.client.get("/profil/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "kein Mitgliedsprofil")

    def test_profil_zeigt_zwei_faktor_fuer_admin(self):
        self.user.groups.add(self.admin_group)
        response = self.client.get("/profil/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Zwei-Faktor-Authentifizierung (2FA)")
        self.assertContains(response, "/anmelden/zwei-faktor/neu/")

    def test_negativ_profil_ohne_admin_und_ohne_geraet_zeigt_kein_zwei_faktor(self):
        # Reguläres Mitglied ohne Admin-Gruppe und ohne 2FA-Gerät
        response = self.client.get("/profil/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Zwei-Faktor-Authentifizierung (2FA)")

    def test_submit_creates_request_without_changing_master_data(self):
        member = make_member(user=self.user)

        response = submit_change(self.client, "telefon", "030 999999")

        self.assertRedirects(response, "/profil/")
        request = ChangeRequest.objects.get()
        self.assertEqual(request.member, member)
        self.assertEqual(request.feld, "telefon")
        self.assertEqual(request.wunschwert, "030 999999")
        self.assertEqual(request.status, ChangeRequest.Status.EINGEREICHT)
        self.assertEqual(request.eingereicht_von, self.user)
        member.refresh_from_db()
        self.assertEqual(member.telefon, "030 123456")

    def test_submit_is_validated_against_model_field(self):
        make_member(user=self.user)

        submit_change(self.client, "email", "keine-mail")

        self.assertEqual(ChangeRequest.objects.count(), 0)

    def test_submit_unchanged_value_is_rejected(self):
        make_member(user=self.user)

        submit_change(self.client, "telefon", "030 123456")

        self.assertEqual(ChangeRequest.objects.count(), 0)

    def test_second_open_request_for_same_field_is_rejected(self):
        make_member(user=self.user)
        submit_change(self.client, "telefon", "030 999999")

        submit_change(self.client, "telefon", "030 111111")

        self.assertEqual(ChangeRequest.objects.count(), 1)

    def test_new_request_allowed_after_decision(self):
        member = make_member(user=self.user)
        ChangeRequest.objects.create(
            member=member,
            feld="telefon",
            wunschwert="030 999999",
            status=ChangeRequest.Status.ABGELEHNT,
            eingereicht_von=self.user,
        )

        response = submit_change(self.client, "telefon", "030 999999")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ChangeRequest.objects.count(), 2)

    def test_own_requests_are_listed(self):
        make_member(user=self.user)
        submit_change(self.client, "ort", "Neustadt")

        response = self.client.get("/profil/")

        self.assertContains(response, "Neustadt")
        self.assertContains(response, "Eingereicht")

    def test_only_editable_fields_are_offered(self):
        make_member(user=self.user)

        response = self.client.get("/profil/")

        content = response.content.decode()
        self.assertIn('value="telefon"', content)
        self.assertNotIn('value="status"', content)
        self.assertNotIn('value="eintrittsdatum"', content)


class ChangeRequestListAccessTests(TestCase):
    def setUp(self):
        self.member_user = make_user("p1", "mitglied")
        self.member = make_member(user=self.member_user)
        self.change_request = ChangeRequest.objects.create(
            member=self.member, feld="telefon", wunschwert="030 999999"
        )

    def test_list_requires_login(self):
        response = self.client.get("/mitglieder/wuensche/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_list_is_forbidden_for_member(self):
        self.client.login(username="p1", password="x")
        response = self.client.get("/mitglieder/wuensche/")
        self.assertEqual(response.status_code, 403)

    def test_list_is_forbidden_for_kapitaen(self):
        make_user("k1", "kapitaen")
        self.client.login(username="k1", password="x")
        response = self.client.get("/mitglieder/wuensche/")
        self.assertEqual(response.status_code, 403)

    def test_admin_nav_contains_change_requests_link(self):
        make_user("vorstand", "admin")
        self.client.login(username="vorstand", password="x")
        response = self.client.get("/dashboard/")
        self.assertContains(response, 'href="/mitglieder/wuensche/"')

    def test_list_shows_pending_request_with_current_value(self):
        make_user("vorstand", "admin")
        self.client.login(username="vorstand", password="x")

        response = self.client.get("/mitglieder/wuensche/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "030 999999")
        self.assertContains(response, "030 123456")
        self.assertContains(response, "Freigeben")


class ApprovalWorkflowTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.member_user = make_user("p1", "mitglied")
        self.member = make_member(user=self.member_user)
        self.change_request = ChangeRequest.objects.create(
            member=self.member,
            feld="telefon",
            wunschwert="030 999999",
            eingereicht_von=self.member_user,
        )
        # force_login, damit kein Login-Audit-Eintrag die Count-Assertions trübt.
        self.client.force_login(self.admin)

    def approve(self, pk=None, follow=False):
        return self.client.post(
            f"/mitglieder/wuensche/{pk or self.change_request.pk}/freigabe/",
            follow=follow,
        )

    def test_approve_overwrites_value_and_completes_request(self):
        response = self.approve()

        self.assertRedirects(response, "/mitglieder/wuensche/")
        self.member.refresh_from_db()
        self.assertEqual(self.member.telefon, "030 999999")
        self.change_request.refresh_from_db()
        self.assertEqual(self.change_request.status, ChangeRequest.Status.FREIGEGEBEN)
        self.assertEqual(self.change_request.entschieden_von, self.admin)
        self.assertIsNotNone(self.change_request.entschieden_am)

    def test_approve_leaves_other_fields_untouched(self):
        self.approve()
        self.member.refresh_from_db()
        self.assertEqual(self.member.vorname, "Anna")
        self.assertEqual(self.member.email, "anna@example.org")
        self.assertEqual(self.member.status, Member.Status.AKTIV)
        self.assertEqual(Member.objects.count(), 1)

    def test_approve_writes_audit_entry(self):
        self.approve()

        audit = AuditLog.objects.get(aktion="Änderungswunsch freigegeben")
        self.assertEqual(audit.benutzer, self.admin)
        self.assertEqual(audit.member, self.member)
        self.assertIn("030 123456", audit.text)
        self.assertIn("030 999999", audit.text)
        self.assertIn("Meier, Anna", audit.text)

    def test_approve_writes_stammdaten_audit_entry(self):
        self.approve()

        feld_eintrag = AuditLog.objects.get(aktion="Stammdaten geändert")
        self.assertEqual(feld_eintrag.benutzer, self.admin)
        self.assertEqual(feld_eintrag.member, self.member)
        self.assertEqual(feld_eintrag.feld, "telefon")
        self.assertEqual(feld_eintrag.alt_wert, "030 123456")
        self.assertEqual(feld_eintrag.neu_wert, "030 999999")

    def test_approve_is_post_only(self):
        response = self.client.get(
            f"/mitglieder/wuensche/{self.change_request.pk}/freigabe/"
        )
        self.assertEqual(response.status_code, 405)
        self.member.refresh_from_db()
        self.assertEqual(self.member.telefon, "030 123456")

    def test_approve_is_forbidden_for_member(self):
        self.client.logout()
        self.client.login(username="p1", password="x")
        response = self.approve()
        self.assertEqual(response.status_code, 403)
        self.member.refresh_from_db()
        self.assertEqual(self.member.telefon, "030 123456")

    def test_second_decision_on_same_request_returns_404(self):
        self.approve()
        response = self.approve()
        self.assertEqual(response.status_code, 404)

    def test_reject_keeps_master_data(self):
        response = self.client.post(
            f"/mitglieder/wuensche/{self.change_request.pk}/ablehnung/",
            {"kommentar": "Bitte telefonisch melden."},
        )

        self.assertRedirects(response, "/mitglieder/wuensche/")
        self.member.refresh_from_db()
        self.assertEqual(self.member.telefon, "030 123456")
        self.change_request.refresh_from_db()
        self.assertEqual(self.change_request.status, ChangeRequest.Status.ABGELEHNT)
        self.assertEqual(self.change_request.kommentar, "Bitte telefonisch melden.")
        self.assertEqual(self.change_request.entschieden_von, self.admin)

    def test_reject_writes_audit_entry(self):
        self.client.post(
            f"/mitglieder/wuensche/{self.change_request.pk}/ablehnung/",
            {"kommentar": ""},
        )
        audit = AuditLog.objects.get(member=self.member)
        self.assertEqual(audit.aktion, "Änderungswunsch abgelehnt")
        self.assertEqual(audit.benutzer, self.admin)
        self.assertEqual(audit.member, self.member)

    def test_reject_is_post_only(self):
        response = self.client.get(
            f"/mitglieder/wuensche/{self.change_request.pk}/ablehnung/"
        )
        self.assertEqual(response.status_code, 405)

    def test_failed_audit_log_rolls_back_master_data(self):
        self.client.raise_request_exception = False

        with patch(
            "core.models.AuditLog.objects.create",
            side_effect=RuntimeError("DB-Ausfall"),
        ):
            response = self.approve()

        self.assertEqual(response.status_code, 500)
        self.member.refresh_from_db()
        self.assertEqual(self.member.telefon, "030 123456")
        self.change_request.refresh_from_db()
        self.assertEqual(self.change_request.status, ChangeRequest.Status.EINGEREICHT)
        self.assertIsNone(self.change_request.entschieden_am)
        self.assertEqual(AuditLog.objects.filter(member=self.member).count(), 0)

    def test_failed_audit_log_keeps_request_open(self):
        self.client.raise_request_exception = False

        with patch(
            "core.models.AuditLog.objects.create",
            side_effect=RuntimeError("DB-Ausfall"),
        ):
            response = self.client.post(
                f"/mitglieder/wuensche/{self.change_request.pk}/ablehnung/",
                {"kommentar": "Bitte telefonisch melden."},
            )

        self.assertEqual(response.status_code, 500)
        self.change_request.refresh_from_db()
        self.assertEqual(self.change_request.status, ChangeRequest.Status.EINGEREICHT)
        self.assertEqual(self.change_request.kommentar, "")
        self.assertIsNone(self.change_request.entschieden_am)
        self.assertEqual(AuditLog.objects.filter(member=self.member).count(), 0)

    def test_nothing_happens_before_approval(self):
        self.client.get("/mitglieder/wuensche/")
        self.member.refresh_from_db()
        self.change_request.refresh_from_db()
        self.assertEqual(self.member.telefon, "030 123456")
        self.assertEqual(self.change_request.status, ChangeRequest.Status.EINGEREICHT)
        self.assertEqual(AuditLog.objects.filter(member=self.member).count(), 0)

    def test_invalid_stored_wunschwert_cannot_be_approved(self):
        self.change_request.wunschwert = "keine-mail"
        self.change_request.feld = "email"
        self.change_request.save()

        response = self.approve(follow=True)

        self.member.refresh_from_db()
        self.assertEqual(self.member.email, "anna@example.org")
        self.change_request.refresh_from_db()
        self.assertEqual(self.change_request.status, ChangeRequest.Status.EINGEREICHT)
        self.assertEqual(AuditLog.objects.filter(member=self.member).count(), 0)
        self.assertContains(response, "kann nicht übernommen werden")

    def test_approval_of_one_member_does_not_touch_others(self):
        other = make_member(vorname="Bernd", nachname="Schmidt", telefon="040 111")
        self.approve()

        other.refresh_from_db()
        self.assertEqual(other.telefon, "040 111")
