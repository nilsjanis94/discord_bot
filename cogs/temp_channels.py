import discord
from discord.ext import commands
import asyncio
import sys
import os
import sqlite3

# Füge das Hauptverzeichnis zum Pfad hinzu, damit wir utils importieren können
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db import Database
from utils.permissions import is_admin

class TempChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Verwende die DB-Klasse statt direkter SQLite-Verbindung
        self.db = Database()
        
        # Korrekter Variablenname
        self.active_channels = {}
        self.creator_channels = {}
        self.bot.loop.create_task(self.initialize_database())
        self.bot.loop.create_task(self.load_creator_channels())
        self.bot.loop.create_task(self.check_empty_channels())
    
    async def initialize_database(self):
        """Initialisiert die Datenbanktabellen"""
        # Warte, bis der Bot bereit ist
        await self.bot.wait_until_ready()
        
        # Erstelle die Tabellen, falls sie nicht existieren
        await self.db.execute('''
        CREATE TABLE IF NOT EXISTS temp_voice_config (
            guild_id INTEGER PRIMARY KEY,
            creator_channel_id INTEGER,
            category_id INTEGER,
            user_limit INTEGER DEFAULT 1,
            default_privacy TEXT DEFAULT 'public'
        )
        ''')
        
        await self.db.execute('''
        CREATE TABLE IF NOT EXISTS temp_voice_channels (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            owner_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            privacy TEXT DEFAULT 'public'
        )
        ''')
        
        print("✅ Temporäre Kanäle Datenbanktabellen initialisiert")
    
    async def load_creator_channels(self):
        """Lädt die Erstellungskanäle aus der Datenbank."""
        await asyncio.sleep(1)  # Warte kurz, bis der Bot vollständig gestartet ist
        
        try:
            # Verwende die richtige Methode für die DB-Klasse
            results = await self.db.fetch_all(
                "SELECT guild_id, creator_channel_id, category_id, user_limit, default_privacy FROM temp_voice_config"
            )
        except Exception as e:
            print(f"Fehler beim Laden der Erstellungskanäle: {e}")
            # Versuche alternative Spaltennamen
            try:
                results = await self.db.fetch_all(
                    "SELECT guild_id, channel_id, category_id, max_per_user, default_privacy FROM temp_voice_config"
                )
            except Exception as e2:
                print(f"Alternativer Versuch fehlgeschlagen: {e2}")
                results = []
        
        for row in results:
            guild_id, creator_channel_id, category_id, user_limit, default_privacy = row
            self.creator_channels[creator_channel_id] = {
                "guild_id": guild_id,
                "category_id": category_id,
                "user_limit": user_limit,
                "default_privacy": default_privacy
            }
        
        try:
            # Lade auch aktive Kanäle
            active_channels = await self.db.fetch_all(
                "SELECT channel_id, guild_id, owner_id, privacy FROM temp_voice_channels"
            )
        except Exception as e:
            print(f"Fehler beim Laden der aktiven Kanäle: {e}")
            # Versuche alternative Spaltennamen
            try:
                active_channels = await self.db.fetch_all(
                    "SELECT channel_id, guild_id, creator_id, privacy FROM temp_voice_channels"
                )
            except Exception as e2:
                print(f"Alternativer Versuch fehlgeschlagen: {e2}")
                active_channels = []
        
        for row in active_channels:
            channel_id, guild_id, owner_id, privacy = row
            self.active_channels[channel_id] = {
                "guild_id": guild_id,
                "owner_id": owner_id,
                "privacy": privacy
            }
        
        print(f"✅ Temporäre Kanäle geladen: {len(self.creator_channels)} Erstellungskanäle, {len(self.active_channels)} aktive temporäre Kanäle")
    
    async def check_empty_channels(self):
        """Überprüft regelmäßig, ob temporäre Kanäle leer sind und löscht sie gegebenenfalls."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                # Verwende active_channels statt temp_channels
                for channel_id in list(self.active_channels.keys()):
                    channel = self.bot.get_channel(channel_id)
                    if channel is None:
                        # Kanal existiert nicht mehr, entferne ihn aus der Datenbank
                        await self.db.execute(
                            "DELETE FROM temp_voice_channels WHERE channel_id = ?",
                            (channel_id,)
                        )
                        self.active_channels.pop(channel_id, None)
                    elif len(channel.members) == 0:
                        # Kanal ist leer, lösche ihn
                        await channel.delete(reason="Temporärer Sprachkanal ist leer")
                        await self.db.execute(
                            "DELETE FROM temp_voice_channels WHERE channel_id = ?",
                            (channel_id,)
                        )
                        self.active_channels.pop(channel_id, None)
            except Exception as e:
                print(f"Fehler beim Überprüfen leerer Kanäle: {e}")
            
            await asyncio.sleep(60)  # Überprüfe alle 60 Sekunden
    
    async def is_channel_owner(self, ctx, channel_id=None):
        """Überprüft, ob der Benutzer der Besitzer des Kanals ist"""
        channel_id = channel_id or ctx.author.voice.channel.id if ctx.author.voice else None
        
        if not channel_id:
            await ctx.send("❌ Du bist in keinem Sprachkanal!")
            return False
        
        if channel_id not in self.active_channels:
            await ctx.send("❌ Dies ist kein temporärer Sprachkanal!")
            return False
        
        if self.active_channels[channel_id]["owner_id"] != ctx.author.id:
            await ctx.send("❌ Du bist nicht der Besitzer dieses Kanals!")
            return False
        
        return True
    
    @commands.group(name="tempvoice", aliases=["tv"], invoke_without_command=True)
    async def temp_voice(self, ctx):
        """Temporäre Sprachkanäle verwalten"""
        embed = discord.Embed(
            title="🔊 Temporäre Sprachkanäle",
            description="Mit diesem System können Benutzer eigene temporäre Sprachkanäle erstellen und verwalten.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Admin-Befehle",
            value="`!tempvoice setup` - Richtet das System ein\n"
                  "`!tempvoice category <name>` - Setzt die Kategorie\n"
                  "`!tempvoice limit <anzahl>` - Setzt das Limit pro Benutzer\n"
                  "`!tempvoice list` - Zeigt alle temporären Kanäle",
            inline=False
        )
        
        embed.add_field(
            name="Benutzer-Befehle",
            value="`!tv name <name>` - Ändert den Namen deines Kanals\n"
                  "`!tv userlimit <anzahl>` - Setzt das Benutzerlimit (0 = unbegrenzt)\n"
                  "`!tv privacy <public/locked/hidden>` - Setzt die Privatsphäre-Einstellung\n"
                  "`!tv kick @user` - Kickt einen Benutzer aus deinem Kanal\n"
                  "`!tv invite @user` - Lädt einen Benutzer in deinen Kanal ein",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @temp_voice.command(name="setup")
    @is_admin()
    async def setup_temp_voice(self, ctx, *, channel_name: str = "➕ Erstelle Sprachkanal"):
        """Richtet das System für temporäre Sprachkanäle ein"""
        # Erstelle Kategorie falls nicht vorhanden
        category = discord.utils.get(ctx.guild.categories, name="Temporäre Kanäle")
        if not category:
            category = await ctx.guild.create_category("Temporäre Kanäle")
        
        # Erstelle den Erstellungskanal
        channel = await ctx.guild.create_voice_channel(
            name=channel_name,
            category=category
        )
        
        # Überprüfe die Spalten in der Datenbank
        try:
            # Speichere in der Datenbank
            await self.db.execute(
                '''
                INSERT OR REPLACE INTO temp_voice_config 
                (guild_id, creator_channel_id, category_id, user_limit, default_privacy) 
                VALUES (?, ?, ?, ?, ?)
                ''',
                (str(ctx.guild.id), str(channel.id), str(category.id), "3", "public")
            )
        except Exception as e:
            print(f"Fehler beim Speichern in der Datenbank: {e}")
            # Versuche alternative Spaltennamen
            try:
                await self.db.execute(
                    '''
                    INSERT OR REPLACE INTO temp_voice_config 
                    (guild_id, channel_id, category_id, max_per_user, default_privacy) 
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (str(ctx.guild.id), str(channel.id), str(category.id), "3", "public")
                )
            except Exception as e2:
                print(f"Alternativer Versuch fehlgeschlagen: {e2}")
                await ctx.send("❌ Fehler beim Einrichten des Systems. Bitte kontaktiere den Administrator.")
                return
        
        # Aktualisiere das Dictionary
        self.creator_channels[channel.id] = {
            "guild_id": ctx.guild.id,
            "category_id": category.id,
            "user_limit": 3,
            "default_privacy": "public"
        }
        
        embed = discord.Embed(
            title="✅ Temporäre Sprachkanäle eingerichtet",
            description=f"Das System wurde erfolgreich eingerichtet!\n\n"
                        f"Erstellungskanal: {channel.mention}\n"
                        f"Kategorie: {category.name}\n"
                        f"Standard-Privatsphäre: `public`",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Verwendung",
            value="Benutzer können dem Kanal beitreten, um automatisch einen eigenen temporären Sprachkanal zu erstellen.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @temp_voice.command(name="category")
    @is_admin()
    async def set_category(self, ctx, *, category_name: str):
        """Setzt die Kategorie für temporäre Sprachkanäle"""
        # Prüfe, ob das System eingerichtet ist
        if ctx.guild.id not in self.creator_channels:
            return await ctx.send("❌ Das System für temporäre Sprachkanäle ist noch nicht eingerichtet. Nutze `!tempvoice setup`.")
        
        # Erstelle oder finde die Kategorie
        category = discord.utils.get(ctx.guild.categories, name=category_name)
        if not category:
            category = await ctx.guild.create_category(category_name)
        
        # Aktualisiere in der Datenbank
        await self.db.execute(
            'UPDATE temp_voice_config SET category_id = ? WHERE guild_id = ?',
            (str(category.id), str(ctx.guild.id))
        )
        
        await ctx.send(f"✅ Kategorie für temporäre Sprachkanäle wurde auf `{category_name}` gesetzt!")
    
    @temp_voice.command(name="limit")
    @is_admin()
    async def set_limit(self, ctx, limit: int):
        """Setzt das Limit für temporäre Kanäle pro Benutzer"""
        # Prüfe, ob das System eingerichtet ist
        if ctx.guild.id not in self.creator_channels:
            return await ctx.send("❌ Das System für temporäre Sprachkanäle ist noch nicht eingerichtet. Nutze `!tempvoice setup`.")
        
        if limit < 1 or limit > 10:
            return await ctx.send("❌ Das Limit muss zwischen 1 und 10 liegen.")
        
        # Aktualisiere in der Datenbank
        await self.db.execute(
            'UPDATE temp_voice_config SET user_limit = ? WHERE guild_id = ?',
            (str(limit), str(ctx.guild.id))
        )
        
        await ctx.send(f"✅ Limit für temporäre Sprachkanäle pro Benutzer wurde auf `{limit}` gesetzt!")
    
    @temp_voice.command(name="defaultprivacy")
    @is_admin()
    async def set_default_privacy(self, ctx, privacy: str):
        """Setzt die Standard-Privatsphäre-Einstellung für neue Kanäle (public, locked, hidden)"""
        # Prüfe, ob das System eingerichtet ist
        if ctx.guild.id not in self.creator_channels:
            return await ctx.send("❌ Das System für temporäre Sprachkanäle ist noch nicht eingerichtet. Nutze `!tempvoice setup`.")
        
        privacy = privacy.lower()
        if privacy not in ["public", "locked", "hidden"]:
            return await ctx.send("❌ Gültige Einstellungen sind: `public`, `locked`, `hidden`")
        
        # Aktualisiere in der Datenbank
        await self.db.execute(
            'UPDATE temp_voice_config SET default_privacy = ? WHERE guild_id = ?',
            (privacy, str(ctx.guild.id))
        )
        
        await ctx.send(f"✅ Standard-Privatsphäre für neue temporäre Kanäle wurde auf `{privacy}` gesetzt!")
    
    @temp_voice.command(name="list")
    @is_admin()
    async def list_temp_channels(self, ctx):
        """Listet alle aktiven temporären Sprachkanäle auf"""
        # Filtere Kanäle für diesen Server
        guild_channels = {}
        
        for channel_id, data in self.active_channels.items():
            channel = self.bot.get_channel(channel_id)
            if channel and channel.guild.id == ctx.guild.id:
                creator = ctx.guild.get_member(data["owner_id"])
                creator_name = creator.name if creator else "Unbekannt"
                guild_channels[channel_id] = {
                    "name": channel.name,
                    "creator": creator_name,
                    "members": len(channel.members)
                }
        
        if not guild_channels:
            return await ctx.send("❌ Es gibt derzeit keine aktiven temporären Sprachkanäle.")
        
        embed = discord.Embed(
            title="🔊 Aktive temporäre Sprachkanäle",
            color=discord.Color.blue()
        )
        
        for channel_id, data in guild_channels.items():
            embed.add_field(
                name=data["name"],
                value=f"Ersteller: {data['creator']}\n"
                      f"Mitglieder: {data['members']}\n"
                      f"ID: {channel_id}",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    # Benutzer-Befehle für Kanalverwaltung
    
    @temp_voice.command(name="name")
    async def change_name(self, ctx, *, new_name: str):
        """Ändert den Namen deines temporären Sprachkanals"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ Du musst in deinem Sprachkanal sein, um seinen Namen zu ändern!")
        
        channel_id = ctx.author.voice.channel.id
        
        # Prüfe, ob der Benutzer der Besitzer ist
        if not await self.is_channel_owner(ctx, channel_id):
            return
        
        # Ändere den Namen
        try:
            await ctx.author.voice.channel.edit(name=new_name)
            await ctx.send(f"✅ Der Name deines Kanals wurde zu `{new_name}` geändert!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Ändern des Namens: {e}")
    
    @temp_voice.command(name="userlimit", aliases=["maxusers", "max"])
    async def set_user_limit(self, ctx, limit: int):
        """Setzt das Benutzerlimit für deinen temporären Sprachkanal"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ Du musst in deinem Sprachkanal sein, um das Limit zu ändern!")
        
        channel_id = ctx.author.voice.channel.id
        
        # Prüfe, ob der Benutzer der Besitzer ist
        if not await self.is_channel_owner(ctx, channel_id):
            return
        
        if limit < 0 or limit > 99:
            return await ctx.send("❌ Das Limit muss zwischen 0 und 99 liegen (0 = unbegrenzt).")
        
        # Ändere das Limit
        try:
            await ctx.author.voice.channel.edit(user_limit=limit)
            limit_text = "unbegrenzt" if limit == 0 else str(limit)
            await ctx.send(f"✅ Das Benutzerlimit deines Kanals wurde auf `{limit_text}` gesetzt!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Ändern des Limits: {e}")
    
    @temp_voice.command(name="privacy")
    async def set_privacy(self, ctx, mode: str):
        """Setzt die Privatsphäre-Einstellung deines Kanals (public, locked, hidden)"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ Du musst in deinem Sprachkanal sein, um die Privatsphäre zu ändern!")
        
        channel_id = ctx.author.voice.channel.id
        
        # Prüfe, ob der Benutzer der Besitzer ist
        if not await self.is_channel_owner(ctx, channel_id):
            return
        
        mode = mode.lower()
        if mode not in ["public", "locked", "hidden"]:
            return await ctx.send("❌ Gültige Modi sind: `public`, `locked`, `hidden`")
        
        # Ändere die Privatsphäre-Einstellung
        try:
            overwrites = ctx.author.voice.channel.overwrites
            
            if mode == "public":
                # Öffentlich: Jeder kann sehen und beitreten
                if ctx.guild.default_role in overwrites:
                    overwrites[ctx.guild.default_role].connect = None
                    overwrites[ctx.guild.default_role].view_channel = None
                    if overwrites[ctx.guild.default_role].is_empty():
                        overwrites.pop(ctx.guild.default_role)
            
            elif mode == "locked":
                # Gesperrt: Jeder kann sehen, aber nicht beitreten
                overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(
                    connect=False,
                    view_channel=True
                )
            
            elif mode == "hidden":
                # Versteckt: Niemand kann sehen oder beitreten
                overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(
                    connect=False,
                    view_channel=False
                )
            
            await ctx.author.voice.channel.edit(overwrites=overwrites)
            
            # Sende eine Bestätigungsnachricht mit Erklärung
            privacy_info = {
                "public": "Jeder kann deinen Kanal sehen und beitreten",
                "locked": "Jeder kann deinen Kanal sehen, aber nur eingeladene Benutzer können beitreten",
                "hidden": "Nur eingeladene Benutzer können deinen Kanal sehen und beitreten"
            }
            
            embed = discord.Embed(
                title=f"✅ Privatsphäre-Einstellung: {mode.capitalize()}",
                description=privacy_info[mode],
                color=discord.Color.green()
            )
            
            if mode != "public":
                embed.add_field(
                    name="Benutzer einladen",
                    value="Nutze `!tv invite @user`, um Benutzer in deinen Kanal einzuladen.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Ändern der Privatsphäre: {e}")
    
    @temp_voice.command(name="kick")
    async def kick_user(self, ctx, member: discord.Member):
        """Kickt einen Benutzer aus deinem temporären Sprachkanal"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ Du musst in deinem Sprachkanal sein, um Benutzer zu kicken!")
        
        channel_id = ctx.author.voice.channel.id
        
        # Prüfe, ob der Benutzer der Besitzer ist
        if not await self.is_channel_owner(ctx, channel_id):
            return
        
        # Prüfe, ob der zu kickende Benutzer im Kanal ist
        if not member.voice or member.voice.channel.id != channel_id:
            return await ctx.send("❌ Dieser Benutzer ist nicht in deinem Kanal!")
        
        # Kicke den Benutzer
        try:
            await member.move_to(None)
            
            # Verhindere, dass der Benutzer wieder beitreten kann
            overwrites = ctx.author.voice.channel.overwrites
            overwrites[member] = discord.PermissionOverwrite(connect=False)
            await ctx.author.voice.channel.edit(overwrites=overwrites)
            
            await ctx.send(f"👢 {member.mention} wurde aus deinem Kanal gekickt!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Kicken des Benutzers: {e}")
    
    @temp_voice.command(name="invite")
    async def invite_user(self, ctx, member: discord.Member):
        """Lädt einen Benutzer in deinen gesperrten temporären Sprachkanal ein"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ Du musst in deinem Sprachkanal sein, um Benutzer einzuladen!")
        
        channel_id = ctx.author.voice.channel.id
        
        # Prüfe, ob der Benutzer der Besitzer ist
        if not await self.is_channel_owner(ctx, channel_id):
            return
        
        # Erlaube dem Benutzer den Zugriff
        try:
            overwrites = ctx.author.voice.channel.overwrites
            overwrites[member] = discord.PermissionOverwrite(connect=True, view_channel=True)
            await ctx.author.voice.channel.edit(overwrites=overwrites)
            
            await ctx.send(f"✉️ {member.mention} wurde in deinen Kanal eingeladen!")
            
            # Sende eine DM an den eingeladenen Benutzer
            try:
                embed = discord.Embed(
                    title="🔊 Kanaleinladung",
                    description=f"{ctx.author.name} hat dich in seinen Sprachkanal eingeladen!",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Kanal",
                    value=ctx.author.voice.channel.name,
                    inline=False
                )
                embed.add_field(
                    name="Server",
                    value=ctx.guild.name,
                    inline=False
                )
                await member.send(embed=embed)
            except discord.HTTPException:
                pass  # Ignoriere Fehler beim Senden der DM
            
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Einladen des Benutzers: {e}")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Event-Handler für Sprachkanal-Änderungen"""
        # Ignoriere Bots
        if member.bot:
            return
        
        # Prüfe, ob der Benutzer einem Erstellungskanal beigetreten ist
        if after.channel and after.channel.id in self.creator_channels:
            # Hole Konfiguration aus der Datenbank
            result = await self.db.fetch_one(
                'SELECT category_id, user_limit, default_privacy FROM temp_voice_config WHERE guild_id = ?',
                (str(member.guild.id),)
            )
            
            if not result:
                return
            
            category_id, user_limit, default_privacy = result
            category = member.guild.get_channel(int(category_id))
            
            # Prüfe, ob der Benutzer das Limit erreicht hat
            user_channels = 0
            for creator_id in self.creator_channels.values():
                if creator_id["guild_id"] == member.guild.id:
                    user_channels += 1
            
            if user_channels >= int(user_limit):
                # Entferne den Benutzer aus dem Kanal
                try:
                    await member.move_to(None)
                    await member.send(f"❌ Du hast das Limit von {user_limit} temporären Kanälen erreicht!")
                except discord.HTTPException:
                    pass
                return
            
            # Erstelle einen neuen temporären Kanal
            channel_name = f"🔊 {member.name}'s Kanal"
            
            try:
                new_channel = await member.guild.create_voice_channel(
                    name=channel_name,
                    category=category,
                    user_limit=0  # Kein Limit
                )
                
                # Setze Berechtigungen basierend auf der Standard-Privatsphäre-Einstellung
                overwrites = {
                    member: discord.PermissionOverwrite(
                        connect=True,
                        view_channel=True,
                        manage_channels=True,
                        move_members=True,
                        mute_members=True,
                        deafen_members=True
                    )
                }
                
                if default_privacy == "locked":
                    # Gesperrt: Jeder kann sehen, aber nicht beitreten
                    overwrites[member.guild.default_role] = discord.PermissionOverwrite(
                        connect=False,
                        view_channel=True
                    )
                elif default_privacy == "hidden":
                    # Versteckt: Niemand kann sehen oder beitreten
                    overwrites[member.guild.default_role] = discord.PermissionOverwrite(
                        connect=False,
                        view_channel=False
                    )
                # Bei "public" werden keine speziellen Berechtigungen für die Standardrolle gesetzt
                
                await new_channel.edit(overwrites=overwrites)
                
                # Bewege den Benutzer in den neuen Kanal
                await member.move_to(new_channel)
                
                # Speichere den Kanal in der Datenbank
                try:
                    await self.db.execute(
                        '''
                        INSERT INTO temp_voice_channels 
                        (channel_id, guild_id, owner_id, privacy) 
                        VALUES (?, ?, ?, ?)
                        ''',
                        (str(new_channel.id), str(member.guild.id), str(member.id), default_privacy)
                    )
                except Exception as e:
                    print(f"Fehler beim Speichern des Kanals in der Datenbank: {e}")
                    # Versuche alternative Spaltennamen
                    try:
                        await self.db.execute(
                            '''
                            INSERT INTO temp_voice_channels 
                            (channel_id, guild_id, creator_id, privacy) 
                            VALUES (?, ?, ?, ?)
                            ''',
                            (str(new_channel.id), str(member.guild.id), str(member.id), default_privacy)
                        )
                    except Exception as e2:
                        print(f"Alternativer Versuch fehlgeschlagen: {e2}")
                
                # Aktualisiere das Dictionary
                self.active_channels[new_channel.id] = {
                    "guild_id": member.guild.id,
                    "owner_id": member.id,
                    "privacy": default_privacy
                }
                
                print(f"✅ Temporärer Kanal {channel_name} erstellt von {member.name} (Privatsphäre: {default_privacy})")
                
                # Sende eine Willkommensnachricht
                try:
                    embed = discord.Embed(
                        title="🔊 Dein temporärer Sprachkanal",
                        description="Du hast einen temporären Sprachkanal erstellt! Hier sind einige Befehle, die du verwenden kannst:",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name="Befehle",
                        value="`!tv name <name>` - Ändert den Namen deines Kanals\n"
                              "`!tv userlimit <anzahl>` - Setzt das Benutzerlimit (0 = unbegrenzt)\n"
                              "`!tv privacy <public/locked/hidden>` - Setzt die Privatsphäre-Einstellung\n"
                              "`!tv kick @user` - Kickt einen Benutzer aus deinem Kanal\n"
                              "`!tv invite @user` - Lädt einen Benutzer in deinen Kanal ein",
                        inline=False
                    )
                    
                    # Füge Informationen zur aktuellen Privatsphäre-Einstellung hinzu
                    privacy_info = {
                        "public": "Jeder kann deinen Kanal sehen und beitreten",
                        "locked": "Jeder kann deinen Kanal sehen, aber nur eingeladene Benutzer können beitreten",
                        "hidden": "Nur eingeladene Benutzer können deinen Kanal sehen und beitreten"
                    }
                    
                    embed.add_field(
                        name=f"Aktuelle Privatsphäre: {default_privacy.capitalize()}",
                        value=privacy_info[default_privacy],
                        inline=False
                    )
                    
                    await member.send(embed=embed)
                except discord.HTTPException:
                    pass  # Ignoriere Fehler beim Senden der DM
                
            except discord.HTTPException as e:
                print(f"❌ Fehler beim Erstellen des temporären Kanals: {e}")
        
        # Prüfe, ob ein temporärer Kanal leer geworden ist
        if before.channel and before.channel.id in self.active_channels:
            if len(before.channel.members) == 0:
                try:
                    await before.channel.delete(reason="Temporärer Kanal ist leer")
                    print(f"🗑️ Temporärer Kanal {before.channel.name} gelöscht (leer)")
                    
                    # Lösche aus der Datenbank
                    await self.db.execute(
                        "DELETE FROM temp_voice_channels WHERE channel_id = ?",
                        (before.channel.id,)
                    )
                    
                    # Entferne aus dem Dictionary
                    self.active_channels.pop(before.channel.id, None)
                    
                except discord.HTTPException as e:
                    print(f"❌ Fehler beim Löschen des Kanals {before.channel.id}: {e}")

async def setup(bot):
    # Überprüfe, ob die Tabellen bereits existieren, bevor du sie erstellst
    db = Database()
    
    # Prüfe, ob die Tabellen existieren
    try:
        await db.fetch_one("SELECT 1 FROM temp_voice_config LIMIT 1")
        print("✅ Tabelle temp_voice_config existiert bereits")
    except Exception:
        print("⚠️ Erstelle Tabelle temp_voice_config...")
        await db.execute('''
            CREATE TABLE IF NOT EXISTS temp_voice_config (
                guild_id INTEGER PRIMARY KEY,
                creator_channel_id INTEGER,
                category_id INTEGER,
                user_limit INTEGER DEFAULT 1,
                default_privacy TEXT DEFAULT 'public'
            )
        ''')
    
    try:
        await db.fetch_one("SELECT 1 FROM temp_voice_channels LIMIT 1")
        print("✅ Tabelle temp_voice_channels existiert bereits")
    except Exception:
        print("⚠️ Erstelle Tabelle temp_voice_channels...")
        await db.execute('''
            CREATE TABLE IF NOT EXISTS temp_voice_channels (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                owner_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                privacy TEXT DEFAULT 'public'
            )
        ''')
    
    await bot.add_cog(TempChannels(bot)) 