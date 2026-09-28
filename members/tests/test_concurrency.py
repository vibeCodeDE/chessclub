import threading
import time
from unittest.mock import patch

from django.db import connections
from django.test import Client, TransactionTestCase

from core.models import AuditLog
from members import views
from members.models import ChangeRequest

from .test_selfservice import make_member, make_user


class ConcurrentDecisionTests(TransactionTestCase):
    """Zwei Admins entscheiden gleichzeitig – nur eine Entscheidung darf zählen."""

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
        self.url = f"/mitglieder/wuensche/{self.change_request.pk}/freigabe/"

    def test_two_admins_approving_at_once_decide_only_once(self):
        in_view = threading.Event()
        release = threading.Event()
        original_clean = views.clean_member_value

        def slow_clean(feld, value):
            in_view.set()
            release.wait(timeout=10)
            return original_clean(feld, value)

        statuses = []

        def approve():
            client = Client()
            client.login(username="vorstand", password="x")
            try:
                statuses.append(client.post(self.url).status_code)
            finally:
                connections.close_all()

        second = None
        with patch.object(views, "clean_member_value", slow_clean):
            first = threading.Thread(target=approve)
            first.start()
            try:
                self.assertTrue(
                    in_view.wait(timeout=10), "erster Antrag kam nicht in die View"
                )
                second = threading.Thread(target=approve)
                second.start()
                # Zweiter Antrag soll auf die Zeilensperre treffen,
                # bevor der erste freigibt.
                time.sleep(0.5)
            finally:
                release.set()
                first.join(timeout=30)
                if second is not None:
                    second.join(timeout=30)

        self.assertFalse(first.is_alive())
        self.assertCountEqual(statuses, [302, 404])
        self.member.refresh_from_db()
        self.assertEqual(self.member.telefon, "030 999999")
        self.change_request.refresh_from_db()
        self.assertEqual(
            self.change_request.status, ChangeRequest.Status.FREIGEGEBEN
        )
        # Ein Eintrag für die Stammdaten-Änderung, einer für die Freigabe.
        self.assertEqual(
            AuditLog.objects.filter(member=self.member).count(), 2
        )
