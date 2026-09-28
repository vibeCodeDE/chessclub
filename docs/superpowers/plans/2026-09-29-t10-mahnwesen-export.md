# T10: Mahnwesen + Beitrags-Export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Offene Beiträge eines Jahres übersehen, pro Beitragsposten eine 1. und 2. Mahnung mit Datum setzen, einen druckbaren Mahnbrief je Mitglied erzeugen und die Jahresbeiträge als CSV exportieren.

**Architecture:** Die Regelbasis kommt in zwei neue Fachmodule — `dues/mahnung.py` (Stufenregel, offene Posten, Brief-Daten) und `dues/export.py` (CSV-Spalten und -Zeilen) —, während `dues/services.py` unverändert Beitragslauf und Zahlungsstand behält. Die Datenmodelle `dues.Mahnung` und `verein.Vereinsdaten` tragen die Historie und die Absenderangaben. Views übersetzen nur HTTP in Service-Aufrufe; alle Rollenprüfungen bleiben im View-Dekorator.

**Tech Stack:** Django 5, PostgreSQL 16, pytest/pytest-django, Tailwind-CLI-Build (kein CDN, kein neues Frontend-Asset), Docker Compose für Tests und Browser-Check.

**Spezifikation:** `docs/superpowers/specs/2026-09-29-t10-mahnwesen-export-design.md`

## Global Constraints

- Tests laufen ausschließlich im Stack: `docker compose exec -T app pytest <pfad> -q` aus dem Repo-Wurzelverzeichnis. Es gibt kein lokales Python.
- Deutsch ist die Sprache der App: Docstrings, Commit-Messages, Fehlermeldungen, Templates, Variablennamen in Tests.
- Kommentare und Docstrings erklären **warum** (Muster aus T8/T9: `dues/services.py`, `dues/models.py`). Keine Kommentare, die das Offensichtliche wiederholen.
- Keine neue Abhängigkeit in `requirements.txt`. Kein CDN, kein Fremd-Asset. Das Print-Stylesheet des Mahnbriefs ist Inline-CSS im Template.
- Beträge werden in der Oberfläche deutsch formatiert (`dues.services.eur` bzw. `f"{x:.2f}".replace(".", ",")`). In der DB und in der Rechnung `Decimal`.
- Rollenprüfung immer über `@role_required(ADMIN_GROUP)` aus `core.roles`. Schreibaktionen immer `@require_POST`.
- Alemt/COMMIT-Messages in diesem Repo: `T10: <Kurzsatz>`.
- Bestehende `dues/tests/test_*.py` nicht umbenennen; die neuen Testdateien heißen `test_mahnung_models.py`, `test_mahnung_services.py`, `test_export.py`, `test_views_mahnung.py`.
- `services.py` bleibt unangetastet — wenn eine Funktion dort gebraucht wird (`offen`, `posten_mit_status`, `bezahlte_summe`, `PostenStatus`, `_BADGE`, `SUMME`, `eur`), wird sie **importiert**, nicht dupliziert.

---

### Task 1: App `verein` mit `Vereinsdaten`

**Files:**
- Create: `verein/__init__.py` (leer)
- Create: `verein/apps.py`
- Create: `verein/models.py`
- Create: `verein/admin.py`
- Create: `verein/migrations/__init__.py` (leer)
- Create: `verein/tests/__init__.py` (leer)
- Create: `verein/tests/test_models.py`
- Create: `verein/migrations/0001_initial.py` (per `makemigrations`, Committed-Datei ist generiert)
- Modify: `config/settings.py` (Zeile mit `"dues",` in `INSTALLED_APPS`)

**Interfaces:**
- Consumes: nichts
- Produces: `verein.models.Vereinsdaten` mit den Feldern `name`, `strasse`, `plz`, `ort`, `telefon`, `email`, `kassierer`, `zahlungshinweis`, `zahlungsziel` und der Klassenmethode `Vereinsdaten.aktuell() -> Vereinsdaten`. Wird in Task 7 von `dues/views.py` und im Brief-Template benutzt.

- [ ] **Step 1: App-Gerüst anlegen (leere `__init__.py` sind Pflicht)**

```powershell
New-Item -ItemType Directory -Path verein, verein\migrations, verein\tests | Out-Null
New-Item -ItemType File -Path verein\__init__.py, verein\migrations\__init__.py, verein\tests\__init__.py | Out-Null
```

- [ ] **Step 2: Failing test schreiben** — `verein/tests/test_models.py`:

```python
"""Vereinsdaten: genau ein Datensatz für Brief und spätere E-Mail (T10)."""

from django.test import TestCase

from verein.models import Vereinsdaten


class VereinsdatenTests(TestCase):
    def test_aktuell_legt_den_einzigen_datensatz_an(self):
        self.assertEqual(Vereinsdaten.objects.count(), 0)

        datensatz = Vereinsdaten.aktuell()

        self.assertEqual(Vereinsdaten.objects.count(), 1)
        self.assertEqual(datensatz.pk, 1)
        self.assertEqual(datensatz.name, "Schachverein")

    def test_aktuell_liefert_beim_zweiten_mal_denselben_datensatz(self):
        erster = Vereinsdaten.aktuell()

        zweiter = Vereinsdaten.aktuell()

        self.assertEqual(erster.pk, zweiter.pk)
        self.assertEqual(Vereinsdaten.objects.count(), 1)

    def test_der_name_ist_pflicht(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            Vereinsdaten(name="").full_clean()

    def test_save_erzwingt_pk_eins(self):
        zweiter = Vereinsdaten.objects.create(name="Zweiter Versuch")

        self.assertEqual(zweiter.pk, 1)
        self.assertEqual(Vereinsdaten.objects.count(), 1)

    def test_str_ist_der_name(self):
        datensatz = Vereinsdaten.objects.create(name="Schachverein Example")

        self.assertEqual(str(datensatz), "Schachverein Example")

    def test_alle_felder_koennen_befuellt_werden(self):
        datensatz = Vereinsdaten.objects.create(
            name="Schachverein Example",
            strasse="Turnierweg 3",
            plz="12345",
            ort="Musterstadt",
            telefon="0123 456",
            email="kasse@example.org",
            kassierer="R. Kaiser",
            zahlungshinweis="Bitte per Überweisung ausgleichen.",
            zahlungsziel="Verwendungszweck: Nachname, Vorname, Jahr",
        )

        self.assertEqual(datensatz.ort, "Musterstadt")
        self.assertEqual(datensatz.kassierer, "R. Kaiser")
        self.assertIn("Überweisung", datensatz.zahlungshinweis)
```

- [ ] **Step 3: Test laufen lassen, Fehlschlag bestätigen**

Run: `docker compose exec -T app pytest verein -q`
Expected: ERROR — `ModuleNotFoundError: No module named 'verein'`

- [ ] **Step 4: `verein/apps.py` schreiben**

```python
from django.apps import AppConfig


class VereinConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "verein"
```

- [ ] **Step 5: `verein/models.py` schreiben**

```python
"""Stammdaten des Vereins (T10, Grundlage für PRD M2.5).

Der Mahnbrief braucht Absender, Kontakt und Zahlungshinweis. Weil es dafür
noch kein Modell gab, sind die Angaben hier zentral gepflegt statt in den
Templates; T14 (Gruppemail) und T17 (News) lesen denselben Datensatz.

Es ist bewusst **ein** Datensatz: ``Vereinsdaten.aktuell()`` liefert ihn und legt
ihn beim ersten Aufruf an, damit ein frisches Deployment keinen ``DoesNotExist``
in der Briefansicht produziert. Gepflegt wird ausschließlich im Admin.
"""

from django.db import models


class Vereinsdaten(models.Model):
    name = models.CharField("Vereinsname", max_length=100)
    strasse = models.CharField("Straße/Nr.", max_length=200, blank=True)
    plz = models.CharField("PLZ", max_length=10, blank=True)
    ort = models.CharField("Ort", max_length=100, blank=True)
    telefon = models.CharField("Telefon", max_length=50, blank=True)
    email = models.EmailField("E-Mail", blank=True)
    kassierer = models.CharField("Kassierer/in", max_length=100, blank=True)
    zahlungshinweis = models.TextField(
        "Zahlungshinweis",
        blank=True,
        help_text="Textbaustein im Mahnbrief, z. B. die Zahlungswege.",
    )
    zahlungsziel = models.TextField(
        "Verwendungszweck",
        blank=True,
        help_text="Textbaustein im Mahnbrief, z. B. Bankverbindung und Zweck.",
    )

    class Meta:
        verbose_name = "Vereinsdaten"
        verbose_name_plural = "Vereinsdaten"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Genau eine Zeile: ein zweiter Versuch landet auf pk=1 statt eine
        # zweite, konkurrierende Konfiguration anzulegen.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def aktuell(cls):
        """Der eine Datensatz — wird beim ersten Aufruf angelegt."""
        datensatz, _ = cls.objects.get_or_create(
            pk=1, defaults={"name": "Schachverein"}
        )
        return datensatz
```

- [ ] **Step 6: `verein/admin.py` schreiben**

```python
from django.contrib import admin

from .models import Vereinsdaten


@admin.register(Vereinsdaten)
class VereinsdatenAdmin(admin.ModelAdmin):
    """Die Vereinsdaten werden ausschließlich hier gepflegt (T10)."""

    fields = (
        "name",
        "strasse",
        "plz",
        "ort",
        "telefon",
        "email",
        "kassierer",
        "zahlungshinweis",
        "zahlungsziel",
    )

    def has_add_permission(self, request):
        # Es gibt nur einen Datensatz (pk=1) — ein zweiter wäre bedeutungslos.
        return not Vereinsdaten.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
```

- [ ] **Step 7: App in den Settings anmelden** — in `config/settings.py` in `INSTALLED_APPS` nach der Zeile `"dues",` einfügen:

```python
    "verein",
```

- [ ] **Step 8: Test laufen lassen, Fehlschlag bestätigen** (Tabelle fehlt noch)

Run: `docker compose exec -T app pytest verein -q`
Expected: ERROR — `relation "verein_vereinsdaten" does not exist`

- [ ] **Step 9: Migration erzeugen**

Run: `docker compose exec -T app python manage.py makemigrations verein`
Expected: `Migrations for 'verein': 0001_initial.py` — die Datei `verein/migrations/0001_initial.py` entsteht und wird mit committet.

- [ ] **Step 10: Tests laufen lassen, Erfolg bestätigen**

Run: `docker compose exec -T app pytest verein -q`
Expected: 6 passed

- [ ] **Step 11: Commit**

```powershell
git add verein config/settings.py
git commit -m "T10: App verein mit Vereinsdaten fuer Brief und spaetere E-Mail"
```

---

### Task 2: Model `Mahnung` mit Migration und Admin

**Files:**
- Create: `dues/tests/test_mahnung_models.py`
- Modify: `dues/models.py` (Klasse `Mahnung` anhängen)
- Modify: `dues/admin.py` (`MahnungAdmin` registrieren)
- Create: `dues/migrations/0005_mahnung.py` (generiert)

**Interfaces:**
- Consumes: nichts Neues (`FeePost` existiert seit T8)
- Produces: `dues.models.Mahnung` mit `Stufe` (Choices 1/2), `post`, `stufe`, `datum`, `frist`, `notiz`, `erstellt`, `erstellt_von`, Constraint `unique_mahnung_pro_post_stufe`, `Meta.ordering = ["-datum", "-pk"]`, `related_name="mahnungen"` am Posten. Task 3+ lesen `post.mahnungen.all()`.

- [ ] **Step 1: Failing test schreiben** — `dues/tests/test_mahnung_models.py`:

```python
"""Mahnung als Finanznachweis am Beitragsposten (PRD M2.5)."""

from datetime import date
from decimal import Decimal

from django.db.utils import IntegrityError
from django.test import TestCase

from dues.models import FeeCategory, FeePost, Mahnung
from members.models import Member


def make_post(jahr=2026, betrag="90.00"):
    # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create holt
    # ihn im Testlauf, statt am unique-Slug zu scheitern.
    kategorie = FeeCategory.objects.get_or_create(
        code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
    )[0]
    member = Member.objects.create(
        vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 15),
        beitragskategorie=kategorie,
    )
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=kategorie, betrag=Decimal(betrag)
    )


class MahnungModelTests(TestCase):
    def setUp(self):
        self.post = make_post()

    def test_stufen_choices(self):
        self.assertEqual(Mahnung.Stufe.MAHNUNG_1, 1)
        self.assertEqual(Mahnung.Stufe.MAHNUNG_2, 2)
        self.assertEqual(
            [wert for wert, _ in Mahnung.Stufe.choices], [1, 2]
        )

    def test_defaults(self):
        mahnung = Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        self.assertEqual(mahnung.datum, date.today())
        self.assertIsNone(mahnung.frist)
        self.assertEqual(mahnung.notiz, "")
        self.assertIsNotNone(mahnung.erstellt)

    def test_gleiche_stufe_auf_demselben_posten_ist_unmoeglich(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        with self.assertRaises(IntegrityError):
            Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

    def test_hohere_stufe_auf_demselben_posten_ist_moeglich(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)

        self.assertEqual(self.post.mahnungen.count(), 2)

    def test_posten_sind_ueber_mahnungen_erreichbar(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        self.assertEqual(list(self.post.mahnungen.all())[0].stufe, 1)

    def test_posten_mit_mahnung_kann_nicht_geloescht_werden(self):
        from django.db.models import ProtectedError

        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        with self.assertRaises(ProtectedError):
            self.post.delete()

    def test_ordering_ist_neuestes_datum_zuerst(self):
        Mahnung.objects.create(
            post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1, datum=date(2026, 1, 10)
        )
        Mahnung.objects.create(
            post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2, datum=date(2026, 2, 10)
        )

        mahnungen = list(Mahnung.objects.all())

        self.assertEqual(mahnungen[0].datum, date(2026, 2, 10))
        self.assertEqual(mahnungen[1].datum, date(2026, 1, 10))

    def test_str_nennt_die_stufe_und_den_posten(self):
        mahnung = Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)

        self.assertIn("2. Mahnung", str(mahnung))
        self.assertIn("Meier, Anna", str(mahnung))
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `docker compose exec -T app pytest dues/tests/test_mahnung_models.py -q`
Expected: ERROR — `ImportError: cannot import name 'Mahnung'`

- [ ] **Step 3: Modell anhängen** — in `dues/models.py` ans Dateiende:

```python
class Mahnung(models.Model):
    """Eine Mahnung für einen Beitragsposten (PRD M2.5).

    Die Mahnung hängt am **Posten**, nicht am Mitglied: ein Mitglied kann
    Posten aus mehreren Jahren haben, und gemahnt wird je Posten. Die Stufe ist
    Teil der Historie (1. und 2. Mahnung), nicht ein Zähler am Posten — so
    bleiben Datum, Frist und der ausstellende Vorstand nachvollziehbar.

    Es gibt keinen Storno-Pfad: eine Mahnung wird nicht zurückgezogen. Zahlt
    das Mitglied, fällt der Posten aus der Offene-Übersicht; die Historie
    bleibt lesbar.
    """

    class Stufe(models.IntegerChoices):
        MAHNUNG_1 = 1, "1. Mahnung"
        MAHNUNG_2 = 2, "2. Mahnung"

    post = models.ForeignKey(
        FeePost,
        verbose_name="Beitragsposten",
        # Mahnungen sind Finanznachweis — kein Hard-Delete an der Historie.
        on_delete=models.PROTECT,
        related_name="mahnungen",
    )
    stufe = models.PositiveSmallIntegerField("Stufe", choices=Stufe.choices)
    datum = models.DateField("Mahndatum", default=timezone.localdate)
    frist = models.DateField(
        "Zahlungsfrist",
        null=True,
        blank=True,
        help_text="Optionales Fristdatum für den Brief; leer heißt „keine Frist“.",
    )
    notiz = models.TextField(
        "Notiz", blank=True, help_text="Interner Vermerk — erscheint nicht im Brief."
    )
    erstellt = models.DateTimeField("Erstellt", auto_now_add=True)
    erstellt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Erstellt von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="erstellte_mahnungen",
    )

    class Meta:
        ordering = ["-datum", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["post", "stufe"],
                name="unique_mahnung_pro_post_stufe",
            )
        ]
        verbose_name = "Mahnung"
        verbose_name_plural = "Mahnungen"

    def __str__(self):
        return f"{self.stufe}. Mahnung · {self.post}"
