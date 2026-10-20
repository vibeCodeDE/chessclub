"""Kleine Helfer für Views: Paginierung, AJAX-Antworten, Summen."""

from decimal import Decimal

from django.core.paginator import Paginator
from django.http import JsonResponse


def paginate(queryset, request, per_page=20):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get("seite") or 1)


def ok(**daten):
    return JsonResponse({"ok": True, **daten})


def fehler(nachricht, status=400, **daten):
    return JsonResponse({"ok": False, "message": nachricht, **daten}, status=status)


def euro(betrag):
    if betrag is None:
        betrag = Decimal("0.00")
    return f"{betrag:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def ja_nein(wert):
    return "Ja" if wert else "Nein"


def is_ajax(request):
    return request.headers.get("x-requested-with") == "fetch" or "application/json" in request.headers.get(
        "accept", ""
    )


def sanitize_csv(value):
    """Verhindert CSV Formula Injection (CWE-1236 / SEC-06).

    Wenn ein Textfeld mit =, +, -, @, Tab oder Return beginnt,
    stellt ein vorangestelltes Hochkomma (') sicher, dass Tabellenprogramme
    (Excel, Calc) den Inhalt als Text und nicht als Formel interpretieren.
    """
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text
