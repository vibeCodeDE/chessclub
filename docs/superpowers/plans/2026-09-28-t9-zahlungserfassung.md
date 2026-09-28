# T9: SEPA-Mandate + Zahlungserfassung — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Der Vorstand bucht Beitragszahlungen von Hand (SEPA-Einzug / Überweisung / Bar), sieht je Beitragsposten den offenen Betrag und hebt Fehlbuchungen per Storno auf.

**Architecture:** Zwei neue Modelle in `dues` (`SepaMandate`, `Payment`), die per `PROTECT` an `Member` bzw. `FeePost` hängen. Die gesamte Regelbasis (offener Betrag, Bezahlt-Status, Mandatprüfung) liegt in `dues/services.py` — dieselbe Quelle für Postenliste, Zahlungsliste und später T10/T11b. Views nur Admin, Buchen/Storno/Mandat-Status ausschließlich per POST, jede Buchung mit einer AuditLog-Zeile. Kein Bank-API-Call, keine IBAN.

**Tech Stack:** Django 5.2, PostgreSQL, server-seitige Templates, Plain CSS (`.table-wrap`, `.badge`, `.alert-*`, `.inline-form`), pytest + `django.test.TestCase`.

**Spec:** `docs/superpowers/specs/2026-09-28-t9-zahlungserfassung-design.md` · **PRD:** M2.3, M2.4 · **Task:** `tasks/plan.md` T9

## Global Constraints

- Deutschsprachige App: alle Felder mit `verbose_name`, `__str__` im deutschen Format (`f"{x:.2f}".replace(".", ",")`).
- Rollen: Beiträge/Zahlungen/Mandate sind **Vorstandssache** — `@role_required(ADMIN_GROUP)` (403 für `kapitaen`/`mitglied`).
- Schreibaktionen nur per POST (`@require_POST` → 405 bei GET).
- Kein Hard-Delete für Finanzdaten; Fehlbuchungen per Storno-Gegenbuchung.
- Testkonvention: `django.test.TestCase`, Modul-Helper `make_user`/`make_member`/`kategorie` pro Testdatei, Negativtests mit Docstring `"""Negativtest: …"""`, DB-Constraints via `transaction.atomic()` + `IntegrityError`.
- Nächste Migration: `dues/migrations/0004_...` (Serie `0001_initial`, `0002_seed_beitragssaetze`, `0003_feepost`).
- Kein `MinValueValidator` auf `Payment.betrag` — negative Beträge (Storno) sind erlaubt.

## File Structure

| Datei | Verantwortung |
| --- | --- |
| `dues/models.py` | `SepaMandate`, `Payment` (Datenmodell + `clean()`-Regeln) |
| `dues/services.py` | `PostenStatus`, `bezahlte_summe`, `offen`, `posten_status`, `posten_mit_status`, `hat_sepa_mandat` |
| `dues/views.py` | `zahlungsliste`, `zahlung_buchen`, `zahlung_stornieren`, `mandat_anlegen`, `mandat_status`; Postenliste liefert Status |
| `dues/urls.py` | 5 neue Routen unter `beitraege/` |
| `dues/admin.py` | `SepaMandateAdmin` (anlegbar), `PaymentAdmin` (nur lesend) |
| `dues/templates/dues/posten_liste.html` | Spalten „Bezahlt"/„Offen", Status-Badge, Button „Zahlung buchen" |
| `dues/templates/dues/zahlungen.html` | Zahlungsliste, Buchungsformular, Mandat-Abschnitt |
| `static/css/app.css` | `.badge-unbezahlt/-offen/-bezahlt/-gutschrift` |
| `core/context_processors.py` | Nav-Eintrag „Zahlungen" |
| `dues/tests/*` | Model-, Service-, View-, Admin-, Bank-API-Tests |

---

### Task 1: Modelle `SepaMandate` + `Payment` (+ Migration, Admin)

**Files:**
- Modify: `dues/models.py` (Anhänge nach `FeePost`)
- Create: `dues/migrations/0004_sepamandate_payment.py` (autogeneriert)
- Modify: `dues/admin.py`
- Test: `dues/tests/test_models.py`, `dues/tests/test_admin.py`

**Interfaces:**
- Produces: `dues.models.SepaMandate(member, referenz, datum, status, notiz)` mit `SepaMandate.Status.{AKTIV,WIDERRUFEN,BEENDET}`, `dues.models.Payment(post, betrag, art, datum, referenz, storno_von, notiz, erfasst, erfasst_von)` mit `Payment.Art.{SEPA,UEBERWEISUNG,BAR}` und `Payment.post` → `FeePost`.

- [ ] **Step 1: Failing tests in `dues/tests/test_models.py`**

