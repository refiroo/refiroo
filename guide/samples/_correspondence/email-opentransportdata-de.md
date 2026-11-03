**An:** opentransportdata.swiss (Kontaktadresse oder -formular auf opentransportdata.swiss)

**Betreff:** Nutzung eines datierten Auszugs der Dienststellen-Daten (Didok) in einer Open-Source-Dokumentation

Sehr geehrtes Team von opentransportdata.swiss

Ich entwickle refiroo, eine Open-Source-Anwendung zur Verwaltung von Referenzdaten (Lizenz: AGPL-3.0).
Wir schreiben derzeit das Benutzerhandbuch und möchten einen Teil des Datensatzes «Dienststellen
(Didok)» als durchgehendes Beispiel verwenden, weil er ein klarer, realer Fall von Codes,
Gültigkeitsdaten und mehrsprachigen Namen ist.

Was wir verwenden möchten:
- Die Dienststellen des Kantons Graubünden: rund 2400 Datensätze mit UIC-Nummer, SLOID, Bezeichnung,
  Abkürzung, Gültigkeitszeitraum, Kanton, Bezirk und Gemeinde, Verkehrsmittel und Betreiber.
- Einen Auszug mit Stand 2. November 2026, abgerufen über die API von data.sbb.ch.

Wie wir sie verwenden möchten:
- Als Beispieldaten im Handbuch, das als öffentliche Website veröffentlicht und von der Anwendung selbst
  bereitgestellt wird.
- Als Beispieldateien in unserem öffentlichen Quellcode-Repository und geladen in eine
  Demonstrationsinstanz, die sich mit Docker starten lässt.
- Jede Kopie trägt den Vermerk «Quelle: opentransportdata.swiss, Dienststellen (Didok), Bundesamt für
  Verkehr / SBB, Stand 2026-11-02» mit einem Link zum Datensatz.
- Das Repository enthält zudem ein Skript, das die aktuellen Daten herunterlädt, sodass Nutzerinnen und
  Nutzer den Auszug durch aktuelle Daten ersetzen können.

Unsere Frage betrifft die Bestimmung in Ihren Nutzungsbedingungen, wonach Daten in derselben Frequenz
wie die Rohdaten zu aktualisieren sind. Gilt diese Bestimmung für einen klar datierten Auszug, der
ausschliesslich als Beispieldaten in einer Dokumentation dient? Falls ja: Würde ein datierter Auszug
zusammen mit dem Aktualisierungsskript ihr genügen? Ausserdem wären wir dankbar für einen Hinweis, ob
unser Quellenvermerk korrekt ist und ob weitere Anforderungen bestehen.

Das Projekt: [Link zum Repository]

Vielen Dank für die Veröffentlichung dieser Daten und für Ihre Unterstützung.

Freundliche Grüsse
Krisztian Toth
