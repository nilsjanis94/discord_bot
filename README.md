# Discord Bot Dokumentation

## Moderationssystem

### Timeout
- **Befehl:** `!timeout @User/ID/Name [Minuten] [Grund]`
- **Beispiel:** `!timeout @User 10 Spam im Chat`
- **Berechtigung:** Kick Members
- **Limits:** 
  - Minimum: 1 Minute
  - Maximum: 40320 Minuten (28 Tage)

### Kick
- **Befehl:** `!kick @User/ID/Name [Grund]`
- **Beispiel:** `!kick @User Regelverstoß`
- **Berechtigung:** Kick Members

### Ban
- **Befehl:** `!ban @User/ID/Name [Grund]`
- **Beispiel:** `!ban @User Schwerer Regelverstoß`
- **Berechtigung:** Ban Members

### Verwarnungen
- **User verwarnen:** `!warn @User [Grund]`
  - Gibt einem User eine Verwarnung
  - **Berechtigung:** Kick Members

- **Verwarnungen anzeigen:** `!warnings @User`
  - Zeigt alle Verwarnungen eines Users
  - **Berechtigung:** Kick Members

- **Verwarnung löschen:** `!delwarn @User [Nummer]`
  - Löscht eine bestimmte Verwarnung
  - **Berechtigung:** Administrator

### Timeout-Verwaltung
- **Aktive Timeouts anzeigen:** `!activetimeouts`
  - Zeigt alle derzeit aktiven Timeouts auf dem Server
  - **Berechtigung:** Kick Members

- **Timeout-Historie:** `!timeouts @User`
  - Zeigt die letzten 10 Timeouts eines Users
  - **Berechtigung:** Kick Members

## Willkommenssystem

### Grundeinrichtung
- **Verifikation einrichten:** `!welcome verify #kanal @temp-rolle @verifiziert-rolle`
  - Richtet das Verifikationssystem ein
  - Kanäle mit # erwähnen
  - Rollen mit @ erwähnen
  - Discord-Autovervollständigung nutzen
  - **Berechtigung:** Administrator

- **Willkommenskanal setzen:** `!welcome channel #kanal`
  - Legt fest, wo Willkommensnachrichten erscheinen
  - **Berechtigung:** Administrator

- **Willkommensnachricht setzen:** `!welcome message <Nachricht>`
  - Definiert die Nachricht für neue Mitglieder
  - **Platzhalter:**
    - `{user}` - Username
    - `{mention}` - User Mention
    - `{server}` - Servername
    - `{count}` - Mitgliederzahl
  - **Berechtigung:** Administrator

### Konfiguration prüfen
- **Aktuelle Einstellungen:** `!checkconfig`
  - Zeigt alle aktuellen Einstellungen des Systems
  - Überprüft Kanäle und Rollen
  - **Berechtigung:** Administrator

### Features
- **Automatische Rollenvergabe**
  - Temporäre Rolle für neue Mitglieder
  - Verifizierte Rolle nach Regelbestätigung

- **Willkommensnachrichten**
  - Konfigurierbare Nachricht im Willkommenskanal
  - Automatische Erwähnung des Verifikationskanals
  - Eingebettete Nachrichten mit Avatar

- **Verifikationssystem**
  - Regelwerk mit Reaktions-Verifikation
  - Automatischer Rollentausch nach Verifikation
  - Temporärer privater Kanal für User ohne DMs

- **Benachrichtigungen**
  - DM an neue Mitglieder (falls aktiviert)
  - Fallback-System für deaktivierte DMs
  - Detaillierte Anweisungen zur Verifikation

## Hinweise
- DMs müssen vom User aktiviert sein für direkte Benachrichtigungen
- Bei deaktivierten DMs wird ein temporärer Kanal erstellt
- Der Bot benötigt entsprechende Berechtigungen
- Rollen müssen unter der Bot-Rolle sein
- Nutze die Discord-Autovervollständigung für Erwähnungen

## Fehlerbehebung
- Prüfe die Konfiguration mit `!checkconfig`
- Stelle sicher, dass der Bot die nötigen Berechtigungen hat
- Rollen müssen unter der Bot-Rolle sein
- Bei Problemen die Verifikation neu einrichten

## Updates
- Neue Befehle werden in diesem Dokument dokumentiert
- Änderungen an bestehenden Befehlen werden hier aufgeführt
- Letzte Aktualisierung: [Datum]