```python
class SepaMandateTests(TestCase):
    def setUp(self):
        self.member = make_member(kategorie=kategorie("erwachsene"))

    def test_mandat_wird_angelegt_und_ist_standardmaessig_aktiv(self):
        mandat = SepaMandate.objects.create(member=self.member, referenz="M-2026-001")

        self.assertEqual(mandat.status, SepaMandate.Status.AKTIV)
        self.assertEqual(str(mandat), f"{self.member} · M-2026-001")

    def test_referenz_ist_eindeutig(self):
        """Negativtest: zwei Mandate mit derselben Referenz sind unmöglich."""
        SepaMandate.objects.create(member=self.member, referenz="M-2026-001")
        with self.assertRaises(IntegrityError), transaction.atomic():
            SepaMandate.objects.create(member=self.member, referenz="M-2026-001")


class PaymentValidierungTests(TestCase):
    def setUp(self):
        self.member = make_member(kategorie=kategorie("erwachsene"))
        self.post = FeePost.objects.create(
            member=self.member, jahr=2026, kategorie=self.member.beitragskategorie,
            betrag=Decimal("90.00"),
        )

    def test_sepa_zahlung_braucht_aktives_mandat(self):
        """Negativtest: SEPA ohne Mandat wird abgelehnt (Plan-Vorgabe)."""
        payment = Payment(post=self.post, betrag=Decimal("90.00"), art=Payment.Art.SEPA)

        with self.assertRaises(ValidationError) as ctx:
            payment.full_clean()

        self.assertIn("art", ctx.exception.error_dict)

    def test_sepa_mit_widerrufenem_mandat_wird_abgelehnt(self):
        """Negativtest: ein widerrufenes Mandat trägt keinen Einzug."""
        SepaMandate.objects.create(
            member=self.member, referenz="M-1", status=SepaMandate.Status.WIDERRUFEN
        )
        payment = Payment(post=self.post, betrag=Decimal("90.00"), art=Payment.Art.SEPA)

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_sepa_mit_aktivem_mandat_ist_gueltig(self):
        SepaMandate.objects.create(member=self.member, referenz="M-1")
        payment = Payment(post=self.post, betrag=Decimal("90.00"), art=Payment.Art.SEPA)

        payment.full_clean()

    def test_ueberweisung_ohne_mandat_ist_gueltig(self):
        payment = Payment(post=self.post, betrag=Decimal("90.00"), art=Payment.Art.UEBERWEISUNG)

        payment.full_clean()

    def test_betrag_null_wird_abgelehnt(self):
        """Negativtest: eine 0-€-Buchung ist keine Buchung."""
        payment = Payment(post=self.post, betrag=Decimal("0.00"), art=Payment.Art.BAR)

        with self.assertRaises(ValidationError) as ctx:
            payment.full_clean()

        self.assertIn("betrag", ctx.exception.error_dict)

    def test_storno_verweist_auf_die_originalzahlung(self):
        SepaMandate.objects.create(member=self.member, referenz="M-1")
        original = Payment.objects.create(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.SEPA
        )
        storno = Payment.objects.create(
            post=self.post, betrag=Decimal("-90.00"), art=Payment.Art.SEPA, storno_von=original
        )

        self.assertEqual(list(original.stornos.all()), [storno])
```

- [ ] **Step 2: Run — erwartet FAIL** (`ImportError: cannot import name 'SepaMandate'`)

Run: `pytest dues/tests/test_models.py -x -q`
- [ ] **Step 3: Modelle implementieren** — an `dues/models.py` anhängen:

```python
class SepaMandate(models.Model):
    """SEPA-Mandat eines Mitglieds (PRD M2.3).

    Verwaltet wird nur, was der Einzug braucht: Referenz, Datum, Status. Die
    IBAN liegt beim Verein in der Lastschriftdatei der Bank — die Software
    nimmt **keinen** Einzug vor (PRD M2.3, Entscheidung Nr. 2).
    """

    class Status(models.TextChoices):
        AKTIV = "aktiv", "Aktiv"
        WIDERRUFEN = "widerrufen", "Widerrufen"
        BEENDET = "beendet", "Beendet"

    member = models.ForeignKey(
        "members.Member",
        verbose_name="Mitglied",
        on_delete=models.PROTECT,
        related_name="sepa_mandate",
    )
    referenz = models.CharField("Referenz", max_length=50, unique=True)
    datum = models.DateField("Mandatsdatum", default=timezone.localdate)
    status = models.CharField(
        "Status", max_length=20, choices=Status.choices, default=Status.AKTIV
    )
    notiz = models.TextField("Notiz", blank=True)

    class Meta:
        ordering = ["-datum", "member__nachname"]
        verbose_name = "SEPA-Mandat"
        verbose_name_plural = "SEPA-Mandate"

    def __str__(self):
        return f"{self.member} · {self.referenz}"


class Payment(models.Model):
    """Zahlung auf einen Beitragsposten (PRD M2.4).

    Wird von Hand gebucht — Überweisung, SEPA-Einzug oder Barzahlung. Ein
    **negativer** Betrag ist eine Gegenbuchung (Storno); Zahlungen werden nie
    gelöscht, damit die Finanzhistorie nach § 147 AO nachvollziehbar bleibt.
    """

    class Art(models.TextChoices):
        SEPA = "sepa", "SEPA-Einzug"
        UEBERWEISUNG = "ueberweisung", "Überweisung"
        BAR = "bar", "Barzahlung"

    post = models.ForeignKey(
        FeePost,
        verbose_name="Beitragsposten",
        on_delete=models.PROTECT,
        related_name="zahlungen",
    )
    betrag = models.DecimalField("Betrag", max_digits=6, decimal_places=2)
    art = models.CharField("Zahlungsart", max_length=20, choices=Art.choices)
    datum = models.DateField("Zahlungsdatum", default=timezone.localdate)
    referenz = models.CharField("Referenz", max_length=100, blank=True)
    storno_von = models.ForeignKey(
        "self",
        verbose_name="Storno zu",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stornos",
    )
    notiz = models.TextField("Notiz", blank=True)
    erfasst = models.DateTimeField("Erfasst", auto_now_add=True)
    erfasst_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Erfasst von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="erfasste_zahlungen",
    )

    class Meta:
        ordering = ["-datum", "-pk"]
        verbose_name = "Zahlung"
        verbose_name_plural = "Zahlungen"

    def __str__(self):
        betrag = f"{self.betrag:.2f}".replace(".", ",")
        return f"{self.get_art_display()} {self.datum}: {betrag} €"

    def clean(self):
        super().clean()
        if self.betrag == 0:
            raise ValidationError({"betrag": "Der Betrag darf nicht 0,00 € sein."})
        if self.art == self.Art.SEPA and self.post_id:
            if not SepaMandate.objects.filter(
                member_id=self.post.member_id, status=SepaMandate.Status.AKTIV
            ).exists():
                raise ValidationError(
                    {
                        "art": "Für einen SEPA-Einzug wird ein aktives SEPA-Mandat "
                        "des Mitglieds benötigt — bitte es unter „Zahlungen“ "
                        "zuerst anlegen."
                    }
                )
```

