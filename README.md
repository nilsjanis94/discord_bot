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

- **Willkommensnachricht:** `!welcome message <nachricht>`
  - Legt die Nachricht fest, die neue Mitglieder begrüßt
  - Unterstützt Platzhalter wie {user}, {mention}, {server}, {count}
  - Beispiel: `!welcome message Willkommen {mention} auf {server}!`

- **Regelkanal:** `!welcome rules #kanal`
  - Legt den Kanal für Serverregeln fest
  - Beispiel: `!welcome rules #regeln`

- **Verifikation:** `!welcome verify #kanal @temp-rolle @verifiziert-rolle`
  - Richtet das Verifikationssystem ein
  - Beispiel: `!welcome verify #verify @rookie @member`

- **Status prüfen:** `!checkconfig`
  - Zeigt die aktuelle Konfiguration des Willkommenssystems

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
- **Aktive anzeigen:** `!activetimeouts`
- **User-Timeouts anzeigen:** `!timeouts @User`

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
- **Logs anzeigen:** `!viewlogs [limit]`

### 🤖 Auto-Moderation

#### Grundeinstellungen
- **Aktivieren:** `!automod enable`
- **Deaktivieren:** `!automod disable`
- **Status:** `!automod status`
- **Log-Kanal:** `!automod log #kanal`

#### Filter
- **Spam:** `!automod spam <an/aus> [schwelle] [interval]`
  - Erkennt zu viele Nachrichten in kurzer Zeit
  - Beispiel: `!automod spam an 5 3` (5 Nachrichten in 3 Sekunden)

- **Links:** `!automod links <an/aus>`
  - Filtert Nachrichten mit verbotenen Links
  - Beispiel: `!automod links an`

- **CAPS:** `!automod caps <an/aus> [schwelle]`
  - Erkennt Nachrichten mit zu vielen Großbuchstaben
  - Beispiel: `!automod caps an 70` (70% Großbuchstaben)

- **Emoji:** `!automod emoji <an/aus> [schwelle]`
  - Erkennt Nachrichten mit zu vielen Emojis
  - Beispiel: `!automod emoji an 30` (30% Emojis)

- **Flood:** `!automod flood <an/aus> [nachrichten] [sekunden]`
  - Erkennt wiederholte identische Nachrichten
  - Beispiel: `!automod flood an 5 5` (5 gleiche Nachrichten in 5 Sekunden)

#### Wort-Filter
- **Hinzufügen:** `!automod addword <wort>`
  - Fügt ein Wort zum Filter hinzu
  - Beispiel: `!automod addword schimpfwort`

- **Entfernen:** `!automod delword <wort>`
  - Entfernt ein Wort vom Filter
  - Beispiel: `!automod delword schimpfwort`

- **Liste:** `!automod words`
  - Zeigt alle gefilterten Wörter an

#### Link-Filter
- **Hinzufügen:** `!automod addlink <link>`
  - Fügt einen Link zum Filter hinzu
  - Beispiel: `!automod addlink discord.gg`

- **Entfernen:** `!automod dellink <link>`
  - Entfernt einen Link vom Filter
  - Beispiel: `!automod dellink discord.gg`

- **Liste:** `!automod links`
  - Zeigt alle gefilterten Links an

#### Whitelist
- **Rolle hinzufügen:** `!automod whitelist role @rolle`
  - Fügt eine Rolle zur Whitelist hinzu
  - Beispiel: `!automod whitelist role @Moderator`

- **Kanal hinzufügen:** `!automod whitelist channel #kanal`
  - Fügt einen Kanal zur Whitelist hinzu
  - Beispiel: `!automod whitelist channel #bot-befehle`

- **Liste anzeigen:** `!automod whitelist list`
  - Zeigt alle Whitelist-Einträge an

- **Rolle entfernen:** `!automod whitelist removerole @rolle`
  - Entfernt eine Rolle von der Whitelist
  - Beispiel: `!automod whitelist removerole @Moderator`

- **Kanal entfernen:** `!automod whitelist removechannel #kanal`
  - Entfernt einen Kanal von der Whitelist
  - Beispiel: `!automod whitelist removechannel #bot-befehle`

### 🎭 Reaction Roles

#### Grundbefehle
- **Erstellen:** `!reactionrole create <emoji> @rolle <beschreibung>`
  - Erstellt eine neue Reaction Role Nachricht
  - Beispiel: `!reactionrole create 🎮 @Gamer Rolle für Gamer`

- **Entfernen:** `!reactionrole remove <message_id>`
  - Entfernt eine Reaction Role Nachricht
  - Beispiel: `!reactionrole remove 123456789012345678`

- **Auflisten:** `!reactionrole list`
  - Listet alle aktiven Reaction Roles auf

