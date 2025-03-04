import discord
from discord.ext import commands, tasks
import asyncio
import sys
import os
import datetime
import pytz
from typing import Optional, Union
import sqlite3

# Pfad zum Hauptverzeichnis hinzufügen, um utils zu importieren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db import Database
from utils.permissions import is_admin

# Hilfsfunktion zum Finden der richtigen Enums
def find_enums():
    # Suche EntityType
    entity_type = None
    if hasattr(discord, 'EntityType'):
        entity_type = discord.EntityType.external
    elif hasattr(discord, 'GuildScheduledEventEntityType'):
        entity_type = discord.GuildScheduledEventEntityType.external
    else:
        print("WARNUNG: EntityType konnte nicht gefunden werden")
        
    # Suche PrivacyLevel
    privacy_level = None
    if hasattr(discord, 'PrivacyLevel'):
        privacy_level = discord.PrivacyLevel.guild_only
    elif hasattr(discord, 'GuildScheduledEventPrivacyLevel'):
        privacy_level = discord.GuildScheduledEventPrivacyLevel.guild_only
    else:
        print("WARNUNG: PrivacyLevel konnte nicht gefunden werden")
    
    return entity_type, privacy_level

class EventPlanner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.reminder_task = self.event_reminder.start()
        self.timezone = pytz.timezone('Europe/Berlin')  # Standard-Zeitzone für Deutschland
    
    def cog_unload(self):
        self.event_reminder.cancel()
    
    async def initialize_database(self):
        """Initialisiert die Datenbanktabellen für den Eventplaner"""
        # Tabelle für Events
        await self.db.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            max_participants INTEGER DEFAULT 0,
            reminder_sent BOOLEAN DEFAULT FALSE,
            discord_event_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Tabelle für Teilnehmer
        await self.db.execute('''
        CREATE TABLE IF NOT EXISTS event_participants (
            event_id INTEGER,
            user_id INTEGER,
            status TEXT NOT NULL,  -- 'accepted', 'declined', 'maybe'
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (event_id, user_id),
            FOREIGN KEY (event_id) REFERENCES events (event_id) ON DELETE CASCADE
        )
        ''')
        
        print("✅ Eventplaner-Datenbanktabellen initialisiert")
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.initialize_database()
        print("✅ Eventplaner bereit!")
    
    @tasks.loop(minutes=5.0)
    async def event_reminder(self):
        """Sendet Erinnerungen für bevorstehende Events"""
        try:
            # Finde Events, die in 30 Minuten beginnen und für die noch keine Erinnerung gesendet wurde
            now = datetime.datetime.now(self.timezone)
            reminder_time = now + datetime.timedelta(minutes=30)
            
            # Finde passende Events
            events = await self.db.fetch_all('''
            SELECT event_id, guild_id, channel_id, title, start_time, description, location 
            FROM events 
            WHERE start_time <= ? AND start_time >= ? AND reminder_sent = FALSE
            ''', (reminder_time.isoformat(), now.isoformat()))
            
            for event in events:
                event_id, guild_id, channel_id, title, start_time, description, location = event
                
                # Hole Teilnehmer, die zugesagt haben
                participants = await self.db.fetch_all('''
                SELECT user_id FROM event_participants 
                WHERE event_id = ? AND status = 'accepted'
                ''', (event_id,))
                
                guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    continue
                
                channel = guild.get_channel(int(channel_id))
                if not channel:
                    continue
                
                # Erstelle Embed für die Erinnerung
                embed = discord.Embed(
                    title=f"⏰ Erinnerung: {title}",
                    description=f"Das Event beginnt in 30 Minuten!\n\n{description}",
                    color=discord.Color.gold()
                )
                
                if location:
                    embed.add_field(name="Ort", value=location, inline=False)
                
                embed.add_field(
                    name="Startzeit", 
                    value=f"<t:{int(datetime.datetime.fromisoformat(start_time).timestamp())}:F>",
                    inline=False
                )
                
                # Erwähne Teilnehmer
                mentions = []
                for participant in participants:
                    user_id = participant[0]
                    mentions.append(f"<@{user_id}>")
                
                if mentions:
                    mention_text = " ".join(mentions)
                    await channel.send(content=f"Erinnerung für: {mention_text}", embed=embed)
                else:
                    await channel.send(embed=embed)
                
                # Markiere Event als erinnert
                await self.db.execute('''
                UPDATE events SET reminder_sent = TRUE WHERE event_id = ?
                ''', (event_id,))
        
        except Exception as e:
            print(f"Fehler beim Senden von Event-Erinnerungen: {e}")
    
    @event_reminder.before_loop
    async def before_reminder(self):
        await self.bot.wait_until_ready()
    
    # Event-Befehle
    @commands.group(name="event", aliases=["events"], invoke_without_command=True)
    async def event_cmd(self, ctx):
        """Verwaltet Events auf dem Server"""
        await self.list_events(ctx)
    
    @event_cmd.command(name="create")
    @is_admin()
    async def create_event(self, ctx, title: str, date: str, time: str, *, description: str = "Keine Beschreibung"):
        """Erstellt ein neues Event"""
        try:
            # Parsen des Datums und der Zeit
            event_datetime_str = f"{date} {time}"
            event_datetime = datetime.datetime.strptime(event_datetime_str, "%Y-%m-%d %H:%M")
            event_datetime = self.timezone.localize(event_datetime)
            
            # Überprüfe, ob das Datum in der Vergangenheit liegt
            if event_datetime < datetime.datetime.now(self.timezone):
                return await ctx.send("❌ Das Datum darf nicht in der Vergangenheit liegen!")
            
            # Bestimme die Endzeit (standardmäßig 2 Stunden nach Startzeit)
            end_datetime = event_datetime + datetime.timedelta(hours=2)
            
            # Event in die Datenbank einfügen
            await self.db.execute('''
            INSERT INTO events 
            (guild_id, channel_id, creator_id, title, description, start_time, end_time) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (str(ctx.guild.id), str(ctx.channel.id), str(ctx.author.id), title, description, 
                  event_datetime.isoformat(), end_datetime.isoformat()))
            
            # Die gerade erstellte Event-ID abrufen
            event_id_result = await self.db.fetch_one('''
            SELECT event_id FROM events 
            WHERE guild_id = ? AND creator_id = ? AND title = ? 
            ORDER BY created_at DESC LIMIT 1
            ''', (str(ctx.guild.id), str(ctx.author.id), title))
            
            event_id = event_id_result[0] if event_id_result else 0
            
            # Erstelle auch ein Discord-Event
            try:
                # Finde die richtigen Enums
                entity_type, privacy_level = find_enums()
                
                if not entity_type or not privacy_level:
                    raise ValueError("Erforderliche Enums konnten nicht gefunden werden")
                
                # Erstelle das Event mit beiden Enums
                discord_event = await ctx.guild.create_scheduled_event(
                    name=title,
                    description=description,
                    start_time=event_datetime,
                    end_time=end_datetime if end_datetime else None,
                    location=ctx.channel.name,
                    entity_type=entity_type,
                    privacy_level=privacy_level
                )
                
                # Speichere Discord Event ID in der Datenbank
                await self.db.execute('''
                UPDATE events SET discord_event_id = ? WHERE event_id = ?
                ''', (str(discord_event.id), event_id))
                
                discord_event_info = f"Discord-Event wurde erstellt! [Zum Event](<https://discord.com/events/{ctx.guild.id}/{discord_event.id}>)"
            except Exception as e:
                print(f"Fehler beim Erstellen des Discord-Events: {e}")
                discord_event_info = f"Discord-Event konnte nicht erstellt werden. Fehler: {e}"
            
            # Event-Nachricht erstellen und senden
            embed = self.create_event_embed(
                title=title,
                description=description,
                start_time=event_datetime,
                end_time=end_datetime,
                creator=ctx.author,
                event_id=event_id
            )
            
            event_message = await ctx.send(embed=embed)
            
            # Reaktionen hinzufügen für Teilnahme
            await event_message.add_reaction("✅")  # Zusagen
            await event_message.add_reaction("❌")  # Absagen
            await event_message.add_reaction("❓")  # Vielleicht
            
            await ctx.send(f"✅ Event **{title}** wurde erstellt! ID: `{event_id}`\n{discord_event_info}")
        
        except ValueError:
            await ctx.send("❌ Ungültiges Datum oder Zeitformat! Bitte verwende das Format `YYYY-MM-DD HH:MM`")
        except Exception as e:
            await ctx.send(f"❌ Fehler beim Erstellen des Events: {e}")
    
    @event_cmd.command(name="edit")
    @is_admin()
    async def edit_event(self, ctx, event_id: int, parameter: str, *, new_value: str):
        """Bearbeitet ein bestehendes Event
        
        Parameter können sein: title, description, date, time, location, max
        Beispiel: !event edit 1 title Neuer Titel
        """
        # Überprüfe, ob das Event existiert
        event = await self.db.fetch_one('''
        SELECT * FROM events WHERE event_id = ? AND guild_id = ?
        ''', (event_id, str(ctx.guild.id)))
        
        if not event:
            return await ctx.send("❌ Event wurde nicht gefunden!")
        
        try:
            if parameter == "title":
                await self.db.execute('''
                UPDATE events SET title = ? WHERE event_id = ?
                ''', (new_value, event_id))
                await ctx.send(f"✅ Titel des Events wurde zu **{new_value}** geändert.")
            
            elif parameter == "description":
                await self.db.execute('''
                UPDATE events SET description = ? WHERE event_id = ?
                ''', (new_value, event_id))
                await ctx.send(f"✅ Beschreibung des Events wurde aktualisiert.")
            
            elif parameter == "date":
                # Aktuelles Event abrufen, um die Zeit zu behalten
                current_event = await self.db.fetch_one('''
                SELECT start_time FROM events WHERE event_id = ?
                ''', (event_id,))
                
                current_datetime = datetime.datetime.fromisoformat(current_event[0])
                current_time = current_datetime.strftime("%H:%M")
                
                # Neues Datum mit alter Zeit kombinieren
                new_datetime_str = f"{new_value} {current_time}"
                new_datetime = datetime.datetime.strptime(new_datetime_str, "%Y-%m-%d %H:%M")
                new_datetime = self.timezone.localize(new_datetime)
                
                # Überprüfe, ob das neue Datum in der Vergangenheit liegt
                if new_datetime < datetime.datetime.now(self.timezone):
                    return await ctx.send("❌ Das Datum darf nicht in der Vergangenheit liegen!")
                
                await self.db.execute('''
                UPDATE events SET start_time = ? WHERE event_id = ?
                ''', (new_datetime.isoformat(), event_id))
                await ctx.send(f"✅ Datum des Events wurde zu **{new_value}** geändert.")
            
            elif parameter == "time":
                # Aktuelles Event abrufen, um das Datum zu behalten
                current_event = await self.db.fetch_one('''
                SELECT start_time FROM events WHERE event_id = ?
                ''', (event_id,))
                
                current_datetime = datetime.datetime.fromisoformat(current_event[0])
                current_date = current_datetime.strftime("%Y-%m-%d")
                
                # Altes Datum mit neuer Zeit kombinieren
                new_datetime_str = f"{current_date} {new_value}"
                new_datetime = datetime.datetime.strptime(new_datetime_str, "%Y-%m-%d %H:%M")
                new_datetime = self.timezone.localize(new_datetime)
                
                # Überprüfe, ob das neue Datum in der Vergangenheit liegt
                if new_datetime < datetime.datetime.now(self.timezone):
                    return await ctx.send("❌ Die Zeit darf nicht in der Vergangenheit liegen!")
                
                await self.db.execute('''
                UPDATE events SET start_time = ? WHERE event_id = ?
                ''', (new_datetime.isoformat(), event_id))
                await ctx.send(f"✅ Zeit des Events wurde zu **{new_value}** geändert.")
            
            elif parameter == "location":
                await self.db.execute('''
                UPDATE events SET location = ? WHERE event_id = ?
                ''', (new_value, event_id))
                await ctx.send(f"✅ Ort des Events wurde zu **{new_value}** geändert.")
            
            elif parameter == "max":
                try:
                    max_participants = int(new_value)
                    if max_participants < 0:
                        raise ValueError("Max. Teilnehmer darf nicht negativ sein")
                    
                    await self.db.execute('''
                    UPDATE events SET max_participants = ? WHERE event_id = ?
                    ''', (max_participants, event_id))
                    
                    max_text = "unbegrenzt" if max_participants == 0 else str(max_participants)
                    await ctx.send(f"✅ Maximale Teilnehmerzahl wurde auf **{max_text}** gesetzt.")
                except ValueError:
                    await ctx.send("❌ Die maximale Teilnehmerzahl muss eine positive Zahl sein!")
            
            else:
                await ctx.send(f"❌ Unbekannter Parameter `{parameter}`. Erlaubte Parameter: title, description, date, time, location, max")
                return
            
            # Aktualisiere die Event-Anzeige
            await self.show_event(ctx, event_id)
            
            # Discord-Event aktualisieren
            discord_event_id = await self.db.fetch_one('''
            SELECT discord_event_id FROM events WHERE event_id = ?
            ''', (event_id,))
            
            if discord_event_id and discord_event_id[0]:
                try:
                    # Aktualisierte Event-Daten abrufen
                    event_data = await self.db.fetch_one('''
                    SELECT title, description, start_time, end_time, location FROM events WHERE event_id = ?
                    ''', (event_id,))
                    
                    if event_data:
                        title, description, start_time, end_time, location = event_data
                        start_datetime = datetime.datetime.fromisoformat(start_time).astimezone(datetime.timezone.utc)
                        end_datetime = datetime.datetime.fromisoformat(end_time).astimezone(datetime.timezone.utc) if end_time else None
                        
                        # Suche das Discord-Event
                        for scheduled_event in await ctx.guild.fetch_scheduled_events():
                            if str(scheduled_event.id) == discord_event_id[0]:
                                # Aktualisiere je nach bearbeitetem Parameter
                                if parameter == "title":
                                    await scheduled_event.edit(name=new_value)
                                elif parameter == "description":
                                    await scheduled_event.edit(description=new_value)
                                elif parameter == "date" or parameter == "time":
                                    await scheduled_event.edit(start_time=start_datetime, end_time=end_datetime)
                                elif parameter == "location":
                                    await scheduled_event.edit(location=new_value)
                                break
                except Exception as e:
                    print(f"Fehler beim Aktualisieren des Discord-Events: {e}")
        
        except Exception as e:
            await ctx.send(f"❌ Fehler beim Bearbeiten des Events: {e}")
    
    @event_cmd.command(name="delete")
    @commands.has_permissions(manage_events=True)
    async def delete_event(self, ctx, event_id: int):
        """Löscht ein Event"""
        try:
            # Prüfe, ob das Event existiert und prüfe beide Formate für guild_id
            event = await self.db.fetch_one('''
            SELECT event_id, discord_event_id FROM events 
            WHERE event_id = ? AND (guild_id = ? OR guild_id = ?)
            ''', (event_id, str(ctx.guild.id), int(ctx.guild.id)))
            
            if not event:
                # Versuche herauszufinden, ob das Event überhaupt existiert
                exists = await self.db.fetch_one('SELECT event_id, guild_id FROM events WHERE event_id = ?', (event_id,))
                
                if exists:
                    return await ctx.send(f"❌ Event mit ID {event_id} gehört zu einem anderen Server (Guild ID: {exists[1]})!")
                else:
                    return await ctx.send(f"❌ Event mit ID {event_id} existiert nicht in der Datenbank!")
            
            # Lösche das Event aus der Datenbank
            await self.db.execute('DELETE FROM events WHERE event_id = ?', (event_id,))
            await self.db.execute('DELETE FROM event_participants WHERE event_id = ?', (event_id,))
            
            # Versuche, das Discord-Event zu löschen (falls vorhanden)
            discord_event_id = event[1]
            if discord_event_id:
                try:
                    scheduled_event = await ctx.guild.fetch_scheduled_event(int(discord_event_id))
                    if scheduled_event:
                        await scheduled_event.delete()
                        await ctx.send(f"✅ Event mit ID {event_id} und zugehöriges Discord-Event wurden gelöscht!")
                    else:
                        await ctx.send(f"✅ Event mit ID {event_id} wurde gelöscht. Discord-Event konnte nicht gefunden werden.")
                except Exception as e:
                    await ctx.send(f"✅ Event mit ID {event_id} wurde gelöscht. Discord-Event konnte nicht gelöscht werden: {str(e)}")
            else:
                await ctx.send(f"✅ Event mit ID {event_id} wurde gelöscht.")
        
        except Exception as e:
            await ctx.send(f"❌ Fehler beim Löschen des Events: {e}")
    
    @event_cmd.command(name="show", aliases=["info"])
    async def show_event(self, ctx, event_id: int):
        """Zeigt Details zu einem Event an"""
        # Event-Details abrufen
        event = await self.db.fetch_one('''
        SELECT event_id, guild_id, creator_id, title, description, location, start_time, end_time, max_participants
        FROM events WHERE event_id = ? AND guild_id = ?
        ''', (event_id, str(ctx.guild.id)))
        
        if not event:
            return await ctx.send("❌ Event wurde nicht gefunden!")
        
        event_id, guild_id, creator_id, title, description, location, start_time, end_time, max_participants = event
        
        # Ersteller des Events ermitteln
        creator = ctx.guild.get_member(int(creator_id))
        creator_name = creator.display_name if creator else "Unbekannt"
        
        # Teilnehmer abrufen
        participants = await self.db.fetch_all('''
        SELECT user_id, status FROM event_participants WHERE event_id = ?
        ''', (event_id,))
        
        # Event-Embed erstellen
        embed = self.create_event_embed(
            title=title,
            description=description,
            start_time=datetime.datetime.fromisoformat(start_time),
            end_time=datetime.datetime.fromisoformat(end_time) if end_time else None,
            location=location,
            creator_name=creator_name,
            max_participants=max_participants,
            event_id=event_id
        )
        
        # Teilnehmerlisten erstellen
        accepted = []
        declined = []
        maybe = []
        
        for participant in participants:
            user_id, status = participant
            member = ctx.guild.get_member(int(user_id))
            if not member:
                continue
            
            if status == "accepted":
                accepted.append(member.display_name)
            elif status == "declined":
                declined.append(member.display_name)
            elif status == "maybe":
                maybe.append(member.display_name)
        
        # Teilnehmerlisten dem Embed hinzufügen
        if accepted:
            embed.add_field(
                name=f"✅ Zusagen ({len(accepted)})",
                value="\n".join(accepted[:10]) + (f"\n... und {len(accepted) - 10} weitere" if len(accepted) > 10 else ""),
                inline=True
            )
        
        if declined:
            embed.add_field(
                name=f"❌ Absagen ({len(declined)})",
                value="\n".join(declined[:10]) + (f"\n... und {len(declined) - 10} weitere" if len(declined) > 10 else ""),
                inline=True
            )
        
        if maybe:
            embed.add_field(
                name=f"❓ Vielleicht ({len(maybe)})",
                value="\n".join(maybe[:10]) + (f"\n... und {len(maybe) - 10} weitere" if len(maybe) > 10 else ""),
                inline=True
            )
        
        message = await ctx.send(embed=embed)
        
        # Reaktionen hinzufügen für Teilnahme
        await message.add_reaction("✅")  # Zusagen
        await message.add_reaction("❌")  # Absagen
        await message.add_reaction("❓")  # Vielleicht
    
    @event_cmd.command(name="list")
    async def list_events(self, ctx):
        """Listet alle aktiven Events auf"""
        # Aktuelle Events abrufen (die noch nicht vorbei sind)
        now = datetime.datetime.now(self.timezone).isoformat()
        events = await self.db.fetch_all('''
        SELECT event_id, title, start_time, creator_id
        FROM events 
        WHERE guild_id = ? AND start_time >= ?
        ORDER BY start_time ASC
        ''', (str(ctx.guild.id), now))
        
        if not events:
            return await ctx.send("📅 Es sind keine aktiven Events geplant.")
        
        embed = discord.Embed(
            title="📅 Geplante Events",
            description="Hier sind alle kommenden Events aufgelistet.",
            color=discord.Color.blue()
        )
        
        for event in events:
            event_id, title, start_time, creator_id = event
            creator = ctx.guild.get_member(int(creator_id))
            creator_name = creator.display_name if creator else "Unbekannt"
            
            start_time_dt = datetime.datetime.fromisoformat(start_time)
            timestamp = int(start_time_dt.timestamp())
            
            # Teilnehmer zählen
            participants_count = await self.db.fetch_one('''
            SELECT COUNT(*) FROM event_participants 
            WHERE event_id = ? AND status = 'accepted'
            ''', (event_id,))
            
            count = participants_count[0] if participants_count else 0
            
            embed.add_field(
                name=f"ID {event_id}: {title}",
                value=f"📆 <t:{timestamp}:F>\n"
                      f"👤 Erstellt von: {creator_name}\n"
                      f"👥 Zusagen: {count}\n"
                      f"ℹ️ `!event show {event_id}` für Details",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @event_cmd.command(name="join")
    async def join_event(self, ctx, event_id: int):
        """Tritt einem Event bei"""
        await self.update_participation(ctx, event_id, "accepted")
    
    @event_cmd.command(name="leave")
    async def leave_event(self, ctx, event_id: int):
        """Verlässt ein Event"""
        await self.update_participation(ctx, event_id, "declined")
    
    @event_cmd.command(name="maybe")
    async def maybe_join_event(self, ctx, event_id: int):
        """Markiert dich als unsicher für ein Event"""
        await self.update_participation(ctx, event_id, "maybe")
    
    async def update_participation(self, ctx, event_id: int, status: str):
        """Aktualisiert den Teilnahmestatus eines Benutzers"""
        # Überprüfe, ob das Event existiert
        event = await self.db.fetch_one('''
        SELECT title, max_participants FROM events WHERE event_id = ? AND guild_id = ?
        ''', (event_id, str(ctx.guild.id)))
        
        if not event:
            return await ctx.send("❌ Event wurde nicht gefunden!")
        
        title, max_participants = event
        
        # Überprüfe, ob das Event voll ist (nur für Zusagen)
        if status == "accepted" and max_participants > 0:
            current_participants = await self.db.fetch_one('''
            SELECT COUNT(*) FROM event_participants 
            WHERE event_id = ? AND status = 'accepted'
            ''', (event_id,))
            
            if current_participants and current_participants[0] >= max_participants:
                return await ctx.send(f"❌ Das Event **{title}** ist bereits voll!")
        
        # Aktualisiere oder füge Teilnahme hinzu
        await self.db.execute('''
        INSERT OR REPLACE INTO event_participants (event_id, user_id, status)
        VALUES (?, ?, ?)
        ''', (event_id, str(ctx.author.id), status))
        
        status_text = {
            "accepted": "zugesagt",
            "declined": "abgesagt",
            "maybe": "als unsicher markiert"
        }
        
        await ctx.send(f"✅ Du hast für das Event **{title}** {status_text[status]}.")
        
        # Aktualisiere die Event-Anzeige
        await self.show_event(ctx, event_id)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Reagiert auf Reaktionen bei Event-Nachrichten"""
        if payload.user_id == self.bot.user.id:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return
        
        try:
            message = await channel.fetch_message(payload.message_id)
            if not message.embeds or not message.embeds[0].title or not message.embeds[0].footer.text:
                return
            
            # Überprüfe, ob es sich um eine Event-Nachricht handelt
            footer_text = message.embeds[0].footer.text
            if not "Event ID:" in footer_text:
                return
            
            # Extrahiere die Event-ID (sicherer Ansatz)
            try:
                event_id_part = footer_text.split("Event ID:")[1].split("|")[0].strip()
                event_id = int(event_id_part)
            except (IndexError, ValueError):
                print(f"❌ Konnte Event-ID nicht aus Footer extrahieren: '{footer_text}'")
                return
            
            # Überprüfe, ob das Event existiert
            event = await self.db.fetch_one('''
            SELECT title FROM events WHERE event_id = ?
            ''', (event_id,))
            
            if not event:
                return
            
            # Entferne die Reaktion des Benutzers
            user = self.bot.get_user(payload.user_id)
            if user:
                await message.remove_reaction(payload.emoji, user)
            
            # Verarbeite die Reaktion
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            
            if str(payload.emoji) == "✅":
                await self.update_participation_by_reaction(guild, member, event_id, "accepted")
            elif str(payload.emoji) == "❌":
                await self.update_participation_by_reaction(guild, member, event_id, "declined")
            elif str(payload.emoji) == "❓":
                await self.update_participation_by_reaction(guild, member, event_id, "maybe")
        
        except Exception as e:
            print(f"Fehler bei der Verarbeitung der Reaktion: {e}")
    
    async def update_participation_by_reaction(self, guild, member, event_id, status):
        """Aktualisiert den Teilnahmestatus eines Benutzers via Reaktion"""
        if not member:
            return
        
        # Überprüfe, ob das Event existiert
        event = await self.db.fetch_one('''
        SELECT title, max_participants, channel_id FROM events WHERE event_id = ?
        ''', (event_id,))
        
        if not event:
            return
        
        title, max_participants, channel_id = event
        channel = guild.get_channel(int(channel_id))
        
        # Überprüfe, ob das Event voll ist (nur für Zusagen)
        if status == "accepted" and max_participants > 0:
            current_participants = await self.db.fetch_one('''
            SELECT COUNT(*) FROM event_participants 
            WHERE event_id = ? AND status = 'accepted' AND user_id != ?
            ''', (event_id, str(member.id)))
            
            if current_participants and current_participants[0] >= max_participants:
                try:
                    await member.send(f"❌ Das Event **{title}** auf **{guild.name}** ist bereits voll!")
                except:
                    if channel:
                        await channel.send(f"{member.mention}, das Event **{title}** ist bereits voll!")
                return
        
        # Aktualisiere oder füge Teilnahme hinzu
        await self.db.execute('''
        INSERT OR REPLACE INTO event_participants (event_id, user_id, status)
        VALUES (?, ?, ?)
        ''', (event_id, str(member.id), status))
        
        status_text = {
            "accepted": "zugesagt zu",
            "declined": "abgesagt für",
            "maybe": "dich als unsicher markiert für"
        }
        
        try:
            await member.send(f"✅ Du hast {status_text[status]} dem Event **{title}** auf **{guild.name}**.")
        except:
            pass
        
        # Aktualisiere die Event-Nachricht, falls der Kanal noch existiert
        if channel:
            # Erzeuge und sende ein aktualisiertes Embed
            event_details = await self.db.fetch_one('''
            SELECT creator_id, title, description, location, start_time, end_time, max_participants
            FROM events WHERE event_id = ?
            ''', (event_id,))
            
            if not event_details:
                return
            
            creator_id, title, description, location, start_time, end_time, max_participants = event_details
            
            # Suche nach der letzten Event-Nachricht im Kanal
            async for message in channel.history(limit=50):
                if message.author == self.bot.user and message.embeds:
                    for embed in message.embeds:
                        if embed.footer.text == f"Event ID: {event_id}":
                            # Update this message
                            creator = guild.get_member(int(creator_id))
                            creator_name = creator.display_name if creator else "Unbekannt"
                            
                            new_embed = self.create_event_embed(
                                title=title,
                                description=description,
                                start_time=datetime.datetime.fromisoformat(start_time),
                                end_time=datetime.datetime.fromisoformat(end_time) if end_time else None,
                                location=location,
                                creator_name=creator_name,
                                max_participants=max_participants,
                                event_id=event_id
                            )
                            
                            # Teilnehmerlisten erstellen
                            participants = await self.db.fetch_all('''
                            SELECT user_id, status FROM event_participants WHERE event_id = ?
                            ''', (event_id,))
                            
                            accepted = []
                            declined = []
                            maybe = []
                            
                            for participant in participants:
                                user_id, p_status = participant
                                p_member = guild.get_member(int(user_id))
                                if not p_member:
                                    continue
                                
                                if p_status == "accepted":
                                    accepted.append(p_member.display_name)
                                elif p_status == "declined":
                                    declined.append(p_member.display_name)
                                elif p_status == "maybe":
                                    maybe.append(p_member.display_name)
                            
                            # Teilnehmerlisten dem Embed hinzufügen
                            if accepted:
                                new_embed.add_field(
                                    name=f"✅ Zusagen ({len(accepted)})",
                                    value="\n".join(accepted[:10]) + (f"\n... und {len(accepted) - 10} weitere" if len(accepted) > 10 else ""),
                                    inline=True
                                )
                            
                            if declined:
                                new_embed.add_field(
                                    name=f"❌ Absagen ({len(declined)})",
                                    value="\n".join(declined[:10]) + (f"\n... und {len(declined) - 10} weitere" if len(declined) > 10 else ""),
                                    inline=True
                                )
                            
                            if maybe:
                                new_embed.add_field(
                                    name=f"❓ Vielleicht ({len(maybe)})",
                                    value="\n".join(maybe[:10]) + (f"\n... und {len(maybe) - 10} weitere" if len(maybe) > 10 else ""),
                                    inline=True
                                )
                            
                            await message.edit(embed=new_embed)
                            return
    
    def create_event_embed(self, title, description, start_time, creator=None, creator_name=None, 
                          end_time=None, location=None, max_participants=0, event_id=None):
        """Erstellt ein Embed für ein Event"""
        embed = discord.Embed(
            title=f"📅 {title}",
            description=description,
            color=discord.Color.blue()
        )
        
        # Start- und Endzeit formatieren
        start_timestamp = int(start_time.timestamp())
        embed.add_field(
            name="📆 Startzeit",
            value=f"<t:{start_timestamp}:F>",
            inline=False
        )
        
        if end_time:
            end_timestamp = int(end_time.timestamp())
            embed.add_field(
                name="⏰ Endzeit",
                value=f"<t:{end_timestamp}:F>",
                inline=False
            )
        
        # Ort hinzufügen, falls vorhanden
        if location:
            embed.add_field(
                name="📍 Ort",
                value=location,
                inline=False
            )
        
        # Maximale Teilnehmerzahl anzeigen
        if max_participants > 0:
            embed.add_field(
                name="👥 Maximale Teilnehmerzahl",
                value=str(max_participants),
                inline=True
            )
        
        # Ersteller hinzufügen
        event_id_str = str(event_id) if event_id is not None else "0"
        if creator:
            embed.set_footer(text=f"Event ID: {event_id_str} | Erstellt von {creator.display_name}")
            embed.set_author(name=creator.display_name, icon_url=creator.display_avatar.url)
        elif creator_name:
            embed.set_footer(text=f"Event ID: {event_id_str} | Erstellt von {creator_name}")
        else:
            embed.set_footer(text=f"Event ID: {event_id_str}")
        
        return embed

    @event_cmd.command(name="participants", aliases=["teilnehmer"])
    async def list_participants(self, ctx, event_id: int):
        """Zeigt nur die Teilnehmerliste eines Events an"""
        # Event-Details abrufen
        event = await self.db.fetch_one('''
        SELECT title FROM events WHERE event_id = ? AND guild_id = ?
        ''', (event_id, str(ctx.guild.id)))
        
        if not event:
            return await ctx.send("❌ Event wurde nicht gefunden!")
        
        title = event[0]
        
        # Teilnehmer abrufen
        participants = await self.db.fetch_all('''
        SELECT user_id, status FROM event_participants WHERE event_id = ?
        ''', (event_id,))
        
        if not participants:
            return await ctx.send(f"📋 Für das Event **{title}** (ID: {event_id}) haben sich noch keine Teilnehmer angemeldet.")
        
        # Teilnehmer nach Status sortieren
        accepted = []
        declined = []
        maybe = []
        
        for participant in participants:
            user_id, status = participant
            member = ctx.guild.get_member(int(user_id))
            if not member:
                continue
            
            if status == "accepted":
                accepted.append(member.display_name)
            elif status == "declined":
                declined.append(member.display_name)
            elif status == "maybe":
                maybe.append(member.display_name)
        
        # Embed erstellen
        embed = discord.Embed(
            title=f"📋 Teilnehmerliste: {title}",
            description=f"Event ID: {event_id}",
            color=discord.Color.blue()
        )
        
        # Teilnehmerlisten dem Embed hinzufügen
        if accepted:
            embed.add_field(
                name=f"✅ Zusagen ({len(accepted)})",
                value="\n".join(accepted) if len(accepted) <= 15 else "\n".join(accepted[:15]) + f"\n... und {len(accepted) - 15} weitere",
                inline=False
            )
        else:
            embed.add_field(name="✅ Zusagen (0)", value="Noch keine Zusagen", inline=False)
        
        if declined:
            embed.add_field(
                name=f"❌ Absagen ({len(declined)})",
                value="\n".join(declined) if len(declined) <= 10 else "\n".join(declined[:10]) + f"\n... und {len(declined) - 10} weitere",
                inline=False
            )
        
        if maybe:
            embed.add_field(
                name=f"❓ Vielleicht ({len(maybe)})",
                value="\n".join(maybe) if len(maybe) <= 10 else "\n".join(maybe[:10]) + f"\n... und {len(maybe) - 10} weitere",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="db_debug")
    @commands.has_permissions(administrator=True)
    async def db_debug(self, ctx):
        """Zeigt Debug-Informationen zur Datenbank an"""
        try:
            # Prüfe DB-Pfad
            db_path = self.db.db_path
            
            # Hole alle Events ohne Filter
            all_events = await self.db.fetch_all("SELECT event_id, guild_id, title, discord_event_id FROM events")
            
            debug_info = f"**Datenbank-Debug:**\n"
            debug_info += f"Datenbankpfad: {db_path}\n\n"
            
            debug_info += f"**Alle Events ({len(all_events)}):**\n"
            for event in all_events:
                debug_info += f"ID: {event[0]} | Guild: {event[1]} (aktuell: {ctx.guild.id}) | Titel: {event[2]} | Discord-ID: {event[3]}\n"
            
            # Nach Guild-ID filtern
            filtered_events = await self.db.fetch_all(
                "SELECT event_id, guild_id FROM events WHERE guild_id = ?", 
                (str(ctx.guild.id),)
            )
            
            debug_info += f"\n**Events mit guild_id {ctx.guild.id} ({len(filtered_events)}):**\n"
            for event in filtered_events:
                debug_info += f"ID: {event[0]} | Guild: {event[1]}\n"
            
            # Suche konkretes Event
            if ctx.message.content.split()[-1].isdigit():
                event_id = int(ctx.message.content.split()[-1])
                event = await self.db.fetch_one(
                    "SELECT event_id, guild_id, title FROM events WHERE event_id = ?", 
                    (event_id,)
                )
                if event:
                    debug_info += f"\n**Gefundenes Event {event_id}:**\n"
                    debug_info += f"ID: {event[0]} | Guild: {event[1]} | Titel: {event[2]}\n"
                else:
                    debug_info += f"\n**Event {event_id} nicht gefunden!**\n"
            
            await ctx.send(debug_info)
        except Exception as e:
            await ctx.send(f"Fehler beim Debugging: {e}")

async def setup(bot):
    # Erst die Datenbank initialisieren
    event_db = Database()
    
    # Erstelle die Tabellen für den Eventplaner
    try:
        await event_db.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            max_participants INTEGER DEFAULT 0,
            reminder_sent BOOLEAN DEFAULT FALSE,
            discord_event_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        await event_db.execute('''
        CREATE TABLE IF NOT EXISTS event_participants (
            event_id INTEGER,
            user_id INTEGER,
            status TEXT NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (event_id, user_id),
            FOREIGN KEY (event_id) REFERENCES events (event_id) ON DELETE CASCADE
        )
        ''')
        
        print("✅ Eventplaner-Datenbanktabellen initialisiert")
    except Exception as e:
        print(f"❌ Fehler beim Initialisieren der Eventplaner-Datenbank: {e}")
    
    # Jetzt können wir den Cog hinzufügen
    await bot.add_cog(EventPlanner(bot)) 