Imports oben ergänzen: `from django.conf import settings` und `from django.utils import timezone`.

- [ ] **Step 4: Migration** — `python manage.py makemigrations dues` → `dues/migrations/0004_sepamandate_payment.py`; Dependencies müssen auf `("dues", "0003_feepost")` und `("members", "0003_member_beitragskategorie")` zeigen.
- [ ] **Step 5: Admin** — in `dues/admin.py`:

```python
@admin.register(SepaMandate)
class SepaMandateAdmin(admin.ModelAdmin):
    list_display = ("member", "referenz", "status", "datum")
    list_filter = ("status",)
    search_fields = ("member__nachname", "member__vorname", "referenz")
    readonly_fields = ("member",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Zahlungen sind Finanznachweis — nur einsehbar (PRD M2.4).

    Anlegen geht ausschließlich über die Buchungsseite, Löschen nie. Eine
    Fehlbuchung wird per Storno aufgehoben, nicht überschrieben.
    """

    list_display = ("post", "datum", "art", "betrag", "storno_von")
    list_filter = ("art", "datum")
    search_fields = ("post__member__nachname", "post__member__vorname", "referenz")
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

- [ ] **Step 6: Tests in `dues/tests/test_admin.py`** (Admin-Login, `make_user`/`create_superuser` wie dort üblich):

```python
class PaymentAdminTests(TestCase):
    def setUp(self):
        self.client.login(username="root", password="x")
        self.payment = Payment.objects.create(
            post=posten, betrag=Decimal("90.00"), art=Payment.Art.BAR
        )

    def test_payment_kann_nicht_angelegt_werden(self):
        """Negativtest: Payment ist Finanznachweis — nur über die UI buchbar."""
        response = self.client.get("/admin/dues/payment/add/")

        self.assertEqual(response.status_code, 403)

    def test_payment_kann_nicht_geloescht_werden(self):
        response = self.client.get(
            f"/admin/dues/payment/{self.payment.pk}/delete/"
        )

        self.assertEqual(response.status_code, 403)

    def test_mandat_kann_angelegt_werden(self):
        response = self.client.get("/admin/dues/sepamandate/add/")

        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 7: Run** — `pytest dues/ -q` → alle grün.
- [ ] **Step 8: Commit**

```bash
git add dues/models.py dues/migrations/dues/admin.py dues/tests/
git commit -m "T9: Modelle SepaMandate und Payment + Admin"
```

---

### Task 2: Regelbasis — offener Betrag, Status, Mandatprüfung

**Files:**
- Modify: `dues/services.py`
- Test: `dues/tests/test_services.py`

**Interfaces:**
- Consumes: `dues.models.{FeePost, Payment, SepaMandate}` (Task 1)
- Produces:
  - `PostenStatus(models.TextChoices)`: `UNBEZAHLT`, `TEILBEZAHLT`, `BEZAHLT`, `GUTSCHRIFT`
  - `bezahlte_summe(posten) -> Decimal` (Summe inkl. Stornos)
  - `offen(posten) -> Decimal` (negativ = Gutschrift)
  - `posten_status(posten) -> str` (liest `bezahlte_summe`, sonst summiert)
  - `posten_mit_status(jahr) -> list[dict]` mit den Schlüsseln `post`, `member`, `kategorie`, `jahr`, `betrag`, `bezahlt`, `offen`, `status`, `status_label`, `status_klasse`
  - `hat_sepa_mandat(member) -> bool`

- [ ] **Step 1: Failing tests in `dues/tests/test_services.py`**

```python
class OffenerBetragTests(TestCase):
    def setUp(self):
        self.member = make_member(kategorie=kategorie("erwachsene"))
        self.post = FeePost.objects.create(
            member=self.member, jahr=2026, kategorie=self.member.beitragskategorie,
            betrag=Decimal("90.00"),
        )

    def test_unbezahlter_posten_hat_den_vollen_betrag_offen(self):
        self.assertEqual(offen(self.post), Decimal("90.00"))
        self.assertEqual(posten_status(self.post), PostenStatus.UNBEZAHLT)

    def test_teilzahlung(self):
        Payment.objects.create(post=self.post, betrag=Decimal("40.00"), art=Payment.Art.BAR)

        self.assertEqual(offen(self.post), Decimal("50.00"))
        self.assertEqual(posten_status(self.post), PostenStatus.TEILBEZAHLT)

    def test_vollstaendige_zahlung_ist_bezahlt(self):
        Payment.objects.create(post=self.post, betrag=Decimal("90.00"), art=Payment.Art.BAR)

        self.assertEqual(offen(self.post), Decimal("0.00"))
        self.assertEqual(posten_status(self.post), PostenStatus.BEZAHLT)

    def test_ueberzahlung_wird_als_gutschrift_angezeigt_und_nicht_gekappt(self):
        """Die T9-Acceptance: Überzahlung bleibt sichtbar, sie wird nicht gekappt."""
        Payment.objects.create(post=self.post, betrag=Decimal("100.00"), art=Payment.Art.BAR)

        self.assertEqual(offen(self.post), Decimal("-10.00"))
        self.assertEqual(posten_status(self.post), PostenStatus.GUTSCHRIFT)

    def test_storno_stellt_den_offenen_betrag_wieder_her(self):
        original = Payment.objects.create(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.BAR
        )
        Payment.objects.create(
            post=self.post, betrag=Decimal("-90.00"), art=Payment.Art.BAR, storno_von=original
        )

        self.assertEqual(offen(self.post), Decimal("90.00"))
        self.assertEqual(posten_status(self.post), PostenStatus.UNBEZAHLT)


class PostenMitStatusTests(TestCase):
    def test_annotation_ohne_zusatzabfragen(self):
        for i in range(5):
            member = make_member(kategorie=kategorie("erwachsene"), nachname=f"Mustermann{i}")
            post = FeePost.objects.create(
                member=member, jahr=2026, kategorie=member.beitragskategorie,
                betrag=Decimal("90.00"),
            )
            Payment.objects.create(post=post, betrag=Decimal("90.00"), art=Payment.Art.BAR)

        with self.assertNumQueries(1):
            zeilen = posten_mit_status(2026)
            werte = [(z["offen"], z["status"]) for z in zeilen]

        self.assertEqual(werte, [(Decimal("0.00"), PostenStatus.BEZAHLT)] * 5)


class MandatTests(TestCase):
    def test_hat_sepa_mandat_nur_bei_aktivem_mandat(self):
        member = make_member(kategorie=kategorie("erwachsene"))
        self.assertFalse(hat_sepa_mandat(member))
        SepaMandate.objects.create(
            member=member, referenz="M-1", status=SepaMandate.Status.BEENDET
        )
        self.assertFalse(hat_sepa_mandat(member))
        SepaMandate.objects.create(
            member=member, referenz="M-2", status=SepaMandate.Status.AKTIV
        )
        self.assertTrue(hat_sepa_mandat(member))
```

