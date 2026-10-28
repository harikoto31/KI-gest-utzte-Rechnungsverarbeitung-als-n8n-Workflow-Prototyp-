# KI-gestützte Rechnungsverarbeitung mit n8n

Prototyp, der die manuelle Erfassung von Eingangsrechnungen automatisiert: vom PDF-Eingang über Prüfung und Freigabe bis zur CSV-Importdatei für ein ERP-System.

**Kernidee:** KI nur dort, wo sie nötig ist. Ein Sprachmodell macht aus dem Rechnungstext strukturierte Daten, feste Regeln prüfen das Ergebnis, und Menschen entscheiden über die Freigabe.

![Workflow](docs/screenshots/workflow-1.png)

## Ablauf

```mermaid
flowchart TD
    A[E-Mail-Eingang oder Formular-Upload] --> B{PDF-Anhang?}
    B -- nein --> Q[Prüfwarteschlange]
    B -- ja --> C[Text aus PDF extrahieren]
    C --> D{Text leer?}
    D -- ja, Scan --> E[OCR, selbst gehostet]
    E --> F
    D -- nein --> F[KI-Extraktion mit festem JSON-Schema]
    F -- Fehler --> Q
    F --> G[Abgleich mit dem Journal]
    G --> H[Prüf-Node: feste Regeln]
    H -- rot / gelb --> Q
    H -- scan --> I[Bestätigung der OCR-Werte per E-Mail]
    I -- Fehler gefunden --> Q
    I -- bestätigt --> J
    H -- grün --> J[Freigabe durch die Abteilungsleitung per E-Mail]
    J -- abgelehnt --> Q
    J -- freigegeben --> K[CSV-Importdatei für das ERP-System]
    J -- freigegeben --> L[Eintrag ins Journal]
```

**Prüfwarteschlange:** alle Rechnungen, die ein Mensch klären muss, mit Begründung. **Journal:** alle verarbeiteten Rechnungen, zur Duplikaterkennung.

Der Prüf-Node ([`code/pruef_node.py`](code/pruef_node.py)) gibt jeder Rechnung einen Status mit Begründung:

| Status | Bedeutung |
|---|---|
| 🔴 rot | z. B. Summe falsch, Duplikat, IBAN weicht ab |
| 🟡 gelb | z. B. Lieferant oder Kostenstelle unbekannt |
| 🔵 scan | alles ok, aber Werte aus OCR → Bestätigung durch einen Menschen |
| 🟢 grün | alles ok → Freigabe |

## Tech-Stack

n8n (selbst gehostet, Docker Compose) · Python · Gemini API · Stirling-PDF (OCR)

## Setup

1. In `docker/` die `.env.example` nach `.env` kopieren und ausfüllen
2. `docker compose up -d` und n8n unter `http://localhost:5678` öffnen
3. Workflows aus `workflow/` importieren und Credentials anlegen (Gemini, SMTP, Stirling-PDF)

## Grenzen

- Nur der erste Anhang pro E-Mail, nur ein Steuersatz pro Rechnung
- Stammdaten fest im Code statt aus dem ERP
- Nur mit erfundenen Testdaten getestet
