# Discord Bot

Ein vielseitiger Discord Bot für Moderation, Community-Management und Server-Administration.

## Features

### 👋 Willkommenssystem

#### Grundeinrichtung
- **Setup:** `!welcome setup`
  - Erstellt Rollen (Unverified/Verified)
  - Aktiviert Regelakzeptanz
  - Aktiviert Willkommenssystem

#### Konfiguration
- **Willkommenskanal:** `!welcome channel #kanal`
  - Legt den Kanal für Willkommensnachrichten fest
  - Beispiel: `!welcome channel #willkommen`

- **Regelkanal:** `!welcome rules #kanal`
  - Legt den Kanal für Serverregeln fest
  - Beispiel: `!welcome rules #regeln`

#### Funktionsweise
- Neue Mitglieder erhalten automatisch die @Unverified Rolle
- Willkommensnachricht mit Instruktionen im Willkommenskanal
- Nach Regelakzeptanz (✅):
  - @Unverified Rolle wird entfernt
  - @Verified Rolle wird hinzugefügt
  - User erhält Bestätigungsnachricht

#### Berechtigungen
- `Administrator` für Setup und Konfiguration
- Bot benötigt:
  - Rollen verwalten
  - Nachrichten senden
  - Reaktionen sehen
  - DMs senden (optional)

#### Platzhalter
- `{user}` - Username
- `{mention}` - User-Mention
- `{server}` - Servername
- `{count}` - Mitgliederzahl

### 📜 Regelsystem

#### Grundbefehle
- **Anzeigen:** `!rules`
- **Hinzufügen:** `!rules add <nummer> <titel | inhalt>`
- **Bearbeiten:** `!rules edit <nummer> <titel | inhalt>`
- **Entfernen:** `!rules remove <nummer>`
- **Kanal setzen:** `!rules channel #kanal`
- **Berechtigung:** Administrator

#### Format
- Titel optional (mit | getrennt)
- Automatische Nummerierung
- Formatierte Anzeige
- Bearbeitungsverlauf
- Zeitstempel

#### Beispiele
- Regel hinzufügen: `!rules add 1 Respekt | Behandle alle mit Respekt`
- Regel bearbeiten: `!rules edit 1 Verhalten | Sei freundlich zu allen`
- Regel entfernen: `!rules remove 1`

### 🛡️ Moderationssystem

#### Verwarnungen
- **Verwarnen:** `!warn @User <grund>`
- **Anzeigen:** `!warnings @User`
- **Löschen:** `!delwarn @User <nummer>`
- **Alle löschen:** `!clearwarnings @User`

#### Timeouts
- **Timeout:** `!timeout @User <minuten> [grund]`
- **Aufheben:** `!untimeout @User`
- **Limits:** 1-40320 Minuten (28 Tage)

#### Kicks & Bans
- **Kick:** `!kick @User [grund]`
- **Ban:** `!ban @User [grund]`
- **Unban:** `!unban <User-ID>`

#### Nachrichten
- **Löschen:** `!clear <anzahl>`
- **Limit:** 1-100 Nachrichten

#### Modlogs
- **Anzeigen:** `!modlogs @User`
- **Kanal setzen:** `!setmodlog #kanal`

### 🤖 Auto-Moderation

#### Grundeinstellungen
- **Aktivieren:** `!automod enable`
- **Deaktivieren:** `!automod disable`
- **Status:** `!automod status`
- **Log-Kanal:** `!automod log #kanal`

#### Filter
- **Spam:** `!automod spam <an/aus> [schwelle] [interval]`
- **Links:** `!automod links <an/aus>`
- **CAPS:** `!automod caps <an/aus> [schwelle]`
- **Emoji:** `!automod emoji <an/aus> [schwelle]`
- **Flood:** `!automod flood <an/aus> [nachrichten] [sekunden]`

#### Wort-Filter
- **Hinzufügen:** `!automod addword <wort>`
- **Entfernen:** `!automod delword <wort>`
- **Liste:** `!automod words`

#### Whitelist
- **Rolle:** `!automod whitelist role @rolle`
- **Kanal:** `!automod whitelist channel #kanal`

## 📝 Logging-System

### Mod-Logs
- Alle Moderationsaktionen
- Farbcodierte Embeds
- Zeitstempel und Dauer
- Grund und Moderator
- Verwarnungszähler

### Auto-Mod Logs
- Automatische Aktionen
- Regelverstoß-Details
- Betroffene Nachrichten
- Filter-Auslöser

### Welcome-Logs
- Neue Mitglieder
- Regelakzeptanz
- Rollenvergabe
- Verifikationsstatus

## ⚙️ Technische Details

### Datenbank
- SQLite für persistente Datenspeicherung
- Separate Tabellen für:
  - Moderationsaktionen
  - Verwarnungen
  - Auto-Mod Konfiguration
  - Server-Einstellungen
  - Wort-Filter
  - Serverregeln
  - Willkommenssystem

### Berechtigungen
- Administrator
  - Systemkonfiguration
  - Regelmanagement
  - Auto-Mod Einstellungen
- Moderator (Kick Members)
  - Verwarnungen
  - Timeouts
  - Kicks
- Ban Members
  - Bans/Unbans

### Fehlerbehandlung
- Ausführliche Fehlermeldungen
- Berechtigungsprüfungen
- Parametervalidierung
- Datenbank-Backup

## 🔧 Installation & Setup

1. Bot zum Server einladen
2. Grundeinrichtung:
   ```
   !welcome setup
   !welcome channel #willkommen
   !welcome rules #regeln
   !setmodlog #mod-logs
   !automod enable
   ```
3. Regeln erstellen
4. Auto-Mod anpassen

## 📋 Voraussetzungen

- Discord.py 2.0+
- Python 3.8+
- SQLite3
- Erforderliche Bot-Berechtigungen:
  - Nachrichten verwalten
  - Mitglieder kicken
  - Mitglieder bannen
  - Timeout vergeben
  - Nachrichten senden
  - Embeds senden
  - Rollen verwalten

## 🔄 Updates
- Version: 1.0.0
- Letzte Aktualisierung: [DATUM]

## 🤝 Support
Bei Fragen oder Problemen:
- GitHub Issues
- Discord Support Server

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