- [ ] **Step 2: Run — FAIL** (`ImportError: cannot import name 'offen'`)
- [ ] **Step 3: Implementieren** — an `dues/services.py` anhängen (Imports: `from django.db.models import F, Sum, Value` + `from django.db.models.functions import Coalesce` + `from django.db import models` für `TextChoices`):

```python
class PostenStatus(models.TextChoices):
    """Ableitung aus Postenbetrag und Zahlungen — kein gespeichertes Feld."""

    UNBEZAHLT = "unbezahlt", "Unbezahlt"
    TEILBEZAHLT = "teilbezahlt", "Teilbezahlt"
    BEZAHLT = "bezahlt", "Bezahlt"
    GUTSCHRIFT = "gutschrift", "Gutschrift"


_BADGE = {
    PostenStatus.UNBEZAHLT: "badge-unbezahlt",
    PostenStatus.TEILBEZAHLT: "badge-offen",
    PostenStatus.BEZAHLT: "badge-bezahlt",
    PostenStatus.GUTSCHRIFT: "badge-gutschrift",
}

_BETRAG_TYP = models.DecimalField(max_digits=12, decimal_places=2)


def hat_sepa_mandat(member):
    return SepaMandate.objects.filter(
        member=member, status=SepaMandate.Status.AKTIV
    ).exists()


def bezahlte_summe(posten):
    """Summe aller Zahlungen inkl. Stornos (Storno = negativer Betrag)."""
    annotateiert = getattr(posten, "bezahlte_summe", None)
    if annotateiert is not None:
        return annotateiert
    return (
        Payment.objects.filter(post=posten).aggregate(s=Sum("betrag"))["s"]
        or Decimal("0.00")
    )


def offen(posten):
    """Offener Betrag; negativ = Gutschrift (Überzahlung wird nicht gekappt)."""
    return posten.betrag - bezahlte_summe(posten)


def posten_status(posten):
    summe = bezahlte_summe(posten)
    if summe > posten.betrag:
        return PostenStatus.GUTSCHRIFT
    if summe == posten.betrag:
        return PostenStatus.BEZAHLT
    if summe == 0:
        return PostenStatus.UNBEZAHLT
    return PostenStatus.TEILBEZAHLT


def posten_mit_status(jahr):
    """Posten eines Jahres mit Zahlungsstand — eine Abfrage, keine N+1.

    Liefert Dicts, damit das Template ohne weitere Logik auskommt.
    """
    posten = (
        FeePost.objects.filter(jahr=jahr)
        .select_related("member", "kategorie")
        .annotate(
            bezahlt_summe=Coalesce(
                Sum("zahlungen__betrag"), Value(Decimal("0.00")), output_field=_BETRAG_TYP
            )
        )
        .order_by("member__nachname", "member__vorname")
    )
    zeilen = []
    for post in posten:
        rest = post.betrag - post.bezahlt_summe
        status = posten_status(post)
        zeilen.append(
            {
                "post": post,
                "member": post.member,
                "kategorie": post.kategorie,
                "jahr": post.jahr,
                "betrag": post.betrag,
                "bezahlt": post.bezahlt_summe,
                "offen": rest,
                "status": status,
                "status_label": PostenStatus(status).label,
                "status_klasse": _BADGE[status],
            }
        )
    return zeilen
```

- [ ] **Step 4: Run** — `pytest dues/tests/test_services.py -q` → grün.
- [ ] **Step 5: Commit**

```bash
git add dues/services.py dues/tests/test_services.py
git commit -m "T9: Regelbasis fuer offenen Betrag und Zahlungsstatus"
```

---

### Task 3: Zahlungsliste, Buchen, Storno (UI + Views)

**Files:**
- Modify: `dues/views.py`, `dues/urls.py`, `dues/templates/dues/posten_liste.html`
- Create: `dues/templates/dues/zahlungen.html`
- Modify: `static/css/app.css`
- Test: `dues/tests/test_views.py`

**Interfaces:**
- Consumes: `posten_mit_status`, `hat_sepa_mandat` (Task 2), `Payment` (Task 1)
- Produces: Routen `dues:zahlungsliste` (GET `/beitraege/zahlungen/`), `dues:zahlung_buchen` (POST `/beitraege/zahlungen/buchen/`), `dues:zahlung_stornieren` (POST `/beitraege/zahlungen/<pk>/storno/`)

- [ ] **Step 1: Failing tests in `dues/tests/test_views.py`**