```

- [ ] **Step 4: Test laufen lassen, Fehlschlag bestätigen** (Tabelle fehlt)

Run: `docker compose exec -T app pytest dues/tests/test_mahnung_models.py -q`
Expected: ERROR — `relation "dues_mahnung" does not exist`

- [ ] **Step 5: Migration erzeugen**

Run: `docker compose exec -T app python manage.py makemigrations dues`
Expected: `Migrations for 'dues': 0005_mahnung.py`

- [ ] **Step 6: Admin ergänzen** — in `dues/admin.py` den Import auf `from .models import FeeAmount, FeeCategory, FeePost, Mahnung, Payment, SepaMandate` ändern und ans Dateiende:

```python
@admin.register(Mahnung)
class MahnungAdmin(admin.ModelAdmin):
    """Mahnungen entstehen nur über die Mahnungsübersicht (PRD M2.5).

    Im Admin sind sie nur einsehbar: Stufe, Datum und Frist sind fachliche
    Entscheidungen des Vorstands und gehören über die Mahnliste gesetzt, damit
    die Prüfungen aus `dues.mahnung` greifen.
    """

    list_display = ("post", "stufe", "datum", "frist", "erstellt_von")
    list_filter = ("stufe", "datum")
    search_fields = ("post__member__nachname", "post__member__vorname")
    readonly_fields = [feld.name for feld in Mahnung._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

- [ ] **Step 7: Tests laufen lassen, Erfolg bestätigen**

Run: `docker compose exec -T app pytest dues -q`
Expected: alle passed (151 + 8 neue = 159)

- [ ] **Step 8: Commit**

```powershell
git add dues/models.py dues/admin.py dues/migrations/0005_mahnung.py dues/tests/test_mahnung_models.py
git commit -m "T10: Modell Mahnung mit Stufe, Datum und Frist"
```

---

### Task 3: Stufenregel in `dues/mahnung.py`

**Files:**
- Create: `dues/tests/test_mahnung_services.py`
- Create: `dues/mahnung.py`

**Interfaces:**
- Consumes: `dues.models.FeePost`, `dues.models.Mahnung`, `dues.services.offen`, `core.models.AuditLog`
- Produces: `dues.mahnung.mahnstufe_text(stufe: int | None) -> str`, `dues.mahnung.naechste_stufe(post: FeePost) -> int | None`, `dues.mahnung.mahnungen_setzen(post, stufe, datum, frist=None, benutzer=None, notiz="") -> Mahnung` (wirft `django.core.exceptions.ValidationError`)

- [ ] **Step 1: Failing tests schreiben** — `dues/tests/test_mahnung_services.py`:

```python
"""Stufenregel des Mahnwesens (PRD M2.5) — ohne HTTP, nur Services."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import AuditLog
from dues.mahnung import mahnungen_setzen, mahnstufe_text, naechste_stufe
from dues.models import FeeCategory, FeePost, Mahnung, Payment
from members.models import Member


def make_member(nachname="Meier", vorname="Anna", kategorie=None):
    return Member.objects.create(
        vorname=vorname,
        nachname=nachname,
        eintrittsdatum=date(2020, 1, 15),
        beitragskategorie=kategorie,
    )


def make_post(member=None, jahr=2026, betrag="90.00", kategorie=None):
    # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create holt
    # ihn im Testlauf, statt am unique-Slug zu scheitern.
    kategorie = kategorie or FeeCategory.objects.get_or_create(
        code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
    )[0]
    member = member or make_member(kategorie=kategorie)
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=kategorie, betrag=Decimal(betrag)
    )


def zahle(post, betrag="90.00"):
    return Payment.objects.create(
        post=post, betrag=Decimal(betrag), art=Payment.Art.BAR
    )


class MahnstufeTextTests(TestCase):
    def test_erste_und_zweite_stufe(self):
        self.assertEqual(mahnstufe_text(1), "1. Mahnung")
        self.assertEqual(mahnstufe_text(2), "2. Mahnung")

    def test_ausgeschoepfte_stufen(self):
        self.assertEqual(mahnstufe_text(None), "ausgeschöpft")


class NaechsteStufeTests(TestCase):
    def setUp(self):
        self.post = make_post()

    def test_ohne_mahnung_ist_stufe_eins_naechste(self):
        self.assertEqual(naechste_stufe(self.post), 1)

    def test_nach_erster_mahnung_ist_stufe_zwei_naechste(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        self.assertEqual(naechste_stufe(self.post), 2)

    def test_nach_zwei_mahnungen_ist_keine_stufe_mehr_frei(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)

        self.assertIsNone(naechste_stufe(self.post))

    def test_stufe_ist_pro_posten_eigenstaendig(self):
        anderer = make_post(member=make_member(nachname="Koch", kategorie=self.post.kategorie))
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)

        self.assertEqual(naechste_stufe(anderer), 1)


class MahnungenSetzenTests(TestCase):
    def setUp(self):
        self.post = make_post()

    def test_setzt_die_erste_mahnung_mit_datum(self):
        mahnung = mahnungen_setzen(
            self.post, 1, date(2026, 3, 1), benutzer=User.objects.create_user("v")
        )

        self.assertEqual(mahnung.post, self.post)
        self.assertEqual(mahnung.stufe, 1)
        self.assertEqual(mahnung.datum, date(2026, 3, 1))
        self.assertIsNone(mahnung.frist)
        self.assertEqual(mahnung.notiz, "")

    def test_setzt_die_zweite_mahnung_mit_frist_und_notiz(self):
        mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        mahnung = mahnungen_setzen(
            self.post,
            2,
            date(2026, 4, 1),
            frist=date(2026, 4, 15),
            notiz="Telefonisch angekündigt",
        )

        self.assertEqual(mahnung.stufe, 2)
        self.assertEqual(mahnung.frist, date(2026, 4, 15))
        self.assertEqual(mahnung.notiz, "Telefonisch angekündigt")

    def test_rueckdatiertes_datum_wird_akzeptiert(self):
        """Eine Rückdatierung ist legitim — der Vorstand plant im Voraus."""

        mahnung = mahnungen_setzen(self.post, 1, date(2026, 1, 5))

        self.assertEqual(mahnung.datum, date(2026, 1, 5))

    def test_bezahlter_posten_wird_abgelehnt(self):
        zahle(self.post)

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        self.assertIn("bezahlt", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_gutschrift_wird_abgelehnt(self):
        zahle(self.post, "100.00")

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        self.assertIn("bezahlt", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_teilzahlung_bleibt_mahnbar(self):
        zahle(self.post, "40.00")

        mahnung = mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        self.assertEqual(mahnung.stufe, 1)

    def test_ueberspringen_der_stufe_wird_abgelehnt(self):
        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 2, date(2026, 3, 1))

        self.assertIn("1. Mahnung", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_doppelte_stufe_wird_abgelehnt(self):
        mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 4, 1))

        self.assertIn("existiert bereits", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 1)

    def test_nach_zwei_mahnungen_ist_keine_stufe_mehr_setzbar(self):
        mahnungen_setzen(self.post, 1, date(2026, 3, 1))
        mahnungen_setzen(self.post, 2, date(2026, 4, 1))

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 5, 1))

        self.assertIn("ausgeschöpft", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 2)

    def test_unbekannte_stufe_wird_abgelehnt(self):
        with self.assertRaises(ValidationError):
            mahnungen_setzen(self.post, 3, date(2026, 3, 1))

        self.assertEqual(Mahnung.objects.count(), 0)

    def test_ohne_datum_wird_abgelehnt(self):
        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, None)

        self.assertIn("Mahndatum", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_schreibt_einen_audit_eintrag_mit_mitglied(self):
        benutzer = User.objects.create_user("vorstand")

        mahnungen_setzen(
            self.post, 1, date(2026, 3, 1), frist=date(2026, 4, 1), benutzer=benutzer
        )

        eintrag = AuditLog.objects.get(aktion="Mahnung gesetzt")
        self.assertEqual(eintrag.member, self.post.member)
        self.assertEqual(eintrag.benutzer, benutzer)
        self.assertIn("1. Mahnung", eintrag.text)
        self.assertIn("2026-03-01", eintrag.text)

    def test_doppelbuchung_aus_dem_doppelklick_ergibt_keinen_500(self):
        """Zwei gleichzeitige Klicks: die Constraint wird als ValidationError gefangen."""
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 4, 1))

        self.assertIn("existiert bereits", str(fehler.exception))
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `docker compose exec -T app pytest dues/tests/test_mahnung_services.py -q`
Expected: ERROR — `ModuleNotFoundError: No module named 'dues.mahnung'`

- [ ] **Step 3: `dues/mahnung.py` — Teil 1: Stufenregel** (die Datei wird in Task 4 ergänzt, `offene_posten` steht noch nicht drin)

```python
"""Mahnwesen (PRD M2.5): offene Beiträge sehen, 1./2. Mahnung setzen, Brief.

Die Stufenregel steht hier und nicht im View, damit Übersicht, Brief und Tests
dieselbe Antwort bekommen. Grundlage ist :func:`dues.services.offen` — es gibt
im ganzen Mahnwesen keine zweite Berechnung des offenen Betrags.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.models import AuditLog

from .models import Mahnung
from .services import offen


def mahnstufe_text(stufe):
    """„1. Mahnung“ / „2. Mahnung“ / „ausgeschöpft“ — eine Quelle für alle Anzeigen."""
    if stufe is None:
        return "ausgeschöpft"
    return f"{stufe}. Mahnung"


def naechste_stufe(post):
    """Die Stufe, die als Nächstes gesetzt werden darf; ``None`` ist „keine mehr“.

    Stufen werden nicht übersprungen: ohne Mahnung beginnt es bei 1.
    """
    gesetzt = set(post.mahnungen.values_list("stufe", flat=True))
    for stufe in (Mahnung.Stufe.MAHNUNG_1, Mahnung.Stufe.MAHNUNG_2):
        if stufe not in gesetzt:
            return stufe
    return None


def _doppelte_stufe_meldung(post, stufe):
    return ValidationError(
        f"Die {mahnstufe_text(stufe)} für {post} existiert bereits — "
        "bitte die nächste Stufe setzen."
    )


def mahnungen_setzen(post, stufe, datum, frist=None, benutzer=None, notiz=""):
    """Setzt die nächste Mahnung für ``post`` (PRD M2.5).

    Drei Regeln, alle mit verständlicher Meldung statt Datenbankfehler:

    1. der Posten muss noch offen sein (Zahlung macht ihn unmahnbare),
    2. die Stufe muss genau :func:`naechste_stufe` sein — weder überspringen
       noch doppeln,
    3. ein Datum muss angegeben sein.

    Rückdatierte Daten sind erlaubt (der Vorstand mahnt im Voraus), ebenso eine
    Frist ohne Datum und ein leeres ``datum`` wird nie angenommen.
    """
    if datum is None:
        raise ValidationError("Bitte ein gültiges Mahndatum angeben.")

    erwartet = naechste_stufe(post)
    if erwartet is None:
        raise ValidationError(
            f"Für {post} sind beide Mahnstufen ausgeschöpft — "
            "es ist keine weitere Mahnung möglich."
        )
    if stufe != erwartet:
        if stufe in (Mahnung.Stufe.MAHNUNG_1, Mahnung.Stufe.MAHNUNG_2):
            if stufe < erwartet:
                raise _doppelte_stufe_meldung(post, stufe)
            raise ValidationError(
                f"Die {mahnstufe_text(stufe)} kann nicht gesetzt werden — "
                f"es fehlt die {mahnstufe_text(erwartet)}."
            )
        raise ValidationError("Unbekannte Mahnstufe.")

    if offen(post) <= Decimal("0.00"):
        raise ValidationError(
            f"Der Beitragsposten {post} ist bereits bezahlt — "
            "für ihn kann keine Mahnung gesetzt werden."
        )

    with transaction.atomic():
        try:
            with transaction.atomic():
                mahnung = Mahnung.objects.create(
                    post=post,
                    stufe=stufe,
                    datum=datum,
                    frist=frist,
                    notiz=notiz,
                    erstellt_von=benutzer,
                )
        except IntegrityError:
            # Zwei gleichzeitige Klicks: die DB-Constraint fängt ab, der
            # Vorstand soll trotzdem eine Meldung statt eines 500 sehen.
            raise _doppelte_stufe_meldung(post, stufe)

    AuditLog.objects.create(
        benutzer=benutzer,
        aktion="Mahnung gesetzt",
        text=(
            f"{post.jahr} · {post.member}: {mahnstufe_text(stufe)} vom "
            f"{datum.isoformat()}"
            + (f", Frist {frist.isoformat()}" if frist else "")
        ),
        member=post.member,
    )
    return mahnung
```

> Warum das doppelte `transaction.atomic()`: der innere Block ist ein
> Savepoint. Erst dadurch lässt sich eine `IntegrityError` der Constraint
> abfangen, ohne die äußere Transaktion kaputt zu machen — ein Fehler würde sonst
> die Transaktion unbrauchbar machen und der Audit-Eintrag unten fiele mit.

- [ ] **Step 4: Tests laufen lassen, Erfolg bestätigen**

Run: `docker compose exec -T app pytest dues/tests/test_mahnung_services.py -q`
Expected: 18 passed

- [ ] **Step 5: Commit**

```powershell
git add dues/mahnung.py dues/tests/test_mahnung_services.py
git commit -m "T10: Stufenregel des Mahnwesens (1./2. Mahnung, offener Posten)"
```

---

### Task 4: Offene-Posten-Übersicht und Briefdaten in `dues/mahnung.py`

**Files:**
- Modify: `dues/tests/test_mahnung_services.py` (Klassen anhängen)
- Modify: `dues/mahnung.py` (Funktionen anhängen)

**Interfaces:**
- Consumes: `dues.services.posten_mit_status`, `dues.services.SUMME`, `dues.mahnung.naechste_stufe`, `dues.mahnung.mahnstufe_text`
- Produces: `dues.mahnung.offene_posten(jahr: int) -> list[dict]` mit den Schlüsseln `post`, `member`, `kategorie`, `jahr`, `betrag`, `bezahlt`, `offen`, `status`, `status_label`, `status_klasse`, `mahnungen` (QuerySet der Mahnungen), `stufe` (int|None), `stufe_text` (str) — sowie `dues.mahnung.posten_fuer_brief(jahr: int, member: Member) -> tuple[list[dict], Decimal]` (Posten + Summe). Beide werden von Task 6 (Views/Templates) und Task 5 (Export) benutzt.

- [ ] **Step 1: Failing tests anhängen** — ans Ende von `dues/tests/test_mahnung_services.py` (zusätzlich oben `from dues.mahnung import offene_posten, posten_fuer_brief`):

```python
class OffenePostenTests(TestCase):
    def setUp(self):
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

    def _posten(self, anzahl, jahr=2026, betrag="90.00"):
        posten = []
        for nummer in range(anzahl):
            member = make_member(
                nachname=f"Mustermann{nummer:02d}",
                vorname="Anna",
                kategorie=self.kategorie,
            )
            posten.append(
                make_post(member=member, jahr=jahr, betrag=betrag, kategorie=self.kategorie)
            )
        return posten

    def test_leeres_jahr_ergibt_leere_liste(self):
        self.assertEqual(offene_posten(2030), [])

    def test_offene_posten_kommen_vor_bezahlten(self):
        offen_post, bezahlt_post = self._posten(2)

        zeilen = offene_posten(2026)

        self.assertEqual([zeile["post"] for zeile in zeilen], [offen_post])

    def test_bezahlter_posten_faehlt_heraus(self):
        (post,) = self._posten(1)
        zahle(post)

        self.assertEqual(offene_posten(2026), [])

    def test_teilzahlung_bleibt_offen(self):
        (post,) = self._posten(1, betrag="90.00")
        zahle(post, "40.00")

        (zeile,) = offene_posten(2026)

        self.assertEqual(zeile["offen"], Decimal("50.00"))
        self.assertEqual(zeile["status"], "teilbezahlt")

    def test_gutschrift_faehlt_heraus(self):
        (post,) = self._posten(1, betrag="90.00")
        zahle(post, "100.00")

        self.assertEqual(offene_posten(2026), [])

    def test_zeile_traegt_die_felder_der_postenliste(self):
        (post,) = self._posten(1)
        mahnungen_setzen(post, 1, date(2026, 3, 1))

        (zeile,) = offene_posten(2026)

        self.assertEqual(zeile["post"], post)
        self.assertEqual(zeile["member"], post.member)
        self.assertEqual(zeile["kategorie"], post.kategorie)
        self.assertEqual(zeile["betrag"], Decimal("90.00"))
        self.assertEqual(zeile["bezahlt"], Decimal("0.00"))
        self.assertEqual(zeile["offen"], Decimal("90.00"))
        self.assertEqual(zeile["status"], "unbezahlt")
        self.assertEqual(zeile["status_label"], "Unbezahlt")
        self.assertEqual(zeile["status_klasse"], "badge-unbezahlt")
        self.assertEqual(len(zeile["mahnungen"]), 1)
        self.assertEqual(zeile["stufe"], 2)
        self.assertEqual(zeile["stufe_text"], "2. Mahnung")

    def test_stufe_ist_none_bei_ausgeschoepften_stufen(self):
        (post,) = self._posten(1)
        mahnungen_setzen(post, 1, date(2026, 3, 1))
        mahnungen_setzen(post, 2, date(2026, 4, 1))

        (zeile,) = offene_posten(2026)

        self.assertIsNone(zeile["stufe"])
        self.assertEqual(zeile["stufe_text"], "ausgeschöpft")

    def test_sortiert_nach_nachname_und_vorname(self):
        self._posten(3)

        nachnamen = [zeile["member"].nachname for zeile in offene_posten(2026)]

        self.assertEqual(nachnamen, sorted(nachnamen))

    def test_anderes_jahr_wird_ignoriert(self):
        self._posten(2, jahr=2026)
        self._posten(1, jahr=2027)

        self.assertEqual(len(offene_posten(2026)), 2)
        self.assertEqual(len(offene_posten(2027)), 1)

    def test_ohne_zusatzabfragen(self):
        """Eine Abfrage für die Liste, eine für die Mahnungen — keine N+1."""
        self._posten(5)
        for zeile in offene_posten(2026):
            mahnungen_setzen(zeile["post"], 1, date(2026, 3, 1))

        with self.assertNumQueries(2):
            zeilen = offene_posten(2026)
            werte = [(z["offen"], z["stufe"], len(z["mahnungen"])) for z in zeilen]

        self.assertEqual(len(werte), 5)


class PostenFuerBriefTests(TestCase):
    def setUp(self):
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

        self.post = make_post(
            member=make_member(kategorie=self.kategorie), kategorie=self.kategorie
        )

    def test_liefert_die_offenen_posten_des_mitglieds(self):
        (posten, summe) = posten_fuer_brief(2026, self.post.member)

        self.assertEqual([p["post"] for p in posten], [self.post])
        self.assertEqual(summe, Decimal("90.00"))

    def test_ignoriert_bezahlte_posten(self):
        zahle(self.post)

        (posten, summe) = posten_fuer_brief(2026, self.post.member)

        self.assertEqual(posten, [])
        self.assertEqual(summe, Decimal("0.00"))

    def test_ignoriert_andere_mitglieder(self):
        anderer = make_post(
            member=make_member(nachname="Koch", kategorie=self.kategorie),
            kategorie=self.kategorie,
        )

        (posten, _) = posten_fuer_brief(2026, self.post.member)

        self.assertEqual([p["post"] for p in posten], [self.post])
        self.assertNotIn(anderer, [p["post"] for p in posten])

    def test_summe_ist_die_summe_aller_offenen_posten_des_mitglieds(self):
        """Zwei Jahre, zwei Beträge: in den Brief zählt nur das angefragte Jahr.

        `FeePost` hat `unique(member, jahr)` — ein zweiter Posten **für dasselbe
        Jahr** ist deshalb gar nicht möglich, und genau das nutzt der Test als
        Beleg dafür, dass `posten_fuer_brief` sauber nach Jahr filtert.
        """
        post_2026 = make_post(
            member=self.post.member, jahr=2026, betrag="90.00", kategorie=self.kategorie
        )
        post_2027 = make_post(
            member=self.post.member, jahr=2027, betrag="50.00", kategorie=self.kategorie
        )
        self.assertNotEqual(post_2026, post_2027)

        (posten, summe) = posten_fuer_brief(2026, self.post.member)

        self.assertEqual([p["post"] for p in posten], [post_2026])
        self.assertEqual(summe, Decimal("90.00"))

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

Run: `docker compose exec -T app pytest dues/tests/test_mahnung_services.py -q`
Expected: ERROR — `ImportError: cannot import name 'offene_posten'`

- [ ] **Step 3: Importliste ergänzen** — oben in `dues/mahnung.py` wird

```python
from .models import Mahnung
from .services import offen
```

zu

```python
from .models import Mahnung
from .services import offen, posten_mit_status
```

(FeePost wird hier nicht gebraucht — `posten_mit_status` liefert die Zeilen.)

- [ ] **Step 4: `naechste_stufe` aufteilen** — den bisherigen Rumpf von
`naechste_stufe` (Task 3) ersetzen durch zwei Funktionen, damit `offene_posten`
keine Abfrage je Zeile braucht:

```python
def naechste_stufe_fuer(mahnungen):
    """:func:`naechste_stufe` für eine bereits geladene Liste von Mahnungen."""
    gesetzt = {mahnung.stufe for mahnung in mahnungen}
    for stufe in (Mahnung.Stufe.MAHNUNG_1, Mahnung.Stufe.MAHNUNG_2):
        if stufe not in gesetzt:
            return stufe
    return None


def naechste_stufe(post):
    """Die Stufe, die als Nächstes gesetzt werden darf; ``None`` ist „keine mehr“.

    Stufen werden nicht übersprungen: ohne Mahnung beginnt es bei 1.
    """
    return naechste_stufe_fuer(post.mahnungen.all())
```

- [ ] **Step 5: `offene_posten` und `posten_fuer_brief` anhängen** — ans Ende von `dues/mahnung.py`:

```python
def offene_posten(jahr):
    """Beitragsposten des Jahres, die noch offen sind — eine Abfrage, keine N+1.

    Basis ist :func:`dues.services.posten_mit_status` (Posten, Kategorie, Mit-
    glied und Zahlungsstand in einer Abfrage). Danach wird nur ausgefiltert:
    ``offen <= 0`` fällt heraus — dazu gehören bezahlte Posten und Gutschriften,
    denn auf beides schreibt man keinen Mahnbrief. Die Mahnungen aller Posten
    des Jahres kommen in **einer** Abfrage und werden über ``post_id`` indexiert,
    damit die Stufe je Zeile keine Zusatzabfrage kostet.
    """
    mahnungen_pro_post = {}
    for mahnung in Mahnung.objects.filter(post__jahr=jahr).order_by("datum", "pk"):
        mahnungen_pro_post.setdefault(mahnung.post_id, []).append(mahnung)

    zeilen = []
    for zeile in posten_mit_status(jahr):
        if zeile["offen"] <= Decimal("0.00"):
            continue
        mahnungen = mahnungen_pro_post.get(zeile["post"].pk, [])
        stufe = naechste_stufe_fuer(mahnungen)
        zeile.update(
            mahnungen=mahnungen,
            stufe=stufe,
            stufe_text=mahnstufe_text(stufe),
        )
        zeilen.append(zeile)
    return zeilen


def posten_fuer_brief(jahr, member):
    """Offene Posten eines Mitglieds plus Summe — Grundlage des Mahnbriefs.

    Schneidet bewusst aus :func:`offene_posten`, damit Brief und Übersicht nie
    auseinanderlaufen können. Ist die Liste leer (inzwischen bezahlt), gibt es
    keinen Brief — die View gibt dann 404.
    """
    posten = [z for z in offene_posten(jahr) if z["post"].member_id == member.pk]
    summe = sum((z["offen"] for z in posten), Decimal("0.00"))
    return posten, summe
```

- [ ] **Step 6: Tests laufen lassen, Erfolg bestätigen**

Run: `docker compose exec -T app pytest dues/tests/test_mahnung_services.py -q`
Expected: alle passed (18 + 14 = 32)

- [ ] **Step 7: Commit**

```powershell
git add dues/mahnung.py dues/tests/test_mahnung_services.py
git commit -m "T10: Offene-Beitrags-Uebersicht und Briefdaten ohne N+1"
```

---

### Task 5: CSV-Export in `dues/export.py`

**Files:**
- Create: `dues/tests/test_export.py`
- Create: `dues/export.py`

**Interfaces:**
- Consumes: `dues.services.posten_mit_status`, `dues.mahnung.naechste_stufe_fuer`, `dues.mahnung.mahnstufe_text`
- Produces: `dues.export.CSV_SPALTEN` (Tuple[str, ...], 11 Spalten) und `dues.export.beitragszeilen(jahr: int) -> list[list[str]]` — die erste Zeile ist der Kopf. Task 6 schreibt daraus die HttpResponse.

- [ ] **Step 1: Failing test schreiben** — `dues/tests/test_export.py`:

```python
"""CSV-Export der Jahresbeiträge: Finanzdaten, keine Kontaktdaten (PRD M2.5)."""

import csv
import io
from datetime import date
from decimal import Decimal

from django.test import TestCase

from dues.export import CSV_SPALTEN, beitragszeilen
from dues.mahnung import mahnungen_setzen
from dues.models import FeeCategory, FeePost, Mahnung, Payment
from members.models import Member

VERBOTENE_INHALTE = ("Musterweg", "12345", "Musterstadt", "kasse@example.org",
                     "0123 456", "1985-04-01")


def csv_zeilen(text):
    return list(csv.reader(io.StringIO(text.lstrip("\ufeff")), delimiter=";"))


def make_member(nachname="Meier", vorname="Anna", **kwargs):
    daten = {
        "vorname": vorname,
        "nachname": nachname,
        "eintrittsdatum": date(2020, 1, 15),
        "geburtsdatum": date(1985, 4, 1),
        "strasse": "Musterweg 3",
        "plz": "12345",
        "ort": "Musterstadt",
        "email": "kasse@example.org",
        "telefon": "0123 456",
    }
    daten.update(kwargs)
    return Member.objects.create(**daten)


def make_post(member, jahr=2026, betrag="90.00", kategorie=None):
    # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create holt
    # ihn im Testlauf, statt am unique-Slug zu scheitern.
    kategorie = kategorie or FeeCategory.objects.get_or_create(
        code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
    )[0]
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=kategorie, betrag=Decimal(betrag)
    )


class CsvSpaltenTests(TestCase):
    def test_spaltenliste_ist_dokumentiert(self):
        self.assertEqual(
            CSV_SPALTEN,
            (
                "Jahr", "Nachname", "Vorname", "Kategorie", "Beitrag", "Bezahlt",
                "Offen", "Status", "Mahnungen", "1. Mahnung am", "2. Mahnung am",
            ),
        )

    def test_spaltenliste_ist_der_kopf(self):
        member = make_member()
        make_post(member)

        zeilen = beitragszeilen(2026)

        self.assertEqual(tuple(zeilen[0]), CSV_SPALTEN)


class CsvInhaltTests(TestCase):
    def setUp(self):
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

    def test_zeile_eines_unbezahlten_postens(self):
        member = make_member()
        make_post(member, kategorie=self.kategorie)

        (kopf, zeile) = beitragszeilen(2026)

        zeilenwert = dict(zip(kopf, zeile))
        self.assertEqual(zeilenwert["Jahr"], "2026")
        self.assertEqual(zeilenwert["Nachname"], "Meier")
        self.assertEqual(zeilenwert["Vorname"], "Anna")
        self.assertEqual(zeilenwert["Kategorie"], "Erwachsene")
        self.assertEqual(zeilenwert["Beitrag"], "90,00")
        self.assertEqual(zeilenwert["Bezahlt"], "0,00")
        self.assertEqual(zeilenwert["Offen"], "90,00")
        self.assertEqual(zeilenwert["Status"], "Unbezahlt")
        self.assertEqual(zeilenwert["Mahnungen"], "0")
        self.assertEqual(zeilenwert["1. Mahnung am"], "")
        self.assertEqual(zeilenwert["2. Mahnung am"], "")

    def test_zeile_eines_bezahlten_postens(self):
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        Payment.objects.create(
            post=post, betrag=Decimal("90.00"), art=Payment.Art.BAR
        )

        (kopf, zeile) = beitragszeilen(2026)

        zeilenwert = dict(zip(kopf, zeile))
        self.assertEqual(zeilenwert["Bezahlt"], "90,00")
        self.assertEqual(zeilenwert["Offen"], "0,00")
        self.assertEqual(zeilenwert["Status"], "Bezahlt")

    def test_mahndaten_stehen_in_ihren_spalten(self):
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        mahnungen_setzen(post, 1, date(2026, 3, 1))
        mahnungen_setzen(post, 2, date(2026, 4, 15))

        (kopf, zeile) = beitragszeilen(2026)

        zeilenwert = dict(zip(kopf, zeile))
        self.assertEqual(zeilenwert["Mahnungen"], "2")
        self.assertEqual(zeilenwert["1. Mahnung am"], "2026-03-01")
        self.assertEqual(zeilenwert["2. Mahnung am"], "2026-04-15")

    def test_mahnungen_werden_als_iso_datum_ausgegeben(self):
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        mahnungen_setzen(post, 1, date(2026, 3, 1), frist=date(2026, 4, 1))

        (kopf, zeile) = beitragszeilen(2026)

        zeilenwert = dict(zip(kopf, zeile))
        # Die Frist steht bewusst nicht in der Datei — sie gehört in den Brief.
        self.assertEqual(zeilenwert["1. Mahnung am"], "2026-03-01")

    def test_alle_posten_des_jahres(self):
        for nummer in range(4):
            make_post(
                make_member(nachname=f"Mustermann{nummer:02d}"),
                kategorie=self.kategorie,
            )
        make_post(make_member(nachname="Später"), jahr=2027, kategorie=self.kategorie)

        zeilen = beitragszeilen(2026)

        self.assertEqual(len(zeilen) - 1, 4)
        self.assertEqual(FeePost.objects.filter(jahr=2026).count(), 4)

    def test_bezahlte_posten_sind_enthalten(self):
        """Der Export ist die Jahresübersicht, nicht die Mahnliste."""
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        Payment.objects.create(
            post=post, betrag=Decimal("90.00"), art=Payment.Art.BAR
        )

        zeilen = beitragszeilen(2026)

        self.assertEqual(len(zeilen) - 1, 1)

    def test_leeres_jahr_liefert_nur_den_kopf(self):
        self.assertEqual(beitragszeilen(2026), [list(CSV_SPALTEN)])

    def test_sortiert_nach_nachname_und_vorname(self):
        make_post(make_member(nachname="Ziegler"), kategorie=self.kategorie)
        make_post(make_member(nachname="Bauer"), kategorie=self.kategorie)
        make_post(make_member(nachname="Aigner"), kategorie=self.kategorie)

        zeilen = beitragszeilen(2026)

        nachnamen = [zeile[1] for zeile in zeilen[1:]]
        self.assertEqual(nachnamen, ["Aigner", "Bauer", "Ziegler"])

    def test_zwei_exporte_sind_identisch(self):
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        mahnungen_setzen(post, 1, date(2026, 3, 1))

        self.assertEqual(beitragszeilen(2026), beitragszeilen(2026))

    def test_jahressumme_entspricht_der_modellsumme(self):
        for nummer, betrag in enumerate(("90.00", "50.00", "45.00")):
            post = make_post(
                make_member(nachname=f"Mustermann{nummer:02d}"),
                betrag=betrag,
                kategorie=self.kategorie,
            )
            Payment.objects.create(
                post=post, betrag=Decimal("20.00"), art=Payment.Art.BAR
            )

        zeilen = beitragszeilen(2026)
        offene_spalte = CSV_SPALTEN.index("Offen")

        export_summe = sum(
            (Decimal(zeile[offene_spalte].replace(",", ".")) for zeile in zeilen[1:]),
            Decimal("0.00"),
        )
        modell_summe = sum(
            (
                post.betrag
                - sum(
                    z.betrag
                    for z in Payment.objects.filter(post=post)
                )
                for post in FeePost.objects.filter(jahr=2026)
            ),
            Decimal("0.00"),
        )

        self.assertEqual(export_summe, modell_summe)
        self.assertEqual(export_summe, Decimal("135.00"))


class CsvDatensparsamkeitTests(TestCase):
    """Inhaltstest aus plan.md: der Export enthält keine Kontaktdaten."""

    def setUp(self):
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

    def test_keine_adressen_und_keine_kontaktdaten(self):
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        mahnungen_setzen(post, 1, date(2026, 3, 1))

        zeilen = beitragszeilen(2026)
        volltext = "\n".join(";".join(zeile) for zeile in zeilen)

        for verboten in VERBOTENE_INHALTE:
            self.assertNotIn(verboten, volltext)

    def test_keine_adressen_anderer_mitglieder(self):
        """Adressen Dritter landen nicht im Export — auch nicht über die Mahnhistorie."""
        exportiert = make_member(nachname="Exportiert")
        fremd = make_member(nachname="Fremd", vorname="Fritz")
        make_post(exportiert, kategorie=self.kategorie)
        post_fremd = make_post(fremd, kategorie=self.kategorie)
        mahnungen_setzen(post_fremd, 1, date(2026, 3, 1))

        zeilen = beitragszeilen(2026)
        volltext = "\n".join(";".join(zeile) for zeile in zeilen)

        self.assertNotIn("Fritz", volltext)
        self.assertNotIn("Fremd", volltext)
        # … der eigene Posten des exportierten Mitglieds aber schon.
        self.assertIn("Exportiert", volltext)

    def test_jede_zeile_hat_so_viele_spalten_wie_der_kopf(self):
        make_post(make_member(), kategorie=self.kategorie)
        make_post(make_member(nachname="Zweiter"), kategorie=self.kategorie)

        zeilen = beitragszeilen(2026)

        for zeile in zeilen:
            self.assertEqual(len(zeile), len(CSV_SPALTEN))

    def test_zeilen_lesen_sich_als_csv(self):
        make_post(make_member(), kategorie=self.kategorie)

        zeilen = beitragszeilen(2026)
        text = "\n".join(";".join(zeile) for zeile in zeilen)

        self.assertEqual(csv_zeilen(text)[0], list(CSV_SPALTEN))
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `docker compose exec -T app pytest dues/tests/test_export.py -q`
Expected: ERROR — `ModuleNotFoundError: No module named 'dues.export'`

- [ ] **Step 3: `dues/export.py` schreiben**

```python
"""CSV-Export der Jahresbeiträge (PRD M2.5) — für Buchhaltung und Vorstand.

Der Export enthält bewusst **nur** Finanz- und Mahndaten: er wird weitergegeben,
und die Kontaktdaten eines Mitglieds stehen im Mahnbrief (Task 7), nicht in
einer Tabelle, die beim Bearbeiten durch die Hände geht. ``CSV_SPALTEN`` ist
deshalb die Erlaubnis: was nicht dort steht, darf nicht im Export stehen.

Diese Datei liefert Zeilen, keine HTTP-Antwort — der View entscheidet über
Dateiname und Header (Muster aus ``members.views.mitglieder_export``).
"""

from .models import Mahnung
from .services import posten_mit_status

# Reihenfolge ist Vertrag: der Inhaltstest in dues/tests/test_export.py prüft
# Kopf und Zellen gegen genau diese Liste.
CSV_SPALTEN = (
    "Jahr",
    "Nachname",
    "Vorname",
    "Kategorie",
    "Beitrag",
    "Bezahlt",
    "Offen",
    "Status",
    "Mahnungen",
    "1. Mahnung am",
    "2. Mahnung am",
)


def _betrag(wert):
    """Deutsches Zahlenformat für die Zelle — Excel mit deutscher Gebietsschema."""
    return f"{wert:.2f}".replace(".", ",")


def _mahn_datum(mahnungen, stufe):
    for mahnung in mahnungen:
        if mahnung.stufe == stufe:
            return mahnung.datum.isoformat()
    return ""


def beitragszeilen(jahr):
    """Alle Beitragsposten des Jahres als CSV-Zeilen (inklusive Kopfzeile).

    Anders als :func:`dues.mahnung.offene_posten` werden **alle** Posten
    ausgegeben, auch bezahlte: der Export ist die Jahresübersicht für die
    Buchhaltung, nicht die Mahnliste.
    """
    mahnungen_pro_post = {}
    for mahnung in Mahnung.objects.filter(post__jahr=jahr).order_by("stufe", "pk"):
        mahnungen_pro_post.setdefault(mahnung.post_id, []).append(mahnung)

    zeilen = [list(CSV_SPALTEN)]
    for zeile in posten_mit_status(jahr):
        post = zeile["post"]
        mahnungen = mahnungen_pro_post.get(post.pk, [])
        zeilen.append(
            [
                str(jahr),
                post.member.nachname,
                post.member.vorname,
                post.kategorie.bezeichnung,
                _betrag(post.betrag),
                _betrag(zeile["bezahlt"]),
                _betrag(zeile["offen"]),
                zeile["status_label"],
                str(len(mahnungen)),
                _mahn_datum(mahnungen, Mahnung.Stufe.MAHNUNG_1),
                _mahn_datum(mahnungen, Mahnung.Stufe.MAHNUNG_2),
            ]
        )
    return zeilen
```

- [ ] **Step 4: Tests laufen lassen, Erfolg bestätigen**

Run: `docker compose exec -T app pytest dues/tests/test_export.py -q`
Expected: alle passed (17)

- [ ] **Step 5: Commit**

```powershell
git add dues/export.py dues/tests/test_export.py
git commit -m "T10: CSV-Export der Jahresbeitraege ohne Kontaktdaten"
```

---

### Task 6: Mahnliste mit Mahnformular, Export-View und Nav

**Files:**
- Create: `dues/tests/test_views_mahnung.py`
- Create: `dues/templates/dues/mahnliste.html`
- Modify: `dues/views.py` (drei Views anhängen)
- Modify: `dues/urls.py` (drei Routen)
- Modify: `core/context_processors.py` (Nav-Eintrag)

**Interfaces:**
- Consumes: `dues.mahnung.offene_posten`, `dues.mahnung.mahnungen_setzen`, `dues.mahnung.mahnstufe_text`, `dues.export.beitragszeilen`, `dues.export.CSV_SPALTEN`, `dues.views._parse_jahr`, `dues.views._jahre`, `dues.views._aktives_jahr`, `dues.views._datum`, `dues.views._liste_und_jahr`
- Produces: URLs `dues:mahnliste` (`/beitraege/mahnungen/`), `dues:mahnung_setzen` (`/beitraege/mahnungen/<pk>/setzen/`, POST), `dues:beitraege_export` (`/beitraege/export.csv`). Task 7 ergänzt `dues:mahnbrief`.

- [ ] **Step 1: Failing tests schreiben** — `dues/tests/test_views_mahnung.py`:

```python
"""Mahnliste, Mahnformular und Export in der Oberfläche (PRD M2.5)."""

import csv
import io
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from dues.models import FeeCategory, FeePost, Mahnung, Payment
from members.models import Member

MAHNLISTE = "/beitraege/mahnungen/"
EXPORT = "/beitraege/export.csv"


def make_user(username, group_name):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


def make_member(nachname="Meier", vorname="Anna", kategorie=None):
    return Member.objects.create(
        vorname=vorname,
        nachname=nachname,
        eintrittsdatum=date(2020, 1, 15),
        beitragskategorie=kategorie,
    )


def make_post(member=None, jahr=2026, betrag="90.00", kategorie=None):
    # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create holt
    # ihn im Testlauf, statt am unique-Slug zu scheitern.
    kategorie = kategorie or FeeCategory.objects.get_or_create(
        code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
    )[0]
    member = member or make_member(kategorie=kategorie)
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=kategorie, betrag=Decimal(betrag)
    )


def zahle(post, betrag="90.00"):
    return Payment.objects.create(
        post=post, betrag=Decimal(betrag), art=Payment.Art.BAR
    )


class MahnlisteZugriffTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.post = make_post()

    def test_admin_darf_die_mahnliste_sehen(self):
        self.client.force_login(self.admin)

        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Offene Beiträge")

    def test_mitglied_erhaelt_403(self):
        self.client.force_login(make_user("mitglied", "mitglied"))

        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.status_code, 403)

    def test_kapitaen_erhaelt_403(self):
        self.client.force_login(make_user("kapitaen", "kapitaen"))

        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.status_code, 403)

    def test_gast_wird_zum_anmelden_umgeleitet(self):
        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response["Location"])

    def test_403_erzeugt_keine_mahnung(self):
        """Negativtest: der verweigerte Zugriff darf nichts schreiben."""
        user = make_user("mitglied", "mitglied")
        self.client.force_login(user)

        self.client.post(
            f"{MAHNLISTE}{self.post.pk}/setzen/",
            {"datum": "2026-03-01"},
        )

        self.assertEqual(Mahnung.objects.count(), 0)


class MahnlisteInhaltTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

    def test_offener_posten_erscheint_mit_summe(self):
        make_post(kategorie=self.kategorie)

        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.context["summe_offen"], Decimal("90.00"))
        self.assertContains(response, "Meier")
        self.assertContains(response, "1. Mahnung")

    def test_bezahlter_posten_erscheint_nicht(self):
        post = make_post(kategorie=self.kategorie)
        zahle(post)

        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.context["zeilen"], [])
        self.assertEqual(response.context["summe_offen"], Decimal("0.00"))

    def test_jahr_ohne_lauf_zeigt_hinweis_statt_crash(self):
        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Für dieses Jahr wurden keine Beiträge gebucht.")

    def test_jahresfilter_zeigt_das_gewahlte_jahr(self):
        make_post(kategorie=self.kategorie)
        response = self.client.get(MAHNLISTE, {"jahr": "2026"})

        self.assertEqual(response.context["jahr"], 2026)
        self.assertEqual(len(response.context["zeilen"]), 1)

    def test_unlesbares_jahr_zeigt_das_aktuelle(self):
        response = self.client.get(MAHNLISTE, {"jahr": "keinjahr"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jahr"], date.today().year)

    def test_mahnbutton_nur_wenn_noch_eine_stufe_frei_ist(self):
        post = make_post(kategorie=self.kategorie)

        response = self.client.get(MAHNLISTE)
        self.assertContains(response, "/setzen/")

        Mahnung.objects.create(post=post, stufe=1, datum=date(2026, 3, 1))
        Mahnung.objects.create(post=post, stufe=2, datum=date(2026, 4, 1))

        response = self.client.get(MAHNLISTE)
        self.assertNotContains(response, "/setzen/")

    def test_bisherige_mahnungen_werden_angezeigt(self):
        post = make_post(kategorie=self.kategorie)
        Mahnung.objects.create(post=post, stufe=1, datum=date(2026, 3, 1))

        response = self.client.get(MAHNLISTE)

        # Das Template formatiert das Datum deutsch, nicht als ISO-String.
        self.assertContains(response, "01.03.2026")
        self.assertContains(response, "1. Mahnung am 01.03.2026")


class MahnungSetzenTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.post = make_post()

    def url(self):
        return reverse("dues:mahnung_setzen", args=[self.post.pk])

    def test_setzt_die_mahnung_und_leitet_auf_die_liste(self):
        response = self.client.post(
            self.url(), {"stufe": "1", "datum": "2026-03-01", "frist": "2026-04-01"}
        )

        mahnung = Mahnung.objects.get()
        self.assertEqual(mahnung.post, self.post)
        self.assertEqual(mahnung.stufe, 1)
        self.assertEqual(mahnung.datum, date(2026, 3, 1))
        self.assertEqual(mahnung.frist, date(2026, 4, 1))
        self.assertEqual(mahnung.erstellt_von, self.admin)
        self.assertRedirects(
            response, f"{MAHNLISTE}?jahr=2026", fetch_redirect_response=False
        )

    def test_ohne_frist_wird_keine_frist_gespeichert(self):
        self.client.post(self.url(), {"stufe": "1", "datum": "2026-03-01"})

        self.assertIsNone(Mahnung.objects.get().frist)

    def test_notiz_wird_uebernommen(self):
        self.client.post(
            self.url(),
            {"stufe": "1", "datum": "2026-03-01", "notiz": "Rückruf vereinbart"},
        )

        self.assertEqual(Mahnung.objects.get().notiz, "Rückruf vereinbart")

    def test_get_ist_nicht_erlaubt(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_uebersprungene_stufe_wird_abgelehnt(self):
        response = self.client.post(self.url(), {"stufe": "2", "datum": "2026-03-01"})

        self.assertEqual(Mahnung.objects.count(), 0)
        self.assertEqual(response.status_code, 302)
        self.assertContains(response, "1. Mahnung")

    def test_bezahlter_posten_wird_abgelehnt(self):
        zahle(self.post)

        self.client.post(self.url(), {"stufe": "1", "datum": "2026-03-01"})

        self.assertEqual(Mahnung.objects.count(), 0)

    def test_unlesbares_datum_wird_abgelehnt(self):
        response = self.client.post(self.url(), {"stufe": "1", "datum": "kein-datum"})

        self.assertEqual(Mahnung.objects.count(), 0)
        self.assertContains(response, "Mahndatum")

    def test_unbekannter_posten_ergibt_404(self):
        response = self.client.post(
            reverse("dues:mahnung_setzen", args=[999999]),
            {"stufe": "1", "datum": "2026-03-01"},
        )

        self.assertEqual(response.status_code, 404)


class ExportViewTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

    def test_export_ist_eine_csv_datei(self):
        make_post(kategorie=self.kategorie)

        response = self.client.get(EXPORT)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("beitraege_2026.csv", response["Content-Disposition"])

    def test_export_ist_bom_und_semikolon(self):
        make_post(kategorie=self.kategorie)

        inhalt = self.client.get(EXPORT).content.decode("utf-8")

        self.assertTrue(inhalt.startswith("\ufeff"))
        self.assertIn("Nachname;Vorname", inhalt)

    def test_export_ist_lesbar_und_komplett(self):
        make_post(kategorie=self.kategorie)
        Mahnung.objects.create(
            post=FeePost.objects.get(), stufe=1, datum=date(2026, 3, 1)
        )

        inhalt = self.client.get(EXPORT).content.decode("utf-8")
        zeilen = list(csv.reader(io.StringIO(inhalt.lstrip("\ufeff")), delimiter=";"))

        self.assertEqual(zeilen[0][0], "Jahr")
        self.assertEqual(zeilen[1][0], "2026")
        self.assertEqual(len(zeilen), 2)

    def test_zwei_exporte_sind_identisch(self):
        make_post(kategorie=self.kategorie)

        erster = self.client.get(EXPORT).content
        zweiter = self.client.get(EXPORT).content

        self.assertEqual(erster, zweiter)

    def test_jahr_aus_der_querystring(self):
        make_post(kategorie=self.kategorie, jahr=2027)

        response = self.client.get(EXPORT, {"jahr": "2027"})

        self.assertIn("beitraege_2027.csv", response["Content-Disposition"])

    def test_mitglied_erhaelt_403_und_keine_datei(self):
        self.client.force_login(make_user("mitglied", "mitglied"))
        make_post(kategorie=self.kategorie)

        response = self.client.get(EXPORT)

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("text/csv", response.get("Content-Type", ""))
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `docker compose exec -T app pytest dues/tests/test_views_mahnung.py -q`
Expected: FAIL — 404 auf `/beitraege/mahnungen/` (Routen fehlen)

- [ ] **Step 3: Drei Views an `dues/views.py` anhängen**

Zuerst die Importliste oben ergänzen:

```python
import csv

from .export import beitragszeilen
from .mahnung import mahnungen_setzen, mahnstufe_text, offene_posten
```

und dann ans Dateiende:

```python
def _mahnungen_und_jahr(jahr):
    return f"{reverse('dues:mahnliste')}?jahr={jahr}"


@role_required(ADMIN_GROUP)
def mahnliste(request):
    """Offene Beiträge eines Jahres — Grundlage für Mahnung und Brief (PRD M2.5)."""
    jahr = _parse_jahr(request.GET.get("jahr"))
    if jahr is None:
        if request.GET.get("jahr") is not None:
            return redirect("dues:mahnliste")
        jahr = _aktives_jahr()

    zeilen = offene_posten(jahr)
    return render(
        request,
        "dues/mahnliste.html",
        {
            "jahr": jahr,
            "jahre": _jahre(),
            "zeilen": zeilen,
            "summe_offen": sum((z["offen"] for z in zeilen), Decimal("0.00")),
        },
    )


@role_required(ADMIN_GROUP)
@require_POST
def mahnung_setzen(request, pk):
    """Setzt die nächste Mahnung für einen Beitragsposten (PRD M2.5).

    Die Prüfungen liegen in `dues.mahnung.mahnungen_setzen`; hier wird nur
    übersetzt und eine verständliche Meldung gezeigt.
    """
    post = get_object_or_404(
        FeePost.objects.select_related("member", "kategorie"), pk=pk
    )
    stufe = request.POST.get("stufe", "")
    stufe = int(stufe) if stufe in ("1", "2") else None
    datum = _datum(request.POST.get("datum"))
    frist = _datum_leer(request.POST.get("frist"))

    try:
        mahnung = mahnungen_setzen(
            post,
            stufe,
            datum,
            frist=frist,
            benutzer=request.user,
            notiz=request.POST.get("notiz", ""),
        )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect(_mahnungen_und_jahr(post.jahr))

    messages.success(
        request,
        f"{mahnstufe_text(mahnung.stufe)} für {post.member} gesetzt "
        f"(Datum {mahnung.datum.strftime('%d.%m.%Y')}).",
    )
    return redirect(_mahnungen_und_jahr(post.jahr))


@role_required(ADMIN_GROUP)
def beitraege_export(request):
    """CSV der Jahresbeiträge (PRD M2.5).

    Kein Audit-Eintrag: der Export ist eine Leseaktion. Protokolliert wird er
    laut PRD mit dem Auskunfts-Export in T23, dort mit Person und Zweck.
    """
    jahr = _parse_jahr(request.GET.get("jahr")) or _aktives_jahr()
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="beitraege_{jahr}.csv"'
    response.write("\ufeff")  # BOM für Excel
    writer = csv.writer(response, delimiter=";")
    for zeile in beitragszeilen(jahr):
        writer.writerow(zeile)
    return response
```

Dazu zwei Helfer — `_datum` in `dues/views.py` liefert bei leerem Feld das heutige
Datum, für die optionale Frist braucht es „leer":

```python
def _datum_leer(roh):
    """Optionales Datum aus dem Formular: leer bleibt leer (die Frist ist freiwillig)."""
    if not str(roh or "").strip():
        return None
    return _datum(roh)
```

und der fehlende `HttpResponse`-Import oben:

```python
from django.http import HttpResponse
```

- [ ] **Step 4: Routen ergänzen** — in `dues/urls.py` ans `urlpatterns` anhängen:

```python
    path("beitraege/mahnungen/", views.mahnliste, name="mahnliste"),
    path(
        "beitraege/mahnungen/<int:pk>/setzen/",
        views.mahnung_setzen,
        name="mahnung_setzen",
    ),
    path("beitraege/export.csv", views.beitraege_export, name="beitraege_export"),
```

- [ ] **Step 5: Nav-Eintrag** — in `core/context_processors.py` in `NAV_ITEMS` nach `("dues:zahlungsliste", "Zahlungen", {"admin"}),` einfügen:

```python
    ("dues:mahnliste", "Mahnungen", {"admin"}),
```

- [ ] **Step 6: `dues/templates/dues/mahnliste.html` schreiben**

```html
{% extends "base.html" %}

{% block title %}Mahnungen — Schachverein{% endblock %}

{% block content %}
<h1>Offene Beiträge {{ jahr }}</h1>

<form class="filter-bar" method="get">
  <label for="jahr">Jahr</label>
  <select id="jahr" name="jahr">
    {% for jahr_auswahl in jahre %}
      <option value="{{ jahr_auswahl }}" {% if jahr_auswahl == jahr %}selected{% endif %}>{{ jahr_auswahl }}</option>
    {% endfor %}
  </select>
  <button type="submit">Anzeigen</button>
  <a class="button-link" href="{% url 'dues:beitraege_export' %}?jahr={{ jahr }}">CSV-Export {{ jahr }}</a>
</form>

<p class="tile-hinweis">
  {{ zeilen|length }} offene(r) Posten, zusammen
  <strong>{{ summe_offen }}&nbsp;€</strong>.
  <a href="{% url 'dues:posten_liste' %}?jahr={{ jahr }}">Alle Beitragsposten {{ jahr }}</a>
</p>

<div class="table-wrap">
  <table class="data">
    <thead>
      <tr>
        <th>Mitglied</th>
        <th>Kategorie</th>
        <th>Beitrag</th>
        <th>Bezahlt</th>
        <th>Offen</th>
        <th>Status</th>
        <th>Mahnungen</th>
        <th>Aktion</th>
      </tr>
    </thead>
    <tbody>
      {% for zeile in zeilen %}
        <tr>
          <td><a href="{% url 'members:member_detail' zeile.member.pk %}">{{ zeile.member }}</a></td>
          <td>{{ zeile.kategorie }}</td>
          <td>{{ zeile.betrag }}&nbsp;€</td>
          <td>{{ zeile.bezahlt }}&nbsp;€</td>
          <td><strong>{{ zeile.offen }}&nbsp;€</strong></td>
          <td><span class="badge {{ zeile.status_klasse }}">{{ zeile.status_label }}</span></td>
          <td>
            {% for mahnung in zeile.mahnungen %}
              {{ mahnung.get_stufe_display }} am {{ mahnung.datum|date:"d.m.Y" }}{% if not forloop.last %}, {% endif %}
            {% empty %}
              keine
            {% endfor %}
          </td>
          <td>
            <a class="button-link" href="{% url 'dues:mahnbrief' pk=zeile.post.pk %}">Mahnbrief</a>
            {% if zeile.stufe %}
              <form class="inline-form" method="post" action="{% url 'dues:mahnung_setzen' pk=zeile.post.pk %}">
                {% csrf_token %}
                <input type="hidden" name="stufe" value="{{ zeile.stufe }}">
                <label class="sr-only" for="datum-{{ zeile.post.pk }}">Mahndatum</label>
                <input type="date" id="datum-{{ zeile.post.pk }}" name="datum" value="{{ jahr }}-03-01" required>
                <label class="sr-only" for="frist-{{ zeile.post.pk }}">Frist</label>
                <input type="date" id="frist-{{ zeile.post.pk }}" name="frist">
                <button type="submit">{{ zeile.stufe_text }} setzen</button>
              </form>
            {% else %}
              <span class="tile-hinweis">Stufen ausgeschöpft</span>
            {% endif %}
          </td>
        </tr>
      {% empty %}
        <tr>
          <td colspan="8">Für dieses Jahr wurden keine Beiträge gebucht.</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<p class="tile-hinweis">
  Bezahlte Posten stehen nicht in dieser Liste — der offene Betrag entscheidet.
  Beim Setzen prüft die Anwendung, ob der Posten noch offen ist und ob die
  Stufe die nächste ist.
</p>
{% endblock %}
```

- [ ] **Step 7: Tests laufen lassen, Restfehler einordnen**

Run: `docker compose exec -T app pytest dues/tests/test_views_mahnung.py -q`
Expected: alle passed **außer** den Tests, die `dues:mahnbrief` benutzen (dieser Pfad ist Task 7). Fehlt noch `sr-only` in der Tailwind-Version, `class="sr-only"` durch ein leeres `aria-label` am Feld ersetzen.

- [ ] **Step 8: Nav-Test ergänzen** — in `core/tests/test_nav.py` ans Dateiende, im Muster der beiden `zahlungen`-Tests:

```python
    def test_admin_sees_mahnungen(self):
        make_user("admin1", "admin")
        self.client.login(username="admin1", password="x")
        response = self.client.get("/")
        self.assertContains(response, 'href="/beitraege/mahnungen/"')

    def test_member_sees_no_mahnungen(self):
        """Negativtest: das Mahnwesen bleibt Vorstandssache (PRD §3.8)."""
        make_user("mitglied1", "mitglied")
        self.client.login(username="mitglied1", password="x")
        response = self.client.get("/")
        self.assertNotContains(response, 'href="/beitraege/mahnungen/"')
```

- [ ] **Step 9: Tests laufen lassen, Erfolg bestätigen**

Run: `docker compose exec -T app pytest dues core -q`
Expected: alle passed

- [ ] **Step 10: Commit**

```powershell
git add dues/views.py dues/urls.py dues/templates/dues/mahnliste.html core/context_processors.py core/tests/test_nav.py dues/tests/test_views_mahnung.py
git commit -m "T10: Mahnliste, Mahnformular und CSV-Export der Beitraege"
```

---

### Task 7: Druckbarer Mahnbrief

**Files:**
- Modify: `dues/tests/test_views_mahnung.py` (Klasse `MahnbriefTests` anhängen)
- Create: `dues/templates/dues/mahnbrief.html`
- Modify: `dues/views.py` (`mahnbrief`)
- Modify: `dues/urls.py` (Route)

**Interfaces:**
- Consumes: `dues.mahnung.posten_fuer_brief`, `dues.mahnung.naechste_stufe`, `dues.mahnung.mahnstufe_text`, `verein.models.Vereinsdaten.aktuell`
- Produces: URL `dues:mahnbrief` (`/beitraege/mahnungen/<pk>/`) — Kontext `post`, `posten` (Liste von Dicts), `summe_offen` (Decimal), `verein` (`Vereinsdaten`), `stufe` (int), `stufe_text` (str), `naechste_frist` (date|None: die Frist der gesetzten Mahnung, falls vorhanden)

- [ ] **Step 1: Failing tests anhängen** — ans Ende von `dues/tests/test_views_mahnung.py`:

```python
class MahnbriefTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

        self.post = make_post(kategorie=self.kategorie)
        self.verein = Vereinsdaten.objects.create(
            name="Schachverein Example",
            strasse="Turnierweg 3",
            plz="12345",
            ort="Musterstadt",
            kassierer="R. Kaiser",
            zahlungshinweis="Bitte per Überweisung ausgleichen.",
            zahlungsziel="Verwendungszweck: Nachname, Vorname, Jahr",
        )

    def url(self, post=None):
        return reverse("dues:mahnbrief", args=[(post or self.post).pk])

    def test_brief_zeigt_mitglied_und_summe(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meier, Anna")
        self.assertContains(response, "90,00")
        self.assertEqual(response.context["summe_offen"], Decimal("90.00"))

    def test_brief_zeigt_die_offenen_posten(self):
        response = self.client.get(self.url())

        self.assertContains(response, "Erwachsene")
        self.assertEqual(len(response.context["posten"]), 1)

    def test_brief_zeigt_die_vereinsdaten(self):
        response = self.client.get(self.url())

        self.assertContains(response, "Schachverein Example")
        self.assertContains(response, "Turnierweg 3")
        self.assertContains(response, "R. Kaiser")
        self.assertContains(response, "Verwendungszweck")

    def test_brief_ist_eigenstaendiges_dokument_mit_druckknopf(self):
        response = self.client.get(self.url())

        self.assertNotIn("site-header", response.content.decode())
        self.assertContains(response, "window.print()")
        self.assertContains(response, "@media print")

    def test_brief_nennt_die_naechste_stufe(self):
        Mahnung.objects.create(post=self.post, stufe=1, datum=date(2026, 3, 1))

        response = self.client.get(self.url())

        self.assertContains(response, "2. Mahnung")

    def test_brief_nennt_die_frist_der_gesetzten_mahnung(self):
        Mahnung.objects.create(
            post=self.post, stufe=1, datum=date(2026, 3, 1), frist=date(2026, 4, 15)
        )

        response = self.client.get(self.url())

        self.assertContains(response, "15.04.2026")

    def test_interne_notiz_erscheint_nicht_im_brief(self):
        Mahnung.objects.create(
            post=self.post,
            stufe=1,
            datum=date(2026, 3, 1),
            notiz="Rückruf am Dienstag vereinbart",
        )

        response = self.client.get(self.url())

        self.assertNotContains(response, "Rückruf am Dienstag")

    def test_bezahlter_posten_ergibt_404(self):
        zahle(self.post)

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 404)

    def test_unbekannter_posten_ergibt_404(self):
        response = self.client.get(reverse("dues:mahnbrief", args=[999999]))

        self.assertEqual(response.status_code, 404)

    def test_mitglied_erhaelt_403(self):
        self.client.force_login(make_user("mitglied", "mitglied"))

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 403)

    def test_kapitaen_erhaelt_403(self):
        self.client.force_login(make_user("kapitaen", "kapitaen"))

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 403)

    def test_brief_ohne_verein_daten_bricht_nicht_ab(self):
        Vereinsdaten.objects.all().delete()

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 200)
```

Zusätzlich oben in der Datei importieren:

```python
from verein.models import Vereinsdaten
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `docker compose exec -T app pytest dues/tests/test_views_mahnung.py -q -k Mahnbrief`
Expected: FAIL — `NoReverseMatch`/`404`, Route und View fehlen

- [ ] **Step 3: View anhängen** — in `dues/views.py` den Import ergänzen:

```python
from verein.models import Vereinsdaten
```

und die View:

```python
@role_required(ADMIN_GROUP)
def mahnbrief(request, pk):
    """Druckbarer Mahnbrief für einen Beitragsposten (PRD M2.5).

    Der Brief entsteht aus dem **offenen** Posten, nicht aus einer gespeicherten
    Mahnung: so ist er nach dem Ausdrucken aktuell, ohne dass er neu erzeugt
    werden muss. 404, wenn es nichts Offenes mehr gibt — ein leerer Brief geht
    nicht in die Post.
    """
    post = get_object_or_404(
        FeePost.objects.select_related("member", "kategorie"), pk=pk
    )
    posten, summe_offen = posten_fuer_brief(post.jahr, post.member)
    if not posten:
        raise Http404("Für diesen Beitragsposten ist nichts mehr offen.")

    # Die Frist der gesetzten Mahnung gilt für den Brief; ohne Mahnung bleibt
    # sie offen, damit der Vorstand sie per Papier festlegen kann.
    letzte = post.mahnungen.order_by("-datum", "-pk").first()
    return render(
        request,
        "dues/mahnbrief.html",
        {
            "post": post,
            "posten": posten,
            "summe_offen": summe_offen,
            "verein": Vereinsdaten.aktuell(),
            "stufe": naechste_stufe(post),
            "stufe_text": mahnstufe_text(naechste_stufe(post)),
            "naechste_frist": letzte.frist if letzte else None,
            "heute": timezone.localdate(),
        },
    )
```

Dazu den `Http404`-Import:

```python
from django.http import Http404, HttpResponse
```

und `naechste_stufe`/`posten_fuer_brief` in der `dues.mahnung`-Importliste ergänzen.

- [ ] **Step 4: Route ergänzen** — in `dues/urls.py` **vor** der Setzen-Route (Reihenfolge ist bei `int:pk` nicht entscheidend, aber lesbar):

```python
    path("beitraege/mahnungen/<int:pk>/", views.mahnbrief, name="mahnbrief"),
```

- [ ] **Step 5: `dues/templates/dues/mahnbrief.html` schreiben**

Eigenständiges Dokument, kein `base.html` — der Brief soll ohne Navigation und
ohne Fußzeile drucken. Das Print-Stylesheet steht im `<style>`-Block, weil es
nur hier gilt.

```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mahnbrief {{ post.jahr }} — {{ post.member }}</title>
  <style>
    :root { color-scheme: light; }
    body {
      font-family: Georgia, "Times New Roman", serif;
      color: #1a1a2e;
      max-width: 42rem;
      margin: 2rem auto;
      padding: 0 1.25rem;
      line-height: 1.5;
    }
    .absender { font-size: 0.9rem; color: #444; }
    .empfaenger { margin: 2rem 0; }
    h1 { font-size: 1.2rem; }
    table { width: 100%; border-collapse: collapse; margin: 1.5rem 0; }
    th, td { border-bottom: 1px solid #ccc; padding: 0.4rem 0.2rem; text-align: left; }
    th.numerisch, td.numerisch { text-align: right; }
    tfoot td { font-weight: bold; border-top: 2px solid #1a1a2e; }
    .hinweis { background: #f7f7f9; padding: 0.75rem 1rem; margin: 1.5rem 0; }
    .frist { font-weight: bold; }
    .gruss { margin-top: 2.5rem; }
    .werkzeug { margin-bottom: 1.5rem; }
    .werkzeug button {
      font: inherit;
      padding: 0.5rem 1rem;
      cursor: pointer;
      border: 1px solid #0f3460;
      background: #0f3460;
      color: #fff;
      border-radius: 4px;
    }
    @media print {
      .werkzeug { display: none; }
      body { margin: 0; max-width: none; }
      @page { margin: 2cm; }
    }
  </style>
</head>
<body>
  <p class="werkzeug">
    <button type="button" onclick="window.print()">Drucken / Als PDF speichern</button>
  </p>

  <p class="absender">
    <strong>{{ verein.name }}</strong><br>
    {% if verein.strasse %}{{ verein.strasse }}<br>{% endif %}
    {% if verein.plz or verein.ort %}{{ verein.plz }} {{ verein.ort }}<br>{% endif %}
    {% if verein.telefon %}Tel. {{ verein.telefon }}<br>{% endif %}
    {% if verein.email %}{{ verein.email }}{% endif %}
  </p>

  <p class="empfaenger">
    {{ post.member.vorname }} {{ post.member.nachname }}<br>
    {% if post.member.strasse %}{{ post.member.strasse }}<br>{% endif %}
    {% if post.member.plz or post.member.ort %}{{ post.member.plz }} {{ post.member.ort }}{% endif %}
  </p>

  <p>{{ heute|date:"d.m.Y" }}</p>

  <h1>{{ stufe_text }} — Beiträge {{ post.jahr }}</h1>

  <p>
    Sehr geehrte/r {{ post.member.vorname }} {{ post.member.nachname }},
  </p>

  <p>
    nach unseren Unterlagen ist für das Beitragsjahr {{ post.jahr }} noch ein
    Betrag von <strong>{{ summe_offen }}&nbsp;€</strong> offen. Wir bitten um
    Ausgleich
    {% if naechste_frist %}
      <span class="frist">bis zum {{ naechste_frist|date:"d.m.Y" }}</span>.
    {% else %}
      kurzfristig.
    {% endif %}
  </p>

  <table>
    <thead>
      <tr>
        <th>Jahr</th>
        <th>Kategorie</th>
        <th class="numerisch">Beitrag</th>
        <th class="numerisch">Bezahlt</th>
        <th class="numerisch">Offen</th>
      </tr>
    </thead>
    <tbody>
      {% for zeile in posten %}
        <tr>
          <td>{{ zeile.jahr }}</td>
          <td>{{ zeile.kategorie }}</td>
          <td class="numerisch">{{ zeile.betrag }}&nbsp;€</td>
          <td class="numerisch">{{ zeile.bezahlt }}&nbsp;€</td>
          <td class="numerisch">{{ zeile.offen }}&nbsp;€</td>
        </tr>
      {% endfor %}
    </tbody>
    <tfoot>
      <tr>
        <td colspan="4">Offener Betrag</td>
        <td class="numerisch">{{ summe_offen }}&nbsp;€</td>
      </tr>
    </tfoot>
  </table>

  {% if verein.zahlungshinweis or verein.zahlungsziel %}
    <div class="hinweis">
      {% if verein.zahlungshinweis %}<p>{{ verein.zahlungshinweis|linebreaksbr }}</p>{% endif %}
      {% if verein.zahlungsziel %}<p>{{ verein.zahlungsziel|linebreaksbr }}</p>{% endif %}
    </div>
  {% endif %}

  <p class="gruss">
    Mit freundlichen Grüßen<br>
    {% if verein.kassierer %}{{ verein.kassierer }}{% else %}{{ verein.name }}{% endif %}
  </p>
</body>
</html>
```

- [ ] **Step 6: Tests laufen lassen, Erfolg bestätigen**

Run: `docker compose exec -T app pytest dues -q`
Expected: alle passed

- [ ] **Step 7: Commit**

```powershell
git add dues/views.py dues/urls.py dues/templates/dues/mahnbrief.html dues/tests/test_views_mahnung.py
git commit -m "T10: Druckbarer Mahnbrief je Mitglied und Jahr"
```

---

### Task 8: Browser-Check, CSS-Build und Fortschrittsprotokoll

**Files:**
- Modify: `tasks/plan.md` (T10 abhaken)
- Modify: `tasks/todo.md` (T10 unter „Erledigt", „Nächste Schritte" anpassen)
- Modify: `static/css/tailwind.css` (nur falls `npm run build:css` eine Änderung erzeugt)

**Interfaces:**
- Consumes: alles aus Task 1–7
- Produces: Abnahme-Belege in `tasks/todo.md`

- [ ] **Step 1: Gesamten Testlauf im Stack**

Run: `docker compose exec -T app pytest -q`
Expected: alle passed, keine Fehler. Zahl notieren — das ist der Beleg in `todo.md`.

- [ ] **Step 2: CSS neu bauen, falls neue Tailwind-Klassen dazukamen**

Run: `npm run build:css`
Expected: Build läuft durch. Nur committen, wenn `static/css/tailwind.css` sich tatsächlich geändert hat (`git status --short`).

- [ ] **Step 3: Seed-Daten und Beitragslauf vorbereiten**

Im Django-Shell (`docker compose exec app python manage.py shell`) eine Kategorie und ein SEPA-Mandat anlegen ist **nicht** nötig — der Beitragslauf braucht nur `FeeAmount`, die aus der Seed-Migration `0002` vorhanden sind. Stattdessen im Shell nur prüfen:

```python
from dues.models import FeeAmount, FeeCategory
print(FeeAmount.objects.count(), FeeCategory.objects.count())
```

Erwartet: 8 Sätze (4 Kategorien × 2 Jahre) und 4 Kategorien.

- [ ] **Step 4: Browser-Check am laufenden Stack**

Der Stack läuft bereits (`docker compose up`). Weg durch die Oberfläche:

1. Als Admin anmelden, Beitragslauf für 2026 ausführen (`/beitraege/`).
2. Bei zwei von drei Mitgliedern über `/beitraege/zahlungen/` eine Zahlung buchen.
3. `/beitraege/mahnungen/` öffnen: genau **ein** offener Posten mit Summe sichtbar, CSV-Knopf oben.
4. Mahnformular in der Zeile ausführen (Datum wählen) → Erfolgsmeldung, Zeile zeigt „1. Mahnung am …".
5. „Mahnbrief" klicken: Brief mit Adresse, Postentabelle, Summe, Zahlungshinweis, Grußformel; Druckknopf oben; **keine** interne Notiz.
6. Auf der Mahnliste „2. Mahnung" setzen; danach verschwindet der Mahnknopf (Stufen ausgeschöpft).
7. `/beitraege/export.csv?jahr=2026` öffnen: Excel-kompatible Datei, Kopfzeile wie in `CSV_SPALTEN`, bezahlte Posten enthalten, keine Adressspalten.
8. Fenster auf 360 px und 1280 px: kein horizontaler Overflow auf Mahnliste und Brief.
9. Nav zeigt „Mahnungen" nur im Admin-Menü; mit „kapitaen" liefert die URL 403.

Wenn etwas nicht stimmt: erst den Test schreiben, der das Verhalten festhält, dann korrigieren.

- [ ] **Step 5: `tasks/plan.md` aktualisieren**

In der T10-Zeile `[ ]` → `[x]` setzen. Sonst nichts an der Datei ändern — sie ist die Statusquelle.

- [ ] **Step 6: `tasks/todo.md` aktualisieren**

In „### Phase 2: Beiträge + Dashboard" einen Eintrag **nach** T9 anhängen, im Stil der anderen:

```markdown
- **T10: Mahnwesen + Beitrags-Export** — `Mahnung` (FK `PROTECT` auf `FeePost`, Stufe 1/2, Datum, optionale Frist, interne Notiz, `unique(post, stufe)`), `Vereinsdaten` in der neuen Mini-App `verein` (genau ein Datensatz, `aktuell()` legt ihn an). Regelbasis in `dues/mahnung.py` (`naechste_stufe`, `mahnungen_setzen`, `offene_posten`, `posten_fuer_brief`) und `dues/export.py` (`CSV_SPALTEN`, `beitragszeilen`); `services.py` bleibt unverändert. Stufen werden nicht übersprungen und nicht doppelt gesetzt, ein bezahlter Posten ist nicht mahnbar (Gutschrift ebenso), jedes Setzen schreibt eine Audit-Zeile mit `member`. Bezahlte Posten fallen automatisch aus der Übersicht — es gibt bewusst **kein** Zurückziehen und **keine** Mahngebühr. UI: `/beitraege/mahnungen/` (Jahresfilter, Summenzeile, Mahnformular je Zeile, CSV-Knopf), Mahnbrief je Posten als eigenständiges druckbares HTML mit Print-Stylesheet (PDF über den Browser — keine neue Abhängigkeit), `/beitraege/export.csv` mit BOM und `;`. *Beleg:* `pytest` → **N Tests grün** (M: 8 · Services: 32 · Export: 17 · Views: 34 · verein: 6); Negativtests: 403 für „kapitaen"/„mitglied" auf Übersicht, Brief, Export **und** POST (jeweils ohne Seiteneffekt), GET auf `mahnung_setzen` → 405, übersprungene/doppelte Stufe, bezahlter Posten, unbekannter Posten 404, Brief 404 wenn nichts offen ist; Inhaltstest: CSV enthält keine Adresse, E-Mail, Telefon oder Geburtsdatum (auch nicht die anderer Mitglieder), zwei Exporte byte-identisch, Jahressumme == im Test berechnete Modellsumme. Browser-Check am laufenden Stack: Lauf 2026 → 2 von 3 gezahlt → Mahnliste zeigt 1 offenen Posten → 1. Mahnung mit Datum → Brief gedruckt → 2. Mahnung gesetzt (Button verschwindet) → CSV geprüft; 360/1280 px ohne Overflow.
  - *Nebenwirkungen:* Der CSV-Export enthält **alle** Posten des Jahres (auch bezahlte), die Mahnliste nur die offenen — zwei bewusst verschiedene Mengen, beide in `dues/` dokumentiert. Die Vereinsdaten sind die Quelle für Absender und Kontakt; T14 (Gruppemail) und T17 (News) lesen denselben Datensatz. Der Export wird **nicht** protokolliert — laut PRD erst mit T23 (Auskunfts-Export, dort mit Person und Zweck).
  - *Hinweise an Folge-Tasks:* T11 (Dashboard) nimmt offene Summe und Anzahl aus `offene_posten(jahr)`; T11b (Kassenbericht) legt `dues/kassenbericht.py` neben `mahnung.py` und `export.py` an. Mahnbrief serverseitig als PDF und eine Frist ohne Mahnung bleiben bewusst offen (Browser druckt, der Vorstand legt die Frist auf Papier fest).
```

`(N Tests grün)` sowie `M: 8 · Services: 32 · Export: 17 · Views: 34` mit den **tatsächlichen** Zahlen aus Task 8 Schritt 1 und den Testdateien ersetzen.

- [ ] **Step 7: „Nächste Schritte" in `todo.md` aktualisieren**

T10 aus der Liste streichen. Neue Reihenfolge:

```markdown
1. [T11](plan.md) Dashboard-Erweiterung offene Beiträge
2. [T11b](plan.md) Kassenbuch-Sicht Beiträge (Jahresübersicht) — *neu, schließt M2.6*
3. [T12](plan.md) Zugriffsprotokoll Detailansicht — *hängt nur an T5, kann vor T11 gemacht werden*
4. **Checkpoint 2** — Beitragslauf-Jahr komplett (Lauf → Zahlung → Mahnung → Export), Dashboard zeigt echte Zahlen, Review mit Mensch
```

- [ ] **Step 8: Commit**

```powershell
git add tasks/plan.md tasks/todo.md static/css/tailwind.css
git commit -m "todo.md: T10 abgeschlossen, Fortschrittsprotokoll fortgeschrieben"
```

Falls `static/css/tailwind.css` unverändert ist, kommt die Datei nicht ins `git add` — `git add` mit einer unveränderten Datei ist harmlos, der Commit enthält sie dann aber nicht.

---

## Selbstprüfung (gegen die Spezifikation)

| Abschnitt der Spec | Task |
|---|---|
| 4.1 `Mahnung` (Felder, Constraint, Ordering) | Task 2 |
| 4.2 `verein.Vereinsdaten` (Felder, `aktuell()`, `pk=1`, Admin) | Task 1 |
| 5.1–5.2 Stufenfolge und die drei Prüfungen inkl. `IntegrityError`-Fang | Task 3 |
| 5.3 `offene_posten` (eine Abfrage, Filter, Stufen, `assertNumQueries`) | Task 4 |
| 5.4 `posten_fuer_brief` | Task 4 |
| 5.5 `mahnstufe_text` | Task 3 |
| 6 `CSV_SPALTEN`, `beitragszeilen`, Inhaltstest | Task 5 |
| 7.1 Routen und Nav | Task 6, Task 7 |
| 7.2 Views inkl. 405/404/403 und kein Audit beim Export | Task 6, Task 7 |
| 7.3 Templates inkl. eigenständigem Brief und Print-Stylesheet | Task 6, Task 7 |
| 8 Testumfang inkl. Nav-Test | Task 1–7, Task 8 Schritt 8 |
| Abnahme laut `plan.md` (druckbar, CSV vollständig, 403, nur erlaubte Felder, zweiter Export identisch) | Task 8 Schritt 4 |