## Wetter-System

### Wetter abfragen
- **Aktuelles Wetter:** `!wetter [Stadt]`
  - Zeigt das aktuelle Wetter für die angegebene Stadt
  - **Beispiel:** `!wetter Berlin`
  - Zeigt:
    - Temperatur
    - Gefühlte Temperatur
    - Luftfeuchtigkeit
    - Windgeschwindigkeit
    - Wetterbeschreibung
    - Sonnenauf- und untergang

- **5-Tage Vorhersage:** `!wettervorhersage [Stadt]`
  - Zeigt die Wettervorhersage für die nächsten 5 Tage
  - **Beispiel:** `!wettervorhersage Hamburg`

### Wetter-Benachrichtigungen
- **Wetter-Updates aktivieren:** `!wetter_updates [Stadt] [Kanal]`
  - Sendet tägliche Wetterupdates in den angegebenen Kanal
  - **Berechtigung:** Administrator
  - **Beispiel:** `!wetter_updates Berlin #wetter`

## Funktionsweise

### Mod-Logs
- Alle Moderationsaktionen werden automatisch protokolliert
- Protokolliert werden:
  - Betroffener User (Name, ID)
  - Ausführender Moderator
  - Art der Aktion
  - Grund
  - Zeitstempel
  - Bei Timeouts: Dauer und Ablaufzeit

### Benachrichtigungen
- Betroffene User erhalten eine DM (falls aktiviert)
- Kurze Bestätigung im Befehlskanal
- Detaillierte Logs im Mod-Log Kanal

### Datenbank
- Alle Aktionen werden dauerhaft gespeichert
- Historie kann jederzeit eingesehen werden
- Separate Logs für verschiedene Aktionstypen

### Wetter-API
- Nutzt OpenWeatherMap API
- Automatische Aktualisierung der Wetterdaten
- Unterstützung für weltweite Städte
- Temperaturen in Celsius

## Hinweise
- DMs müssen vom User aktiviert sein, um Benachrichtigungen zu erhalten
- Timeouts können nicht länger als 28 Tage sein (Discord-Limit)
- Der Bot benötigt entsprechende Berechtigungen für alle Aktionen
- Mod-Logs sollten in einem geschützten Kanal eingerichtet werden
- Wetter-Updates benötigen einen gültigen API-Schlüssel

## Fehlerbehebung
- Bei fehlenden Berechtigungen wird eine Fehlermeldung angezeigt
- DM-Fehler werden im Mod-Log protokolliert
- Bei Problemen mit Timeouts wird der Grund angegeben
- Ungültige Städtenamen werden mit einer Fehlermeldung quittiert

## Updates
- Neue Befehle werden in diesem Dokument dokumentiert
- Änderungen an bestehenden Befehlen werden hier aufgeführt
- Letzte Aktualisierung: [Datum]

## Moderationsprotokoll
- **Mod-Logs einsehen:** `!modlogs @User`
  - Zeigt alle Moderationsaktionen für einen User
  - Inkl. Verwarnungen, Timeouts, Kicks und Bans
  - **Berechtigung:** Kick Members

### Konfiguration
- **Mod-Log Kanal setzen:** `!setmodlog #Kanal`
  - Legt fest, in welchem Kanal Moderationsaktionen protokolliert werden
  - **Berechtigung:** Administrator
  - **Beispiel:** `!setmodlog #mod-logs`

## Hinweise
- DMs müssen vom User aktiviert sein, um Benachrichtigungen zu erhalten
- Timeouts können nicht länger als 28 Tage sein (Discord-Limit)
- Der Bot benötigt entsprechende Berechtigungen für alle Aktionen
- Mod-Logs sollten in einem geschützten Kanal eingerichtet werden
- Wetter-Updates benötigen einen gültigen API-Schlüssel

## Fehlerbehebung
- Bei fehlenden Berechtigungen wird eine Fehlermeldung angezeigt
- DM-Fehler werden im Mod-Log protokolliert
- Bei Problemen mit Timeouts wird der Grund angegeben
- Ungültige Städtenamen werden mit einer Fehlermeldung quittiert

## Updates
- Neue Befehle werden in diesem Dokument dokumentiert
- Änderungen an bestehenden Befehlen werden hier aufgeführt
- Letzte Aktualisierung: [Datum]

## Auto-Moderation