```python
ZAHLUNGEN = "/beitraege/zahlungen/"
BUCHEN = "/beitraege/zahlungen/buchen/"


def make_post(jahr=2026, betrag="90.00"):
    member = make_member(kategorie=kategorie("erwachsene"))
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=member.beitragskategorie,
        betrag=Decimal(betrag),
    )


class ZahlungslisteZugriffTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.post = make_post()

    def test_admin_darf_die_zahlungsliste_sehen(self):
        self.client.force_login(self.admin)

        self.assertEqual(self.client.get(ZAHLUNGEN).status_code, 200)

    def test_mitglied_erhaelt_403_und_keine_zahlung(self):
        """Negativtest: Mitglieder buchen nie — und es entsteht auch nichts."""
        self.client.force_login(make_user("mitglied", "mitglied"))

        response = self.client.post(
            BUCHEN,
            {"post": self.post.pk, "betrag": "90.00", "art": Payment.Art.BAR},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Payment.objects.count(), 0)

    def test_kapitaen_erhaelt_403(self):
        self.client.force_login(make_user("kapitaen", "kapitaen"))

        self.assertEqual(self.client.get(ZAHLUNGEN).status_code, 403)


class ZahlungBuchenTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.post = make_post()

    def test_barzahlung_bucht_die_zahlung(self):
        response = self.client.post(
            BUCHEN,
            {"post": self.post.pk, "betrag": "90,00", "art": Payment.Art.BAR, "referenz": "Kassenbon 7"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        zahlung = Payment.objects.get()
        self.assertEqual(zahlung.betrag, Decimal("90.00"))
        self.assertEqual(zahlung.erfasst_von, self.admin)

    def test_buchung_wird_im_audit_log_protokolliert(self):
        self.client.post(
            BUCHEN, {"post": self.post.pk, "betrag": "90.00", "art": Payment.Art.BAR}
        )

        eintrag = AuditLog.objects.get(aktion="Zahlung gebucht")
        self.assertEqual(eintrag.member, self.post.member)
        self.assertEqual(eintrag.benutzer, self.admin)

    def test_sepa_ohne_mandat_wird_abgelehnt(self):
        """Negativtest: die Plan-Vorgabe — SEPA braucht ein aktives Mandat."""
        response = self.client.post(
            BUCHEN, {"post": self.post.pk, "betrag": "90.00", "art": Payment.Art.SEPA},
            follow=True,
        )

        self.assertEqual(Payment.objects.count(), 0)
        self.assertContains(response, "SEPA-Mandat")

    def test_buchung_ist_nur_per_post_moeglich(self):
        """Negativtest: GET bucht nichts (405)."""
        response = self.client.get(BUCHEN)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Payment.objects.count(), 0)

    def test_betrag_null_wird_abgelehnt(self):
        self.client.post(
            BUCHEN, {"post": self.post.pk, "betrag": "0", "art": Payment.Art.BAR}
        )

        self.assertEqual(Payment.objects.count(), 0)

    def test_unbekannter_posten_wird_abgelehnt(self):
        self.client.post(
            BUCHEN, {"post": "99999", "betrag": "10.00", "art": Payment.Art.BAR}
        )

        self.assertEqual(Payment.objects.count(), 0)

    def test_formular_bleibt_bei_fehler_ausgefuellt(self):
        response = self.client.post(
            BUCHEN, {"post": self.post.pk, "betrag": "0", "art": Payment.Art.BAR,
                    "referenz": "Bon 42"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bon 42")


class StornoTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.post = make_post()
        self.zahlung = Payment.objects.create(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.BAR
        )

    def test_storno_bucht_eine_gegenbuchung(self):
        self.client.post(f"/beitraege/zahlungen/{self.zahlung.pk}/storno/")

        storno = Payment.objects.get(storno_von=self.zahlung)
        self.assertEqual(storno.betrag, Decimal("-90.00"))
        self.assertEqual(offen(self.post), Decimal("90.00"))

    def test_storno_ist_nur_per_post_moeglich(self):
        """Negativtest: GET storniert nichts (405)."""
        self.client.get(f"/beitraege/zahlungen/{self.zahlung.pk}/storno/")

        self.assertEqual(Payment.objects.count(), 1)

    def test_ein_storno_kann_nicht_storniert_werden(self):
        """Negativtest: Storno einer Gegenbuchung wird verweigert."""
        storno = Payment.objects.create(
            post=self.post, betrag=Decimal("-90.00"), art=Payment.Art.BAR,
            storno_von=self.zahlung,
        )
        self.client.post(f"/beitraege/zahlungen/{storno.pk}/storno/")

        self.assertEqual(Payment.objects.count(), 2)


class PostenListeZahlungsanzeigeTests(TestCase):
    def test_postenliste_zeigt_offenen_betrag_und_status(self):
        self.client.force_login(make_user("vorstand", "admin"))
        post = make_post()

        response = self.client.get(f"{LISTE}?jahr=2026")

        self.assertContains(response, "Unbezahlt")
        self.assertContains(response, "90")
        self.assertContains(response, reverse("dues:zahlungsliste"))
        self.assertIn(post.member.nachname, response.content.decode())
```

- [ ] **Step 2: Run — FAIL** (404/ImportError)
- [ ] **Step 3: URLs** — `dues/urls.py`:

```python
urlpatterns = [
    path("beitraege/", views.posten_liste, name="posten_liste"),
    path("beitraege/lauf/", views.beitragslauf, name="beitragslauf"),
    path("beitraege/zahlungen/", views.zahlungsliste, name="zahlungsliste"),
    path("beitraege/zahlungen/buchen/", views.zahlung_buchen, name="zahlung_buchen"),
    path(
        "beitraege/zahlungen/<int:pk>/storno/",
        views.zahlung_stornieren,
        name="zahlung_stornieren",
    ),
    path("beitraege/mandate/", views.mandat_anlegen, name="mandat_anlegen"),
    path(
        "beitraege/mandate/<int:pk>/status/",
        views.mandat_status,
        name="mandat_status",
    ),
]
```