#### Funktionsweise
- Bot erstellt eine Embed-Nachricht mit der Beschreibung
- Bot fügt das angegebene Emoji als Reaktion hinzu
- User können durch Reaktion die Rolle erhalten/verlieren
- Alle Daten werden in der Datenbank gespeichert

#### Berechtigungen
- `Administrator` für Erstellung und Verwaltung
- Bot benötigt:
  - Rollen verwalten
  - Nachrichten senden
  - Reaktionen hinzufügen
  - Reaktionen sehen

### 🔊 Temporäre Sprachkanäle

#### Admin-Befehle
- **Setup:** `!tempvoice setup [kanalname]`
  - Richtet das System für temporäre Sprachkanäle ein
  - Erstellt einen Erstellungskanal und eine Kategorie
  - Beispiel: `!tempvoice setup "➕ Erstelle deinen Kanal"`

- **Kategorie setzen:** `!tempvoice category <name>`
  - Legt die Kategorie für temporäre Kanäle fest
  - Beispiel: `!tempvoice category "Sprachkanäle"`

- **Limit setzen:** `!tempvoice limit <anzahl>`
  - Legt das Limit für Kanäle pro Benutzer fest (1-10)
  - Beispiel: `!tempvoice limit 3`

- **Standard-Privatsphäre:** `!tempvoice defaultprivacy <public/locked/hidden>`
  - Legt die Standard-Privatsphäre für neue Kanäle fest
  - Beispiel: `!tempvoice defaultprivacy locked`

- **Kanäle auflisten:** `!tempvoice list`
  - Zeigt alle aktiven temporären Sprachkanäle an

#### Benutzer-Befehle
- **Name ändern:** `!tv name <name>`
  - Ändert den Namen des eigenen temporären Kanals
  - Beispiel: `!tv name "Gaming mit Freunden"`

- **Benutzerlimit:** `!tv userlimit <anzahl>`
  - Setzt das Benutzerlimit für den eigenen Kanal (0-99)
  - Beispiel: `!tv userlimit 5`

- **Privatsphäre:** `!tv privacy <public/locked/hidden>`
  - Ändert die Privatsphäre-Einstellung des Kanals
  - `public`: Jeder kann sehen und beitreten
  - `locked`: Jeder kann sehen, aber nur eingeladene Benutzer können beitreten
  - `hidden`: Nur eingeladene Benutzer können den Kanal sehen und beitreten
  - Beispiel: `!tv privacy locked`

- **Benutzer kicken:** `!tv kick @user`
  - Kickt einen Benutzer aus dem eigenen Kanal
  - Beispiel: `!tv kick @Störenfried`

- **Benutzer einladen:** `!tv invite @user`
  - Lädt einen Benutzer in den eigenen Kanal ein
  - Beispiel: `!tv invite @Freund`

#### Funktionsweise
- Benutzer treten dem Erstellungskanal bei
- Ein neuer temporärer Sprachkanal wird automatisch erstellt
- Der Benutzer wird in den neuen Kanal verschoben
- Der Kanal wird automatisch gelöscht, wenn er leer ist
- Der Ersteller hat volle Kontrolle über seinen Kanal
- Privatsphäre-Einstellungen ermöglichen verschiedene Zugriffsebenen

### 🌤️ Wetter-System

#### Wetter abfragen
- **Aktuelles Wetter:** `!wetter <stadt>`
  - Zeigt das aktuelle Wetter für die angegebene Stadt
  - Beispiel: `!wetter Berlin`
  - Zeigt:
    - Temperatur
    - Wetterzustand
    - Windgeschwindigkeit

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
  - Reaction Roles
  - Wetter-Einstellungen
  - Temporäre Sprachkanäle

### Berechtigungen
- Administrator
  - Systemkonfiguration
  - Regelmanagement
  - Auto-Mod Einstellungen
  - Reaction Roles
  - Temporäre Sprachkanäle Setup
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
   !automod log #automod-logs
   !tempvoice setup "➕ Erstelle deinen Kanal"
   ```
3. Regeln erstellen
4. Auto-Mod anpassen
5. Reaction Roles einrichten

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
  - Reaktionen hinzufügen
  - Sprachkanäle erstellen und verwalten

## 🔄 Updates
- Version: 1.0.0
- Letzte Aktualisierung: [DATUM]

## 🤝 Support
Bei Fragen oder Problemen:
- GitHub Issues
- Discord Support Server

## Hinweise
- DMs müssen vom User aktiviert sein, um Benachrichtigungen zu erhalten
- Timeouts können nicht länger als 28 Tage sein (Discord-Limit)
- Der Bot benötigt entsprechende Berechtigungen für alle Aktionen
- Mod-Logs sollten in einem geschützten Kanal eingerichtet werden
- AutoMod-Einstellungen werden in der Datenbank gespeichert und bleiben nach Neustart erhalten
- Reaction Roles funktionieren auch nach Neustart des Bots
- Temporäre Sprachkanäle werden automatisch gelöscht, wenn sie leer sind 