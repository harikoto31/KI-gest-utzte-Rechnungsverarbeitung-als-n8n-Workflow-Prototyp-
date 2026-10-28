"""
Erzeugt 4 Fake-Rechnungen als PDF für den n8n-Prototyp.
ALLE Daten sind erfunden. Keine echten Firmen, keine echten Personen.
"""
import os
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def rechnungstext(daten):
    """Baut aus einem dict den kompletten Rechnungstext als EINEN String.
    Beide PDF-Arten (Text und Scan) nutzen diese Funktion, damit der
    Inhalt garantiert gleich ist und nichts doppelt gepflegt werden muss."""

    # Positionen: aus einer Liste von dicts wird eine Zeile pro Position.
    # "\n".join(...) verbindet alle Zeilen mit Zeilenumbruch dazwischen.
    positionen = "\n".join(
        f"  {p['menge']} x {p['bezeichnung']}: {p['betrag']} EUR"
        for p in daten["positionen"]
    )

    # Optionaler Zusatz oben (z. B. "ZWEITSCHRIFT" beim Duplikat).
    # .get() liefert None, wenn der Schlüssel fehlt → dann leerer String.
    zusatz = f"*** {daten['zusatz']} ***\n\n" if daten.get("zusatz") else ""

    # Bewusst KEINE Kostenstelle auf der Rechnung: die ist ein internes
    # Konzept des Empfängers. Nur die Bestellnummer könnte darauf hinweisen.
    return f"""{zusatz}{daten['lieferant']}
{daten['strasse']}
{daten['ort']}
USt-IdNr.: {daten['ust_id']}

Rechnung an:
Beispiel Handels GmbH
Musterweg 5
60311 Frankfurt am Main

RECHNUNG

Rechnungsnummer: {daten['rechnungsnr']}
Rechnungsdatum: {daten['datum']}
Ihre Bestellnummer: {daten['bestellnr']}

Positionen:
{positionen}

Nettobetrag: {daten['netto']} EUR
USt 19 %: {daten['ust']} EUR
Gesamtbetrag: {daten['brutto']} EUR

Zahlbar innerhalb von 14 Tagen ohne Abzug.
Bankverbindung: Musterbank, IBAN: {daten['iban']}
"""


def erzeuge_text_pdf(daten, dateiname):
    """Normales PDF: Text ist eine echte Textebene, also markier- und auslesbar."""
    pdf = FPDF()
    pdf.add_page()
    # Helvetica ist eine eingebaute Schrift: kann äöüß, aber KEIN €-Zeichen
    # und keine typografischen Striche (–). Deshalb überall "EUR" und "-".
    pdf.set_font("Helvetica", size=11)
    # multi_cell(Breite, Zeilenhöhe, Text): Breite 0 = bis zum rechten Rand.
    # Bricht bei jedem \n im Text eine neue Zeile um.
    pdf.multi_cell(0, 6, rechnungstext(daten))
    pdf.output(dateiname)
    print(f"erstellt: {dateiname}")


def erzeuge_scan_pdf(daten, dateiname):
    """'Gescanntes' PDF: Der Text existiert NUR als Pixel in einem Bild.
    Für ein Programm ist darin kein einziger Buchstabe lesbar."""

    # 1. Weißes Bild in A4-Proportion (ca. 150 dpi: 1240 x 1754 Pixel)
    bild = Image.new("RGB", (1240, 1754), "white")
    zeichner = ImageDraw.Draw(bild)

    # 2. Schrift laden. load_default(size=...) gibt es erst in neueren
    #    Pillow-Versionen, daher Fallback auf die kleine Standardschrift.
    try:
        schrift = ImageFont.load_default(size=28)
    except TypeError:
        schrift = ImageFont.load_default()

    # 3. Text als Pixel auf das Bild malen
    zeichner.multiline_text((80, 80), rechnungstext(daten), fill="black",
                            font=schrift, spacing=8)

    # 4. Scan-Look: leicht schief und leicht unscharf, wie aus einem Kopierer
    bild = bild.rotate(0.8, fillcolor="white")
    bild = bild.filter(ImageFilter.GaussianBlur(1))

    # 5. Bild zwischenspeichern und als einzigen Inhalt ins PDF setzen
    png_name = dateiname.replace(".pdf", ".png")
    bild.save(png_name)

    pdf = FPDF()
    pdf.add_page()
    # A4 ist 210 mm breit: 10 mm Rand links, 190 mm Bildbreite.
    # Die Höhe berechnet fpdf2 automatisch aus dem Seitenverhältnis.
    pdf.image(png_name, x=10, y=10, w=190)
    pdf.output(dateiname)

    os.remove(png_name)   # Zwischendatei wieder löschen
    print(f"erstellt: {dateiname}")


# ---------------------------------------------------------------------------
# Hauptteil: Grunddaten einmal definieren, Varianten davon ableiten
# ---------------------------------------------------------------------------
basis = {
    "lieferant": "Muster Bürobedarf GmbH",
    "strasse": "Beispielstraße 1",
    "ort": "64283 Darmstadt",
    "ust_id": "DE123456789",
    "iban": "DE89 3704 0044 0532 0130 00",   # bekannte Beispiel-IBAN
    "rechnungsnr": "R-2026-0101",
    "datum": "20.10.2026",
    "bestellnr": "B-4711",
    "positionen": [
        {"menge": 10, "bezeichnung": "Kopierpapier A4, Karton", "betrag": "400,00"},
        {"menge": 4,  "bezeichnung": "Toner schwarz",            "betrag": "600,00"},
    ],
    "netto": "1.000,00",
    "ust": "190,00",
    "brutto": "1.190,00",
}

# {**basis, ...} = neues dict mit allen Werten aus basis,
# nur die genannten Schlüssel werden überschrieben. basis selbst bleibt unverändert.

# 1. korrekt → grün
erzeuge_text_pdf(basis, "rechnung_ok.pdf")

# 2. Rechenfehler: 1.000 + 190 ≠ 1.290 (eigene Rechnungsnummer, sonst wäre es auch ein Duplikat)
erzeuge_text_pdf({**basis, "rechnungsnr": "R-2026-0103", "brutto": "1.290,00"},
                 "rechnung_rechenfehler.pdf")

# 3. Duplikat: GLEICHE Rechnungsnummer wie Nr. 1, aber mit Zusatzzeile.
#    → Datei ist nicht identisch, ein Hash-Vergleich würde es NICHT erkennen
erzeuge_text_pdf({**basis, "zusatz": "ZWEITSCHRIFT"}, "rechnung_duplikat.pdf")

# 4. Scan: eigene Rechnungsnummer, Text nur als Bild
erzeuge_scan_pdf({**basis, "rechnungsnr": "R-2026-0104"}, "rechnung_scan.pdf")