- [ ] **Step 4: Views** — `dues/views.py` ergänzen (Imports: `date`, `Decimal`, `InvalidOperation`, `get_object_or_404`, `transaction`, `AuditLog`, `Payment`, `SepaMandate`, `PostenStatus`, `eur`, `offen`, `posten_mit_status`, `hat_sepa_mandat`):

```python
def _betrag(roh):
    """Deutsches Zahlenformat aus dem Formular ('90,00' -> Decimal)."""
    if roh is None:
        return None
    text = str(roh).strip().replace("€", "").replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ArithmeticError):
        return None


def _datum(roh):
    if not roh:
        return timezone.localdate()
    try:
        return date.fromisoformat(str(roh).strip())
    except ValueError:
        return None


def _zahlungs_context(request, jahr, form=None, gewaehlt=None):
    return {
        "jahr": jahr,
        "jahre": _jahre(),
        "zahlungen": Payment.objects.filter(post__jahr=jahr).select_related(
            "post", "post__member", "erfasst_von"
        ),
        "posten": posten_mit_status(jahr),
        "gewaehlt": gewaehlt,
        "formular": form or {},
        "mitglieder": Member.objects.filter(status=Member.Status.AKTIV).order_by(
            "nachname", "vorname"
        ),
    }


@role_required(ADMIN_GROUP)
def zahlungsliste(request):
    """Zahlungen eines Jahres buchen und Mandate verwalten (PRD M2.3/M2.4)."""
    jahr = _parse_jahr(request.GET.get("jahr")) or _aktives_jahr()
    gewaehlt = None
    pk = _parse_int(request.GET.get("posten"))
    if pk:
        gewaehlt = next((z for z in posten_mit_status(jahr) if z["post"].pk == pk), None)
    form = {
        "post": gewaehlt["post"].pk if gewaehlt else "",
        "betrag": gewaehlt["offen"] if gewaehlt else "",
        "art": Payment.Art.UEBERWEISUNG,
    }
    return render(
        request, "dues/zahlungen.html", _zahlungs_context(request, jahr, form, gewaehlt)
    )


@role_required(ADMIN_GROUP)
@require_POST
def zahlung_buchen(request):
    """Bucht eine Zahlung; Fehler bleiben im Formular sichtbar (kein Redirect)."""
    jahr = _parse_jahr(request.POST.get("jahr")) or _aktives_jahr()
    form = {
        "post": request.POST.get("post", ""),
        "betrag": request.POST.get("betrag", ""),
        "art": request.POST.get("art", Payment.Art.UEBERWEISUNG),
        "referenz": request.POST.get("referenz", ""),
        "notiz": request.POST.get("notiz", ""),
        "datum": request.POST.get("datum", ""),
    }
    post = FeePost.objects.filter(pk=form["post"]).select_related("member").first()
    betrag = _betrag(form["betrag"])
    datum = _datum(form["datum"])
    if post is None or betrag is None or datum is None:
        messages.error(request, "Bitte Beitragsposten, Betrag und Datum prüfen.")
        return render(
            request, "dues/zahlungen.html", _zahlungs_context(request, jahr, form)
        )
    try:
        with transaction.atomic():
            payment = Payment(
                post=post,
                betrag=betrag,
                art=form["art"] if form["art"] in dict(Payment.Art.choices) else Payment.Art.BAR,
                datum=datum,
                referenz=form["referenz"],
                notiz=form["notiz"],
                erfasst_von=request.user,
            )
            payment.full_clean()
            payment.save()
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Zahlung gebucht",
                text=(
                    f"{post.jahr} · {post.member}: {payment.get_art_display()} "
                    f"{eur(payment.betrag)} am {payment.datum}"
                ),
                member=post.member,
            )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return render(
            request, "dues/zahlungen.html", _zahlungs_context(request, jahr, form)
        )
    messages.success(request, f"Zahlung über {eur(betrag)} gebucht.")
    return redirect(f"{reverse('dues:zahlungsliste')}?jahr={post.jahr}")


@role_required(ADMIN_GROUP)
@require_POST
def zahlung_stornieren(request, pk):
    """Hebt eine Fehlbuchung per Gegenbuchung auf (kein Löschen)."""
    original = get_object_or_404(Payment, pk=pk)
    if original.storno_von_id is not None:
        messages.error(request, "Eine Gegenbuchung kann nicht storniert werden.")
        return redirect(_zahlungen_und_jahr(original.post.jahr))
    with transaction.atomic():
        storno = Payment.objects.create(
            post=original.post,
            betrag=-original.betrag,
            art=original.art,
            datum=timezone.localdate(),
            storno_von=original,
            notiz=f"Storno zu #{original.pk}",
            erfasst_von=request.user,
        )
        AuditLog.objects.create(
            benutzer=request.user,
            aktion="Zahlung storniert",
            text=f"Storno zu #{original.pk} über {eur(storno.betrag)}",
            member=original.post.member,
        )
    messages.success(request, f"Zahlung #{original.pk} storniert.")
    return redirect(_zahlungen_und_jahr(original.post.jahr))
```

Hilfsfunktionen: `_parse_int`, `_zahlungen_und_jahr(jahr)` analog `_liste_und_jahr`; `posten_liste` erhält `"posts": posten_mit_status(jahr)` statt des bisherigen Querysets.
- [ ] **Step 5: Templates** — `posten_liste.html`: Tabellenkopf um `<th>Bezahlt</th><th>Offen</th><th>Status</th><th></th>`, Zeile:

```html
<td>{{ post.bezahlt }}&nbsp;€</td>
<td>{{ post.offen }}&nbsp;€</td>
<td><span class="badge {{ post.status_klasse }}">{{ post.status_label }}</span></td>
<td>
  <a class="button-link" href="{% url 'dues:zahlungsliste' %}?jahr={{ jahr }}&amp;posten={{ post.post.pk }}">Zahlung buchen</a>
</td>
```

`{% empty %}`-Zeile auf `colspan="7"`. Neu `dues/templates/dues/zahlungen.html` mit: Jahr-Filter (GET), Buchungsformular (`action="{% url 'dues:zahlung_buchen' %}"`, verstecktes `jahr`, Select `post` aus `posten`, `betrag`, `art`, `datum`, `referenz`, `notiz`), Zahlungstabelle mit Storno-Formular je Zeile (nur wenn `zahlung.storno_von_id` leer) und Mandat-Abschnitt.
- [ ] **Step 6: CSS** — in `static/css/app.css` nach Zeile 213:

```css
.badge-unbezahlt { background: #e5e7eb; color: #374151; }
.badge-offen { background: #fef3c7; color: #92400e; }
.badge-bezahlt { background: #d1fae5; color: #065f46; }
.badge-gutschrift { background: #e0e7ff; color: #3730a3; }
```

- [ ] **Step 7: Run** — `pytest dues/ -q` → grün.
- [ ] **Step 8: Commit**

```bash
git add dues/views.py dues/urls.py dues/templates/dues/ static/css/app.css dues/tests/test_views.py
git commit -m "T9: Zahlungsliste, Buchen und Storno"
```

---

### Task 4: SEPA-Mandate verwalten + Navigation

**Files:**
- Modify: `dues/views.py`, `dues/templates/dues/zahlungen.html`, `core/context_processors.py`
- Test: `dues/tests/test_views.py`, `core/tests/test_nav.py`

**Interfaces:**
- Produces: Routen `dues:mandat_anlegen` (POST `/beitraege/mandate/`), `dues:mandat_status` (POST `/beitraege/mandate/<pk>/status/`), Nav-Eintrag `dues:zahlungsliste`

- [ ] **Step 1: Failing tests**

```python
class MandatAnlegenTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.member = make_member(kategorie=kategorie("erwachsene"))

    def test_mandat_wird_angelegt_und_mit_aktivem_mandat_ist_sepa_buchbar(self):
        self.client.post(
            "/beitraege/mandate/",
            {"member": self.member.pk, "referenz": "M-2026-001", "datum": "2026-01-05"},
        )

        mandat = SepaMandate.objects.get()
        self.assertEqual(mandat.status, SepaMandate.Status.AKTIV)
        self.assertTrue(hat_sepa_mandat(self.member))

    def test_mandat_ohne_referenz_wird_abgelehnt(self):
        """Negativtest: ohne Referenz kein Mandat."""
        self.client.post(
            "/beitraege/mandate/", {"member": self.member.pk, "referenz": "", "datum": "2026-01-05"}
        )

        self.assertEqual(SepaMandate.objects.count(), 0)

    def test_doppelte_referenz_wird_abgelehnt(self):
        """Negativtest: die Referenz ist eindeutig."""
        SepaMandate.objects.create(member=self.member, referenz="M-2026-001")
        self.client.post(
            "/beitraege/mandate/", {"member": self.member.pk, "referenz": "M-2026-001", "datum": "2026-01-05"}
        )

        self.assertEqual(SepaMandate.objects.count(), 1)

    def test_mitglied_darf_kein_mandat_anlegen(self):
        """Negativtest: Mandate sind Vorstandssache (PRD §3.8)."""
        self.client.force_login(make_user("mitglied", "mitglied"))
        self.client.post(
            "/beitraege/mandate/", {"member": self.member.pk, "referenz": "M-1", "datum": "2026-01-05"}
        )

        self.assertEqual(SepaMandate.objects.count(), 0)


class MandatStatusTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.member = make_member(kategorie=kategorie("erwachsene"))
        self.mandat = SepaMandate.objects.create(member=self.member, referenz="M-1")

    def test_widerruf_wird_gesetzt_und_protokolliert(self):
        self.client.post(
            f"/beitraege/mandate/{self.mandat.pk}/status/",
            {"status": SepaMandate.Status.WIDERRUFEN},
        )

        self.mandat.refresh_from_db()
        self.assertEqual(self.mandat.status, SepaMandate.Status.WIDERRUFEN)
        eintrag = AuditLog.objects.get(aktion="SEPA-Mandat geändert")
        self.assertEqual(eintrag.alt_wert, SepaMandate.Status.AKTIV)
        self.assertEqual(eintrag.neu_wert, SepaMandate.Status.WIDERRUFEN)

    def test_status_ist_nur_per_post_moeglich(self):
        """Negativtest: GET ändert nichts (405)."""
        self.client.get(f"/beitraege/mandate/{self.mandat.pk}/status/")

        self.mandat.refresh_from_db()
        self.assertEqual(self.mandat.status, SepaMandate.Status.AKTIV)
```

Dazu in `core/tests/test_nav.py`: Admin sieht „Zahlungen", Rolle „mitglied" nicht.

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Views** — `mandat_anlegen` / `mandat_status`:

```python
@role_required(ADMIN_GROUP)
@require_POST
def mandat_anlegen(request):
    member = get_object_or_404(Member, pk=request.POST.get("member"))
    referenz = request.POST.get("referenz", "").strip()
    datum = _datum(request.POST.get("datum")) or timezone.localdate()
    if not referenz:
        messages.error(request, "Bitte eine Mandatsreferenz angeben.")
        return redirect(_zahlungen_und_jahr(_aktives_jahr()))
    try:
        with transaction.atomic():
            mandat = SepaMandate(
                member=member, referenz=referenz, datum=datum,
                status=SepaMandate.Status.AKTIV,
                notiz=request.POST.get("notiz", ""),
            )
            mandat.full_clean()
            mandat.save()
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="SEPA-Mandat angelegt",
                text=f"Referenz {mandat.referenz} ab {mandat.datum}",
                member=member,
            )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect(_zahlungen_und_jahr(_aktives_jahr()))
    messages.success(request, f"SEPA-Mandat {mandat.referenz} angelegt.")
    return redirect(_zahlungen_und_jahr(_aktives_jahr()))


@role_required(ADMIN_GROUP)
@require_POST
def mandat_status(request, pk):
    mandat = get_object_or_404(SepaMandate, pk=pk)
    status = request.POST.get("status", "")
    if status not in dict(SepaMandate.Status.choices):
        messages.error(request, "Unbekannter Mandatsstatus.")
        return redirect(_zahlungen_und_jahr(_aktives_jahr()))
    vorher = mandat.status
    mandat.status = status
    mandat.save(update_fields=["status"])
    AuditLog.objects.create(
        benutzer=request.user,
        aktion="SEPA-Mandat geändert",
        text=f"Referenz {mandat.referenz}",
        feld="status",
        alt_wert=vorher,
        neu_wert=status,
        member=mandat.member,
    )
    messages.success(request, f"Mandat {mandat.referenz}: Status {status}.")
    return redirect(_zahlungen_und_jahr(_aktives_jahr()))
```

Zusätzlich `mandate` im Zahlungslisten-Context (`_zahlungs_context`): `SepaMandate.objects.select_related("member").order_by("-datum")`.
- [ ] **Step 4: Nav** — in `core/context_processors.py` nach dem Beiträge-Eintrag: `("dues:zahlungsliste", "Zahlungen", {"admin"}),`
- [ ] **Step 5: Template** — Mandat-Abschnitt in `zahlungen.html`: Tabelle aller Mandate (Mitglied, Referenz, Status, Datum) mit Status-Formular je Zeile (drei Buttons je Statust) und Anlege-Formular.
- [ ] **Step 6: Run** — `pytest dues/ core/ -q` → grün.
- [ ] **Step 7: Commit**

```bash
git add dues core
git commit -m "T9: SEPA-Mandate verwalten + Navigation"
```

---

### Task 5: Integrationstest, Bank-API-Garantie, Doku, Browser-Check

**Files:**
- Create: `dues/tests/test_integration.py`, `dues/tests/test_keine_bank_api.py`
- Modify: `tasks/plan.md` (Checkbox T9), `tasks/todo.md` (Fortschrittsprotokoll)

**Interfaces:**
- Consumes: alles aus Task 1–4

- [ ] **Step 1: Failing Integrationstest** (`dues/tests/test_integration.py`)

```python
class BeitragsjahrVerlaufTests(TestCase):
    """End-to-End: Lauf → Zahlung → bezahlt → Storno → wieder offen."""

    def setUp(self):
        self.admin = User.objects.create_user("vorstand", password="x")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.client.force_login(self.admin)
        self.member = make_member(kategorie=kategorie("erwachsene"))
        SepaMandate.objects.create(member=self.member, referenz="M-1")

    def test_ganzes_beitragsjahr(self):
        fuehre_lauf(2026)

        self.client.post(
            BUCHEN,
            {"post": FeePost.objects.get().pk, "betrag": "90.00", "art": Payment.Art.SEPA},
        )
        post = FeePost.objects.get()
        self.assertEqual(posten_status(post), PostenStatus.BEZAHLT)

        zahlung = Payment.objects.get(storno_von__isnull=True)
        self.client.post(f"/beitraege/zahlungen/{zahlung.pk}/storno/")

        self.assertEqual(posten_status(post), PostenStatus.UNBEZAHLT)
        self.assertEqual(offen(post), Decimal("90.00"))
        self.assertEqual(
            AuditLog.objects.filter(aktion__in=["Zahlung gebucht", "Zahlung storniert"]).count(),
            2,
        )
```

- [ ] **Step 2: Bank-API-Test** (`dues/tests/test_keine_bank_api.py`)

```python
class KeineBankApiTests(SimpleTestCase):
    """Die Software führt keinen Einzug aus (PRD M2.3)."""

    VERBOTEN = ("requests", "urllib.request", "http.client", "httpx", "socket")

    def test_dues_importiert_keine_netzwerkbibliothek(self):
        quelle = Path(dues.__file__).parent
        offenders = []
        for datei in sorted(quelle.rglob("*.py")):
            text = datei.read_text(encoding="utf-8")
            for verboten in self.VERBOTEN:
                if f"import {verboten}" in text:
                    offenders.append(f"{datei.name}: {verboten}")

        self.assertEqual(offenders, [])
```

- [ ] **Step 3: Run** — `pytest -q` → alle grün (Zahl der Tests notieren).
- [ ] **Step 4: Browser-Check am laufenden Stack** (`docker compose up -d`): `/beitraege/` zeigt Spalten Bezahlt/Offen/Status + Button; `/beitraege/zahlungen/` bucht eine Zahlung, Überzahlung zeigt „Gutschrift", Storno wirkt; Layout 360 px und 1280 px ohne horizontalen Overflow; Nav zeigt „Zahlungen" nur für Admin.
- [ ] **Step 5: Doku fortschreiben** — `tasks/plan.md`: T9 auf `[x]`; `tasks/todo.md`: T9-Eintrag mit Verifikationsbelegen, „Nächste Schritte" auf T10 verschieben, `dues`-Hinweise für T10 (Zahlungsliste, `posten_mit_status`, Storno-Pfad) ergänzen.
- [ ] **Step 6: Commit**

```bash
git add tasks dues
git commit -m "T9: Integrationstests, Bank-API-Garantie, Doku"
```
