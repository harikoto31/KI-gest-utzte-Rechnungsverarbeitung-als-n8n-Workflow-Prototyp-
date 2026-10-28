"""
Prüf-Node "Rechnung bewerten" (n8n Code-Node, Python)

Kontrolliert die von der KI extrahierten Rechnungswerte mit festen Regeln
und vergibt jeder Rechnung einen Status mit lesbarer Begründung:

    rot   – harte Fehler, darf so nicht ins ERP
    gelb  – Unsicherheiten, ein Mensch soll draufschauen
    scan  – alle Regeln erfüllt, aber Werte stammen aus OCR (Bestätigung nötig)
    gruen – alle Regeln erfüllt

Hinweis: Dieser Code läuft im n8n Code-Node (Modus "Run Once for All Items").
`_items` stellt n8n bereit, und das `return` am Ende ist dort erlaubt.
Als eigenständiges Python-Skript ist die Datei nicht direkt ausführbar.
"""

# --------------------------------------------------------------------------
# Simulierte Stammdaten (im Echtbetrieb aus dem ERP). Bewusste Annahme.
# --------------------------------------------------------------------------
LIEFERANTEN = {
    # USt-ID → bekannter Lieferant mit hinterlegter IBAN
    "DE123456789": {"name": "Muster Bürobedarf GmbH", "iban": "DE89370400440532013000"},
}
BESTELLUNGEN = {
    # Bestellnummer → Kostenstelle (so wird die Kostenstelle ermittelt, nicht geraten)
    "B-4711": "4100",
}
KOSTENSTELLEN = {
    # Kostenstelle → Bezeichnung + wer freigeben muss
    "4100": {"bezeichnung": "Verwaltung", "freigabe_an": "leitung.verwaltung@example.com"},
}


def ist_zahl(x):
    # bool ist in Python eine Unterklasse von int, deshalb ausschließen
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def normalisiere(s):
    # "DE89 3704 ..." und "de893704..." gleich behandeln
    return s.replace(" ", "").upper() if isinstance(s, str) else s


for item in _items:
    j = item["json"]
    r = j.get("output") or {}   # die vom LLM extrahierten Felder

    fehler = []     # harte Probleme → rot
    hinweise = []   # Unsicherheiten → gelb

    # 0. Ist das überhaupt eine Rechnung?
    if r.get("dokumenttyp") != "Rechnung":
        fehler.append(f"Kein Rechnungsdokument: als '{r.get('dokumenttyp')}' erkannt")

    # 1. Pflichtfelder
    for feld, name in [("rechnungsnr", "Rechnungsnummer"),
                       ("lieferant_name", "Lieferant"),
                       ("rechnungsdatum", "Rechnungsdatum")]:
        if r.get(feld) in (None, ""):
            fehler.append(f"{name} fehlt")

    # 2. Beträge: erst Typ prüfen, dann rechnen (kein TypeError möglich)
    netto, ust, brutto = r.get("netto"), r.get("ust"), r.get("brutto")
    if not all(ist_zahl(x) for x in (netto, ust, brutto)):
        fehler.append("Netto, USt oder Brutto nicht als Zahl erkannt")
    elif abs(netto + ust - brutto) >= 0.01:
        fehler.append(f"Summe stimmt nicht: {netto} + {ust} ergibt nicht {brutto}")

    # 3. Duplikat: Jede Journal-Zeile hat eine id, die LLM-Ausgabe nicht.
    #    Kam beim Merge eine id dazu, gab es einen Treffer im Journal.
    if j.get("id") is not None:
        fehler.append("Duplikat: Diese Rechnungsnummer dieses Lieferanten wurde bereits importiert")

    # 4. Lieferant über die USt-ID (eindeutig), IBAN gegen Stamm (Betrugsschutz)
    ust_id = normalisiere(r.get("lieferant_ust_id"))
    iban = normalisiere(r.get("iban"))
    stamm = LIEFERANTEN.get(ust_id)
    if stamm is None:
        hinweise.append("Unbekannter Lieferant: USt-ID nicht im Lieferantenstamm")
    elif iban != stamm["iban"]:
        fehler.append("IBAN weicht vom Lieferantenstamm ab, möglicher Betrugsversuch")

    # 5. Kostenstelle über die Bestellung, dann verantwortliche Person
    kostenstelle = BESTELLUNGEN.get(r.get("bestellnr"))
    freigabe_an = None
    if kostenstelle is None:
        hinweise.append("Kostenstelle nicht ermittelbar: keine bekannte Bestellnummer")
    else:
        kst = KOSTENSTELLEN.get(kostenstelle)
        if kst is None:
            hinweise.append(f"Keine verantwortliche Person für Kostenstelle {kostenstelle}")
        else:
            freigabe_an = kst["freigabe_an"]

    # 6. Status: rot schlägt gelb, gelb schlägt scan, scan schlägt grün
    if fehler:
        status = "rot"
    elif hinweise:
        status = "gelb"
    elif j.get("quelle") == "scan":
        status = "scan"      # alle Regeln ok, aber Werte aus OCR → Kollegin bestätigt
    else:
        status = "gruen"

    # Item durch ein flaches, sauberes dict ersetzen
    item["json"] = {
        **r,
        "lieferant_ust_id": ust_id,
        "iban": iban,
        "kostenstelle": kostenstelle,
        "freigabe_an": freigabe_an,
        "quelle": j.get("quelle"),
        "status": status,
        "fehler": fehler,
        "hinweise": hinweise,
    }

#return items 
""" in n8n ist das `return` am Ende erlaubt, in einem eigenständigen Python-Skript nicht. """