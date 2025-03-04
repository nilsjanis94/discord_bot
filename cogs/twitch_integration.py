import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from datetime import datetime, timedelta
import traceback
import sys
import os
from typing import Dict, List, Optional
from config import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET

# Füge das Hauptverzeichnis zum Pfad hinzu, damit wir utils importieren können
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db import Database
from utils.permissions import is_admin

class TwitchIntegration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.client_id = TWITCH_CLIENT_ID
        self.client_secret = TWITCH_CLIENT_SECRET
        self.access_token = None
        self.token_expires = None
        
        # Cache für Streamer-Status, vermeidet wiederholte Ankündigungen
        self.live_streamers = {}
        self.check_streams.start()
    
    def cog_unload(self):
        self.check_streams.cancel()
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Lädt die Konfiguration beim Start des Bots"""
        await self.load_config()
    
    async def load_config(self):
        """Lädt die API-Anmeldeinformationen aus der Datenbank"""
        # Lädt die erste vorhandene Konfiguration
        config = await self.db.fetch_one(
            "SELECT client_id, client_secret FROM twitch_config LIMIT 1"
        )
        
        if config:
            self.client_id = config[0]
            self.client_secret = config[1]
            print("✅ Twitch API-Konfiguration geladen")
    
    async def get_access_token(self):
        """Holt ein neues Access-Token von der Twitch API"""
        if not self.client_id or not self.client_secret:
            print("❌ Twitch API-Konfiguration fehlt")
            return False
            
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
            
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://id.twitch.tv/oauth2/token"
                params = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials"
                }
                
                async with session.post(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.access_token = data["access_token"]
                        self.token_expires = datetime.now() + timedelta(seconds=data["expires_in"] - 100)
                        return self.access_token
                    else:
                        print(f"❌ Fehler beim Abrufen des Access-Tokens: {response.status}")
                        return None
        except Exception as e:
            print(f"❌ Fehler beim Abrufen des Access-Tokens: {e}")
            return None
    
    @tasks.loop(minutes=5.0)
    async def check_streams(self):
        """Prüft regelmäßig den Status aller überwachten Streamer"""
        await self.bot.wait_until_ready()
        token = await self.get_access_token()
        if not token:
            return

        try:
            streamers = await self.db.fetch_all(
                "SELECT streamer_name, guild_id, last_stream_id, user_id FROM twitch_streamers"
            )
            
            if not streamers:
                return
                
            # Streamer nach Guild gruppieren
            guilds_streamers = {}
            for streamer in streamers:
                guild_id = streamer[1]
                if guild_id not in guilds_streamers:
                    guilds_streamers[guild_id] = []
                guilds_streamers[guild_id].append(streamer)
            
            # Für jede Guild die Streamer überprüfen
            for guild_id, guild_streamers in guilds_streamers.items():
                # Konfiguration für diese Guild laden
                config = await self.db.fetch_one(
                    "SELECT announcement_channel_id, announcement_message, ping_role_id, enabled FROM twitch_config WHERE guild_id = ?",
                    (guild_id,)
                )
                
                if not config or not config[3]:  # Wenn nicht aktiviert
                    continue
                    
                channel_id, message_template, ping_role_id, _ = config
                
                # Channel und Guild Objekte abrufen
                guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    continue
                    
                channel = guild.get_channel(int(channel_id)) if channel_id else None
                if not channel:
                    continue
                
                # Liste der Streamernamen für diese Guild
                streamer_names = [s[0] for s in guild_streamers]
                
                # Status der Streamer abfragen
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Client-ID": self.client_id,
                        "Authorization": f"Bearer {token}"
                    }
                    
                    # Streamerdaten abrufen
                    user_ids = [s[3] for s in guild_streamers if s[3]]
                    streamer_data = {}
                    
                    # Streamer-IDs abrufen, falls nicht vorhanden
                    missing_ids = [s[0] for s in guild_streamers if not s[3]]
                    if missing_ids:
                        chunks = [missing_ids[i:i+100] for i in range(0, len(missing_ids), 100)]
                        for chunk in chunks:
                            params = "&".join([f"login={name}" for name in chunk])
                            async with session.get(f"https://api.twitch.tv/helix/users?{params}", headers=headers) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    for user in data["data"]:
                                        # Streamer-ID in der Datenbank aktualisieren
                                        await self.db.execute(
                                            "UPDATE twitch_streamers SET user_id = ? WHERE streamer_name = ? AND guild_id = ?",
                                            (user["id"], user["login"], guild_id)
                                        )
                                        user_ids.append(user["id"])
                    
                    # Streamer-Status abfragen
                    if user_ids:
                        chunks = [user_ids[i:i+100] for i in range(0, len(user_ids), 100)]
                        for chunk in chunks:
                            params = "&".join([f"user_id={uid}" for uid in chunk])
                            async with session.get(f"https://api.twitch.tv/helix/streams?{params}", headers=headers) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    for stream in data["data"]:
                                        streamer_data[stream["user_login"].lower()] = stream
                    
                    # Für jeden Streamer prüfen
                    for streamer_name, guild_id, last_stream_id, user_id in guild_streamers:
                        streamer_name_lower = streamer_name.lower()
                        
                        # Streamer ist gerade live
                        if streamer_name_lower in streamer_data:
                            stream = streamer_data[streamer_name_lower]
                            stream_id = stream["id"]
                            
                            # Neuer Stream (anderer Stream-ID als zuletzt)
                            if last_stream_id != stream_id:
                                # Ankündigung senden
                                await self.announce_stream(
                                    guild, channel, stream, message_template, 
                                    ping_role_id, streamer_name
                                )
                                
                                # Letzten Stream-ID aktualisieren
                                await self.db.execute(
                                    "UPDATE twitch_streamers SET last_stream_id = ?, last_online = ? WHERE streamer_name = ? AND guild_id = ?",
                                    (stream_id, datetime.now(), streamer_name, guild_id)
                                )
                            
                            # Status für Cache aktualisieren
                            self.live_streamers[f"{guild_id}:{streamer_name}"] = True
                        else:
                            # Streamer ist offline
                            if f"{guild_id}:{streamer_name}" in self.live_streamers:
                                del self.live_streamers[f"{guild_id}:{streamer_name}"]
        except Exception as e:
            print(f"❌ Fehler beim Überprüfen der Streams: {str(e)}")
            traceback.print_exc()
    
    async def announce_stream(self, guild, channel, stream_data, message_template, ping_role_id, streamer_name):
        """Sendet eine Ankündigung, wenn ein Streamer online geht"""
        try:
            # Ping-Rolle Erwähnung
            role_mention = ""
            if ping_role_id:
                role = guild.get_role(int(ping_role_id))
                if role:
                    role_mention = role.mention + " "
            
            # Platzhalter ersetzen
            message = message_template.format(
                streamer=stream_data["user_name"],
                title=stream_data["title"],
                game=stream_data.get("game_name", "Unbekanntes Spiel"),
                url=f"https://twitch.tv/{stream_data['user_login']}",
                viewers=stream_data.get("viewer_count", 0)
            )
            
            # Abonnenten für diesen Streamer
            subscribers = await self.db.fetch_all(
                "SELECT user_id FROM twitch_subscriptions WHERE guild_id = ? AND streamer_name = ?",
                (str(guild.id), streamer_name)
            )
            
            subscriber_mentions = ""
            if subscribers:
                subscriber_mentions = " ".join([f"<@{sub[0]}>" for sub in subscribers])
            
            # Embed erstellen
            embed = discord.Embed(
                title=stream_data["title"],
                url=f"https://twitch.tv/{stream_data['user_login']}",
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )
            embed.set_author(
                name=f"{stream_data['user_name']} ist jetzt live!",
                url=f"https://twitch.tv/{stream_data['user_login']}",
                icon_url="https://static.twitchcdn.net/assets/favicon-32-d6025c14e900565d6177.png"
            )
            embed.add_field(name="Kategorie", value=stream_data.get("game_name", "Unbekanntes Spiel"), inline=True)
            embed.add_field(name="Zuschauer", value=str(stream_data.get("viewer_count", 0)), inline=True)
            
            # Vorschaubild
            thumbnail_url = stream_data.get("thumbnail_url", "")
            if thumbnail_url:
                # Größe anpassen und Timestamp für Cache-Breaking hinzufügen
                thumbnail_url = thumbnail_url.replace("{width}", "320").replace("{height}", "180")
                thumbnail_url += f"?t={int(datetime.now().timestamp())}"
                embed.set_image(url=thumbnail_url)
            
            # Fußzeile
            embed.set_footer(text="Twitch Stream gestartet um")
            
            # Nachricht senden
            content = f"{role_mention}{subscriber_mentions}\n{message}" if role_mention or subscriber_mentions else message
            await channel.send(content=content, embed=embed)
            
        except Exception as e:
            print(f"❌ Fehler beim Ankündigen des Streams: {str(e)}")
    
    @commands.group(name="twitch", invoke_without_command=True)
    async def twitch_cmd(self, ctx):
        """Hauptbefehl für die Twitch-Integration"""
        embed = discord.Embed(
            title="🎮 Twitch-Integration Befehle",
            description="Verwende diese Befehle, um die Twitch-Integration zu verwalten:",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="Admin-Befehle",
            value=(
                "`!twitch setup` - Richtet die Twitch-Integration ein\n"
                "`!twitch api <client_id> <client_secret>` - Konfiguriert die API-Zugangsdaten\n"
                "`!twitch channel #kanal` - Setzt den Ankündigungskanal\n"
                "`!twitch message <nachricht>` - Passt die Ankündigungsnachricht an\n"
                "`!twitch role @rolle` - Legt die Ping-Rolle fest\n"
                "`!twitch add <streamer>` - Fügt einen Streamer hinzu\n"
                "`!twitch remove <streamer>` - Entfernt einen Streamer\n"
                "`!twitch list` - Zeigt alle überwachten Streamer an"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Benutzer-Befehle",
            value=(
                "`!twitch subscribe <streamer>` - Abonniert Benachrichtigungen für einen Streamer\n"
                "`!twitch unsubscribe <streamer>` - Meldet sich von Benachrichtigungen ab\n"
                "`!twitch mysubs` - Zeigt alle abonnierten Streamer an"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Platzhalter für Ankündigungsnachrichten",
            value=(
                "`{streamer}` - Name des Streamers\n"
                "`{title}` - Titel des Streams\n"
                "`{game}` - Spielkategorie\n"
                "`{url}` - Link zum Stream\n"
                "`{viewers}` - Anzahl der Zuschauer"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @twitch_cmd.command(name="setup")
    @is_admin()
    async def setup_twitch(self, ctx):
        """Richtet die Twitch-Integration ein"""
        # Überprüfen, ob bereits konfiguriert
        config = await self.db.fetch_one(
            "SELECT client_id, client_secret, announcement_channel_id FROM twitch_config WHERE guild_id = ?",
            (str(ctx.guild.id),)
        )
        
        if config and all(config):
            await ctx.send("✅ Die Twitch-Integration ist bereits eingerichtet. Verwende `!twitch api` oder andere Kommandos, um Einstellungen anzupassen.")
            return
        
        # Grundkonfiguration erstellen oder aktualisieren
        if config:
            await self.db.execute(
                "UPDATE twitch_config SET enabled = 1 WHERE guild_id = ?",
                (str(ctx.guild.id),)
            )
        else:
            await self.db.execute(
                "INSERT INTO twitch_config (guild_id, enabled) VALUES (?, 1)",
                (str(ctx.guild.id),)
            )
        
        # Setup-Anleitung senden
        embed = discord.Embed(
            title="🎮 Twitch-Integration Setup",
            description="Die Twitch-Integration wurde aktiviert! Folge diesen Schritten zum Einrichten:",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="1. API-Zugangsdaten konfigurieren",
            value=(
                "Registriere eine App auf [dev.twitch.tv](https://dev.twitch.tv/console/apps) und führe aus:\n"
                "`!twitch api <client_id> <client_secret>`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="2. Ankündigungskanal festlegen",
            value="`!twitch channel #kanal`",
            inline=False
        )
        
        embed.add_field(
            name="3. Optional: Ping-Rolle festlegen",
            value="`!twitch role @rolle`",
            inline=False
        )
        
        embed.add_field(
            name="4. Streamer hinzufügen",
            value="`!twitch add <streamer_name>`",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @twitch_cmd.command(name="api")
    @is_admin()
    async def set_api_credentials(self, ctx, client_id: str, client_secret: str):
        """Konfiguriert die Twitch API-Zugangsdaten"""
        # Löscht die Nachricht, um die API-Zugangsdaten zu schützen
        try:
            await ctx.message.delete()
        except:
            pass
            
        # In Datenbank speichern
        config = await self.db.fetch_one(
            "SELECT 1 FROM twitch_config WHERE guild_id = ?",
            (str(ctx.guild.id),)
        )
        
        if config:
            await self.db.execute(
                "UPDATE twitch_config SET client_id = ?, client_secret = ? WHERE guild_id = ?",
                (client_id, client_secret, str(ctx.guild.id))
            )
        else:
            await self.db.execute(
                "INSERT INTO twitch_config (guild_id, client_id, client_secret, enabled) VALUES (?, ?, ?, 1)",
                (str(ctx.guild.id), client_id, client_secret)
            )
        
        # API-Zugangsdaten aktualisieren
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Testen der API-Verbindung
        token = await self.get_access_token()
        if token:
            await ctx.send("✅ Twitch API-Zugangsdaten wurden erfolgreich konfiguriert und getestet.")
        else:
            await ctx.send("❌ Fehler bei der Konfiguration der Twitch API-Zugangsdaten. Überprüfe Client-ID und Secret.")
    
    @twitch_cmd.command(name="channel")
    @is_admin()
    async def set_announcement_channel(self, ctx, channel: discord.TextChannel):
        """Legt den Kanal für Stream-Ankündigungen fest"""
        config = await self.db.fetch_one(
            "SELECT 1 FROM twitch_config WHERE guild_id = ?",
            (str(ctx.guild.id),)
        )
        
        if config:
            await self.db.execute(
                "UPDATE twitch_config SET announcement_channel_id = ? WHERE guild_id = ?",
                (str(channel.id), str(ctx.guild.id))
            )
        else:
            await self.db.execute(
                "INSERT INTO twitch_config (guild_id, announcement_channel_id, enabled) VALUES (?, ?, 1)",
                (str(ctx.guild.id), str(channel.id))
            )
        
        await ctx.send(f"✅ Stream-Ankündigungen werden jetzt in {channel.mention} gesendet.")
    
    @twitch_cmd.command(name="message")
    @is_admin()
    async def set_announcement_message(self, ctx, *, message: str):
        """Legt die Nachricht fest, die bei Stream-Start gesendet wird"""
        await self.db.execute(
            "UPDATE twitch_config SET announcement_message = ? WHERE guild_id = ?",
            (message, str(ctx.guild.id))
        )
        
        # Beispielformatierung zeigen
        formatted = message.format(
            streamer="ExampleStreamer",
            title="Mein cooler Stream",
            game="Minecraft",
            url="https://twitch.tv/examplestreamer",
            viewers="42"
        )
        
        await ctx.send(f"✅ Ankündigungsnachricht wurde aktualisiert.\n\nBeispiel:\n{formatted}")
    
    @twitch_cmd.command(name="role")
    @is_admin()
    async def set_ping_role(self, ctx, role: discord.Role = None):
        """Legt die Rolle fest, die bei Stream-Start gepingt wird"""
        if role:
            await self.db.execute(
                "UPDATE twitch_config SET ping_role_id = ? WHERE guild_id = ?",
                (str(role.id), str(ctx.guild.id))
            )
            await ctx.send(f"✅ Die Rolle {role.mention} wird jetzt bei Stream-Ankündigungen gepingt.")
        else:
            await self.db.execute(
                "UPDATE twitch_config SET ping_role_id = NULL WHERE guild_id = ?",
                (str(ctx.guild.id),)
            )
            await ctx.send("✅ Bei Stream-Ankündigungen wird keine Rolle mehr gepingt.")
    
    @twitch_cmd.command(name="add")
    @is_admin()
    async def add_streamer(self, ctx, streamer_name: str):
        """Fügt einen Streamer zur Überwachungsliste hinzu"""
        streamer_name = streamer_name.lower()
        
        # Prüfen, ob Streamer bereits existiert
        exists = await self.db.fetch_one(
            "SELECT 1 FROM twitch_streamers WHERE streamer_name = ? AND guild_id = ?",
            (streamer_name, str(ctx.guild.id))
        )
        
        if exists:
            await ctx.send(f"❌ Der Streamer `{streamer_name}` wird bereits überwacht.")
            return
        
        # Prüfen, ob der Streamer existiert
        token = await self.get_access_token()
        if not token:
            await ctx.send("❌ Konnte kein Twitch-API-Token abrufen. Bitte konfiguriere die API-Zugangsdaten.")
            return
            
        async with aiohttp.ClientSession() as session:
            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {token}"
            }
            
            async with session.get(f"https://api.twitch.tv/helix/users?login={streamer_name}", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data["data"]:
                        await ctx.send(f"❌ Der Streamer `{streamer_name}` wurde auf Twitch nicht gefunden.")
                        return
                    
                    user_id = data["data"][0]["id"]
                    
                    # Streamer zur Datenbank hinzufügen
                    await self.db.execute(
                        "INSERT INTO twitch_streamers (streamer_name, guild_id, user_id) VALUES (?, ?, ?)",
                        (streamer_name, str(ctx.guild.id), user_id)
                    )
                    
                    await ctx.send(f"✅ Der Streamer `{data['data'][0]['display_name']}` wurde zur Überwachungsliste hinzugefügt.")
                else:
                    await ctx.send(f"❌ Fehler beim Suchen des Streamers: HTTP {response.status}")
    
    @twitch_cmd.command(name="remove")
    @is_admin()
    async def remove_streamer(self, ctx, streamer_name: str):
        """Entfernt einen Streamer von der Überwachungsliste"""
        streamer_name = streamer_name.lower()
        
        # Aus Datenbank entfernen
        success = await self.db.execute(
            "DELETE FROM twitch_streamers WHERE streamer_name = ? AND guild_id = ?",
            (streamer_name, str(ctx.guild.id))
        )
        
        # Auch alle Abonnements entfernen
        await self.db.execute(
            "DELETE FROM twitch_subscriptions WHERE streamer_name = ? AND guild_id = ?",
            (streamer_name, str(ctx.guild.id))
        )
        
        # Aus Cache entfernen
        cache_key = f"{ctx.guild.id}:{streamer_name}"
        if cache_key in self.live_streamers:
            del self.live_streamers[cache_key]
        
        await ctx.send(f"✅ Der Streamer `{streamer_name}` wurde von der Überwachungsliste entfernt.")
    
    @twitch_cmd.command(name="list")
    async def list_streamers(self, ctx):
        """Zeigt alle überwachten Streamer und deren Status an"""
        streamers = await self.db.fetch_all(
            "SELECT streamer_name, last_online FROM twitch_streamers WHERE guild_id = ? ORDER BY streamer_name",
            (str(ctx.guild.id),)
        )
        
        if not streamers:
            await ctx.send("❌ Es werden keine Streamer überwacht. Füge welche mit `!twitch add <streamer_name>` hinzu.")
            return
        
        # Status der Streamer abfragen
        token = await self.get_access_token()
        live_streamers = {}
        
        if token:
            try:
                # User-IDs abrufen
                user_ids = []
                streamer_map = {}
                
                for streamer_name, _ in streamers:
                    user_data = await self.db.fetch_one(
                        "SELECT user_id FROM twitch_streamers WHERE streamer_name = ? AND guild_id = ?",
                        (streamer_name, str(ctx.guild.id))
                    )
                    
                    if user_data and user_data[0]:
                        user_ids.append(user_data[0])
                        streamer_map[user_data[0]] = streamer_name
                
                if user_ids:
                    # Streamer-Status abfragen
                    async with aiohttp.ClientSession() as session:
                        headers = {
                            "Client-ID": self.client_id,
                            "Authorization": f"Bearer {token}"
                        }
                        
                        # In Gruppen von maximal 100 abfragen
                        chunks = [user_ids[i:i+100] for i in range(0, len(user_ids), 100)]
                        for chunk in chunks:
                            params = "&".join([f"user_id={uid}" for uid in chunk])
                            async with session.get(f"https://api.twitch.tv/helix/streams?{params}", headers=headers) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    for stream in data["data"]:
                                        user_id = stream["user_id"]
                                        if user_id in streamer_map:
                                            live_streamers[streamer_map[user_id]] = stream
            except Exception as e:
                print(f"Fehler beim Abrufen der Stream-Status: {e}")
        
        # Embed für die Liste erstellen
        embed = discord.Embed(
            title="📺 Überwachte Twitch-Streamer",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        for streamer_name, last_online in streamers:
            # Status bestimmen
            if streamer_name in live_streamers:
                stream = live_streamers[streamer_name]
                status = f"🔴 LIVE: {stream['game_name']} - {stream['viewer_count']} Zuschauer"
                url = f"https://twitch.tv/{streamer_name}"
            else:
                status = "⚫ Offline"
                url = f"https://twitch.tv/{streamer_name}"
                if last_online:
                    try:
                        last_online_dt = datetime.fromisoformat(last_online)
                        status += f" (Zuletzt live: {last_online_dt.strftime('%d.%m.%Y %H:%M')})"
                    except:
                        pass
            
            embed.add_field(
                name=streamer_name,
                value=f"[{status}]({url})",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @twitch_cmd.command(name="subscribe")
    async def subscribe_streamer(self, ctx, streamer_name: str):
        """Abonniert Benachrichtigungen für einen bestimmten Streamer"""
        streamer_name = streamer_name.lower()
        
        # Prüfen, ob Streamer überwacht wird
        exists = await self.db.fetch_one(
            "SELECT 1 FROM twitch_streamers WHERE streamer_name = ? AND guild_id = ?",
            (streamer_name, str(ctx.guild.id))
        )
        
        if not exists:
            await ctx.send(f"❌ Der Streamer `{streamer_name}` wird nicht überwacht. Ein Administrator muss ihn zuerst mit `!twitch add {streamer_name}` hinzufügen.")
            return
        
        # Prüfen, ob bereits abonniert
        already_subbed = await self.db.fetch_one(
            "SELECT 1 FROM twitch_subscriptions WHERE user_id = ? AND guild_id = ? AND streamer_name = ?",
            (str(ctx.author.id), str(ctx.guild.id), streamer_name)
        )
        
        if already_subbed:
            await ctx.send(f"❌ Du hast den Streamer `{streamer_name}` bereits abonniert.")
            return
        
        # Abonnement hinzufügen
        await self.db.execute(
            "INSERT INTO twitch_subscriptions (user_id, guild_id, streamer_name) VALUES (?, ?, ?)",
            (str(ctx.author.id), str(ctx.guild.id), streamer_name)
        )
        
        await ctx.send(f"✅ Du erhältst jetzt Benachrichtigungen, wenn `{streamer_name}` live geht.")
    
    @twitch_cmd.command(name="unsubscribe")
    async def unsubscribe_streamer(self, ctx, streamer_name: str):
        """Meldet sich von Benachrichtigungen für einen Streamer ab"""
        streamer_name = streamer_name.lower()
        
        # Abonnement entfernen
        success = await self.db.execute(
            "DELETE FROM twitch_subscriptions WHERE user_id = ? AND guild_id = ? AND streamer_name = ?",
            (str(ctx.author.id), str(ctx.guild.id), streamer_name)
        )
        
        await ctx.send(f"✅ Du erhältst keine Benachrichtigungen mehr für `{streamer_name}`.")
    
    @twitch_cmd.command(name="mysubs")
    async def list_subscriptions(self, ctx):
        """Zeigt alle abonnierten Streamer des Nutzers an"""
        subs = await self.db.fetch_all(
            "SELECT ts.streamer_name FROM twitch_subscriptions ts " +
            "JOIN twitch_streamers tst ON ts.streamer_name = tst.streamer_name AND ts.guild_id = tst.guild_id " +
            "WHERE ts.user_id = ? AND ts.guild_id = ?",
            (str(ctx.author.id), str(ctx.guild.id))
        )
        
        if not subs:
            await ctx.send("❌ Du hast keine Streamer abonniert. Nutze `!twitch subscribe <streamer_name>` zum Abonnieren.")
            return
        
        streamer_list = "\n".join([f"• [`{sub[0]}`](https://twitch.tv/{sub[0]})" for sub in subs])
        
        embed = discord.Embed(
            title="📬 Deine Twitch-Abonnements",
            description=f"Du erhältst Benachrichtigungen für diese Streamer:\n\n{streamer_list}",
            color=discord.Color.purple()
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Fügt die Twitch-Integration zum Bot hinzu"""
    await bot.add_cog(TwitchIntegration(bot)) 