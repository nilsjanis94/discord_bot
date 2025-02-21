# Discord Bot Dokumentation

## Moderationsbefehle

### Timeout
Schaltet einen User temporär stumm.
- **Befehl:** `!timeout @User/ID/Name [Minuten] [Grund]`
- **Beispiel:** `!timeout @User 10 Spam im Chat`
- **Berechtigung:** Kick Members
- **Limits:** 
  - Minimum: 1 Minute
  - Maximum: 40320 Minuten (28 Tage)

### Kick
Kickt einen User vom Server.
- **Befehl:** `!kick @User/ID/Name [Grund]`
- **Beispiel:** `!kick @User Regelverstoß`
- **Berechtigung:** Kick Members

### Ban
Bannt einen User vom Server.
- **Befehl:** `!ban @User/ID/Name [Grund]`
- **Beispiel:** `!ban @User Schwerer Regelverstoß`
- **Berechtigung:** Ban Members

### Timeout-Verwaltung
- **Aktive Timeouts anzeigen:** `!activetimeouts`
  - Zeigt alle derzeit aktiven Timeouts auf dem Server
  - **Berechtigung:** Kick Members

- **Timeout-Historie:** `!timeouts @User`
  - Zeigt die letzten 10 Timeouts eines Users
  - **Berechtigung:** Kick Members

### Moderationsprotokoll
- **Mod-Logs einsehen:** `!modlogs @User`
  - Zeigt alle Moderationsaktionen für einen User
  - Inkl. Verwarnungen, Timeouts, Kicks und Bans
  - **Berechtigung:** Kick Members

### Konfiguration
- **Mod-Log Kanal setzen:** `!setmodlog #Kanal`
  - Legt fest, in welchem Kanal Moderationsaktionen protokolliert werden
  - **Berechtigung:** Administrator
  - **Beispiel:** `!setmodlog #mod-logs`

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

## Hinweise
- DMs müssen vom User aktiviert sein, um Benachrichtigungen zu erhalten
- Timeouts können nicht länger als 28 Tage sein (Discord-Limit)
- Der Bot benötigt entsprechende Berechtigungen für alle Aktionen
- Mod-Logs sollten in einem geschützten Kanal eingerichtet werden

## Fehlerbehebung
- Bei fehlenden Berechtigungen wird eine Fehlermeldung angezeigt
- DM-Fehler werden im Mod-Log protokolliert
- Bei Problemen mit Timeouts wird der Grund angegeben

## Updates
- Neue Befehle werden in diesem Dokument dokumentiert
- Änderungen an bestehenden Befehlen werden hier aufgeführt
- Letzte Aktualisierung: [Datum] 