### Grundeinstellungen
- **System aktivieren:** `!automod enable`
  - Aktiviert die Auto-Moderation
  - **Berechtigung:** Administrator

- **System deaktivieren:** `!automod disable`
  - Deaktiviert die Auto-Moderation
  - **Berechtigung:** Administrator

- **Status anzeigen:** `!automod status`
  - Zeigt aktuelle Einstellungen
  - **Berechtigung:** Administrator

- **Log-Kanal setzen:** `!automod log #kanal`
  - Legt fest, wo Verstöße protokolliert werden
  - **Berechtigung:** Administrator

### Filter-Einstellungen

#### Spam-Schutz
- **Befehl:** `!automod spam <an/aus> [schwelle] [interval]`
  - **Schwelle:** Anzahl ähnlicher Nachrichten (Standard: 5)
  - **Interval:** Zeitraum in Sekunden (Standard: 5)
  - **Beispiel:** `!automod spam an 5 10`

#### Link-Filter
- **Befehl:** `!automod links <an/aus>`
  - Blockiert nicht erlaubte Links
  - Whitelist für vertrauenswürdige Domains

#### CAPS-Filter
- **Befehl:** `!automod caps <an/aus> [schwelle]`
  - **Schwelle:** Prozentsatz Großbuchstaben (Standard: 70)
  - **Beispiel:** `!automod caps an 80`

#### Emoji-Filter
- **Befehl:** `!automod emoji <an/aus> [schwelle]`
  - **Schwelle:** Maximale Anzahl Emojis (Standard: 5)
  - **Beispiel:** `!automod emoji an 7`

#### Flood-Schutz
- **Befehl:** `!automod flood <an/aus> [nachrichten] [sekunden]`
  - Verhindert zu schnelles Nachrichtenspamming
  - **Beispiel:** `!automod flood an 5 3`

### Wort-Filter
- **Wort hinzufügen:** `!automod addword <wort>`
  - Fügt Wort zur Blacklist hinzu
  - **Berechtigung:** Administrator

- **Wort entfernen:** `!automod delword <wort>`
  - Entfernt Wort von der Blacklist
  - **Berechtigung:** Administrator

- **Liste anzeigen:** `!automod words`
  - Zeigt alle gefilterten Wörter
  - **Berechtigung:** Administrator

### Whitelist
- **Rolle ausnehmen:** `!automod whitelist role @rolle`
  - Nimmt eine Rolle von allen Filtern aus
  - **Berechtigung:** Administrator

- **Kanal ausnehmen:** `!automod whitelist channel #kanal`
  - Nimmt einen Kanal von allen Filtern aus
  - **Berechtigung:** Administrator

### Features
- **Spam-Erkennung**
  - Erkennt wiederholte Nachrichten
  - Konfigurierbare Schwelle und Zeitintervall
  - Automatische Nachrichtenlöschung

- **Link-Filter**
  - Blockiert nicht erlaubte Links
  - Whitelist für vertrauenswürdige Domains
  - Schutz vor Phishing/Spam-Links

- **CAPS-Filter**
  - Erkennt übermäßige Großschreibung
  - Ignoriert kurze Nachrichten
  - Konfigurierbare Schwelle

- **Emoji-Spam-Filter**
  - Begrenzt Emoji-Anzahl pro Nachricht
  - Erkennt Custom und Unicode Emojis
  - Konfigurierbare Schwelle

- **Flood-Schutz**
  - Verhindert Nachrichtenflut
  - Zeitbasierte Erkennung
  - Konfigurierbare Parameter

- **Wort-Filter**
  - Blacklist für verbotene Wörter
  - Automatische Nachrichtenlöschung
  - Einfache Verwaltung

### Benachrichtigungen
- Verstöße werden im Log-Kanal protokolliert
- Betroffene User erhalten eine DM
- Detaillierte Verstoß-Informationen
- Nachvollziehbare Moderationsaktionen

### Hinweise
- Whitelist-Rollen sind von allen Filtern ausgenommen
- Whitelist-Kanäle werden nicht überwacht
- Bot benötigt "Nachrichten verwalten" Berechtigung
- Logs erfordern "Nachrichten senden" im Log-Kanal

### Fehlerbehebung
- Prüfe Bot-Berechtigungen
- Stelle sicher, dass der Log-Kanal existiert
- Verifiziere Whitelist-Einstellungen
- Überprüfe Filter-Schwellenwerte 