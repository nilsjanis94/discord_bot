import discord
from discord.ext import commands
from utils.automod import AutoMod
from typing import Optional, Union
import re
import asyncio
from utils.permissions import is_admin

class AutoModCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.automod = AutoMod(bot)
    
    async def cog_load(self):
        """Wird beim Laden der Cog ausgeführt"""
        try:
            # Initialisiere AutoMod
            await self.automod.setup(self.bot)
            print("✅ AutoMod wurde initialisiert")
        except Exception as e:
            print(f"❌ Fehler beim Initialisieren von AutoMod: {e}")
        
        # Füge den Event-Listener für Nachrichten hinzu
        self.bot.add_listener(self.on_message, "on_message")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Verarbeitet eingehende Nachrichten für AutoMod"""
        # Ignoriere Bot-Nachrichten und DMs
        if message.author.bot or not message.guild:
            return
            
        try:
            # Verarbeite die Nachricht mit AutoMod
            violation_type = await self.automod.process_message(message)
            
            # Wenn ein Verstoß erkannt wurde, führe eine Aktion aus
            if violation_type:
                print(f"🚨 AutoMod-Verstoß erkannt: {violation_type} von {message.author.name}")
                await self.automod.take_action(message, violation_type)
        except Exception as e:
            print(f"❌ Fehler bei der AutoMod-Verarbeitung: {e}")
    
    @commands.group(name="automod", invoke_without_command=True)
    @is_admin()
    async def automod(self, ctx):
        """Hauptbefehl für AutoMod-Konfiguration"""
        embed = discord.Embed(
            title="🤖 AutoMod-Konfiguration",
            description="Verwende die folgenden Befehle, um AutoMod zu konfigurieren:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Grundeinstellungen",
            value=(
                "`!automod enable` - Aktiviert AutoMod\n"
                "`!automod disable` - Deaktiviert AutoMod\n"
                "`!automod status` - Zeigt den aktuellen Status\n"
                "`!automod log #kanal` - Setzt den Log-Kanal"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Filter",
            value=(
                "`!automod spam <an/aus> [schwelle] [interval]` - Spam-Filter\n"
                "`!automod links <an/aus>` - Link-Filter\n"
                "`!automod caps <an/aus> [schwelle]` - CAPS-Filter\n"
                "`!automod emoji <an/aus> [schwelle]` - Emoji-Filter\n"
                "`!automod flood <an/aus> [nachrichten] [sekunden]` - Flood-Filter"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Wort-Filter",
            value=(
                "`!automod addword <wort>` - Fügt ein Wort zum Filter hinzu\n"
                "`!automod delword <wort>` - Entfernt ein Wort vom Filter\n"
                "`!automod words` - Zeigt alle gefilterten Wörter"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Link-Filter",
            value=(
                "`!automod addlink <link>` - Fügt einen Link zum Filter hinzu\n"
                "`!automod dellink <link>` - Entfernt einen Link vom Filter\n"
                "`!automod links` - Zeigt alle gefilterten Links"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Whitelist",
            value=(
                "`!automod whitelist role @rolle` - Fügt eine Rolle zur Whitelist hinzu\n"
                "`!automod whitelist channel #kanal` - Fügt einen Kanal zur Whitelist hinzu\n"
                "`!automod whitelist list` - Zeigt alle Whitelist-Einträge"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @automod.command(name="enable")
    @is_admin()
    async def automod_enable(self, ctx):
        """Aktiviert AutoMod für diesen Server"""
        await self.automod.enable(ctx.guild.id)
        
        embed = discord.Embed(
            title="✅ AutoMod aktiviert",
            description="AutoMod ist jetzt für diesen Server aktiviert.",
            color=discord.Color.green()
        )
        
        # Prüfe, ob ein Log-Kanal konfiguriert ist
        if ctx.guild.id not in self.automod.log_channels:
            embed.add_field(
                name="⚠️ Hinweis",
                value="Es ist noch kein Log-Kanal konfiguriert. Verwende `!automod log #kanal`, um einen Log-Kanal festzulegen.",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @automod.command(name="disable")
    @is_admin()
    async def automod_disable(self, ctx):
        """Deaktiviert AutoMod für diesen Server"""
        await self.automod.disable(ctx.guild.id)
        
        embed = discord.Embed(
            title="🛑 AutoMod deaktiviert",
            description="AutoMod ist jetzt für diesen Server deaktiviert.",
            color=discord.Color.red()
        )
        
        await ctx.send(embed=embed)
    
    @automod.command(name="status")
    @is_admin()
    async def automod_status(self, ctx):
        """Zeigt den aktuellen Status von AutoMod"""
        status = await self.automod.get_status(ctx.guild.id)
        
        embed = discord.Embed(
            title="🤖 AutoMod-Status",
            color=discord.Color.blue()
        )
        
        # Aktivierungsstatus
        embed.add_field(
            name="Status",
            value="✅ Aktiviert" if status["enabled"] else "❌ Deaktiviert",
            inline=False
        )
        
        # Log-Kanal
        log_channel = ctx.guild.get_channel(status["log_channel"]) if status["log_channel"] else None
        embed.add_field(
            name="Log-Kanal",
            value=log_channel.mention if log_channel else "Nicht konfiguriert",
            inline=False
        )
        
        # Filter-Einstellungen
        filter_status = []
        
        # Spam-Filter
        spam_messages, spam_interval = status["spam_settings"]
        filter_status.append(f"**Spam-Filter:** {spam_messages} Nachrichten in {spam_interval} Sekunden")
        
        # CAPS-Filter
        filter_status.append(f"**CAPS-Filter:** {int(status['caps_threshold'] * 100)}% Großbuchstaben")
        
        # Emoji-Filter
        filter_status.append(f"**Emoji-Filter:** {int(status['emoji_threshold'] * 100)}% Emojis")
        
        # Flood-Filter
        flood_messages, flood_interval = status["flood_settings"]
        filter_status.append(f"**Flood-Filter:** {flood_messages} gleiche Nachrichten in {flood_interval} Sekunden")
        
        embed.add_field(
            name="Filter-Einstellungen",
            value="\n".join(filter_status),
            inline=False
        )
        
        # Wort- und Link-Filter
        embed.add_field(
            name="Wort- und Link-Filter",
            value=(
                f"**Gefilterte Wörter:** {status['banned_words_count']}\n"
                f"**Gefilterte Links:** {status['banned_links_count']}"
            ),
            inline=False
        )
        
        # Whitelist
        whitelist_info = []
        
        # Rollen
        whitelisted_roles = [ctx.guild.get_role(role_id) for role_id in status["whitelisted_roles"]]
        whitelisted_roles = [role.mention for role in whitelisted_roles if role]
        whitelist_info.append(f"**Rollen:** {', '.join(whitelisted_roles) if whitelisted_roles else 'Keine'}")
        
        # Kanäle
        whitelisted_channels = [ctx.guild.get_channel(channel_id) for channel_id in status["whitelisted_channels"]]
        whitelisted_channels = [channel.mention for channel in whitelisted_channels if channel]
        whitelist_info.append(f"**Kanäle:** {', '.join(whitelisted_channels) if whitelisted_channels else 'Keine'}")
        
        embed.add_field(
            name="Whitelist",
            value="\n".join(whitelist_info),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @automod.command(name="log")
    @is_admin()
    async def automod_log(self, ctx, channel: discord.TextChannel):
        """Setzt den Log-Kanal für AutoMod"""
        await self.automod.set_log_channel(ctx.guild.id, channel.id)
        
        embed = discord.Embed(
            title="✅ Log-Kanal gesetzt",
            description=f"AutoMod-Logs werden jetzt in {channel.mention} gesendet.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @automod.command(name="spam")
    @is_admin()
    async def automod_spam(self, ctx, status: str, messages: Optional[int] = None, interval: Optional[int] = None):
        """Konfiguriert den Spam-Filter"""
        if status.lower() not in ["an", "aus", "on", "off"]:
            await ctx.send("❌ Status muss 'an' oder 'aus' sein!")
            return
        
        guild_id = ctx.guild.id
        
        if status.lower() in ["an", "on"]:
            # Setze Standardwerte, falls nicht angegeben
            if messages is None:
                messages = 5
            if interval is None:
                interval = 3
                
            # Setze Spam-Einstellungen
            await self.automod.set_spam_settings(guild_id, messages, interval)
            
            embed = discord.Embed(
                title="✅ Spam-Filter aktiviert",
                description=f"Der Spam-Filter wurde mit {messages} Nachrichten in {interval} Sekunden konfiguriert.",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
        else:
            # Deaktiviere Spam-Filter durch sehr hohe Werte
            await self.automod.set_spam_settings(guild_id, 9999, 1)
            
            embed = discord.Embed(
                title="🛑 Spam-Filter deaktiviert",
                description="Der Spam-Filter wurde deaktiviert.",
                color=discord.Color.red()
            )
            
            await ctx.send(embed=embed)
    
    @automod.command(name="caps")
    @is_admin()
    async def automod_caps(self, ctx, status: str, threshold: Optional[int] = None):
        """Konfiguriert den CAPS-Filter"""
        if status.lower() not in ["an", "aus", "on", "off"]:
            await ctx.send("❌ Status muss 'an' oder 'aus' sein!")
            return
        
        guild_id = ctx.guild.id
        
        if status.lower() in ["an", "on"]:
            # Setze Standardwert, falls nicht angegeben
            if threshold is None:
                threshold = 70
                
            # Validiere Schwellenwert
            if threshold < 1 or threshold > 100:
                await ctx.send("❌ Der Schwellenwert muss zwischen 1 und 100 liegen!")
                return
                
            # Setze CAPS-Schwellenwert
            await self.automod.set_caps_threshold(guild_id, threshold / 100.0)
            
            embed = discord.Embed(
                title="✅ CAPS-Filter aktiviert",
                description=f"Der CAPS-Filter wurde mit einem Schwellenwert von {threshold}% aktiviert.",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
        else:
            # Deaktiviere CAPS-Filter durch sehr hohen Schwellenwert
            await self.automod.set_caps_threshold(guild_id, 1.0)
            
            embed = discord.Embed(
                title="🛑 CAPS-Filter deaktiviert",
                description="Der CAPS-Filter wurde deaktiviert.",
                color=discord.Color.red()
            )
            
            await ctx.send(embed=embed)
    
    @automod.command(name="emoji")
    @is_admin()
    async def automod_emoji(self, ctx, status: str, threshold: Optional[int] = None):
        """Konfiguriert den Emoji-Filter"""
        if status.lower() not in ["an", "aus", "on", "off"]:
            await ctx.send("❌ Status muss 'an' oder 'aus' sein!")
            return
        
        guild_id = ctx.guild.id
        
        if status.lower() in ["an", "on"]:
            # Setze Standardwert, falls nicht angegeben
            if threshold is None:
                threshold = 30
                
            # Validiere Schwellenwert
            if threshold < 1 or threshold > 100:
                await ctx.send("❌ Der Schwellenwert muss zwischen 1 und 100 liegen!")
                return
                
            # Setze Emoji-Schwellenwert
            await self.automod.set_emoji_threshold(guild_id, threshold / 100.0)
            
            embed = discord.Embed(
                title="✅ Emoji-Filter aktiviert",
                description=f"Der Emoji-Filter wurde mit einem Schwellenwert von {threshold}% aktiviert.",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
        else:
            # Deaktiviere Emoji-Filter durch sehr hohen Schwellenwert
            await self.automod.set_emoji_threshold(guild_id, 1.0)
            
            embed = discord.Embed(
                title="🛑 Emoji-Filter deaktiviert",
                description="Der Emoji-Filter wurde deaktiviert.",
                color=discord.Color.red()
            )
            
            await ctx.send(embed=embed)
    
    @automod.command(name="flood")
    @is_admin()
    async def automod_flood(self, ctx, status: str, messages: Optional[int] = None, interval: Optional[int] = None):
        """Konfiguriert den Flood-Filter"""
        if status.lower() not in ["an", "aus", "on", "off"]:
            await ctx.send("❌ Status muss 'an' oder 'aus' sein!")
            return
        
        guild_id = ctx.guild.id
        
        if status.lower() in ["an", "on"]:
            # Setze Standardwerte, falls nicht angegeben
            if messages is None:
                messages = 5
            if interval is None:
                interval = 5
                
            # Setze Flood-Einstellungen
            await self.automod.set_flood_settings(guild_id, messages, interval)
            
            embed = discord.Embed(
                title="✅ Flood-Filter aktiviert",
                description=f"Der Flood-Filter wurde mit {messages} gleichen Nachrichten in {interval} Sekunden konfiguriert.",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
        else:
            # Deaktiviere Flood-Filter durch sehr hohe Werte
            await self.automod.set_flood_settings(guild_id, 9999, 1)
            
            embed = discord.Embed(
                title="🛑 Flood-Filter deaktiviert",
                description="Der Flood-Filter wurde deaktiviert.",
                color=discord.Color.red()
            )
            
            await ctx.send(embed=embed)
    
    @automod.command(name="addword")
    @is_admin()
    async def automod_addword(self, ctx, *, word: str):
        """Fügt ein Wort zum Filter hinzu"""
        # Entferne Anführungszeichen, falls vorhanden
        word = word.strip('"\'')
        
        if not word:
            await ctx.send("❌ Bitte gib ein Wort an!")
            return
            
        await self.automod.add_banned_word(ctx.guild.id, word)
        
        embed = discord.Embed(
            title="✅ Wort hinzugefügt",
            description=f"Das Wort `{word}` wurde zum Filter hinzugefügt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @automod.command(name="delword")
    @is_admin()
    async def automod_delword(self, ctx, *, word: str):
        """Entfernt ein Wort vom Filter"""
        # Entferne Anführungszeichen, falls vorhanden
        word = word.strip('"\'')
        
        if not word:
            await ctx.send("❌ Bitte gib ein Wort an!")
            return
            
        await self.automod.remove_banned_word(ctx.guild.id, word)
        
        embed = discord.Embed(
            title="✅ Wort entfernt",
            description=f"Das Wort `{word}` wurde vom Filter entfernt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @automod.command(name="words")
    @is_admin()
    async def automod_words(self, ctx):
        """Zeigt alle gefilterten Wörter"""
        guild_id = ctx.guild.id
        words = list(self.automod.banned_words[guild_id])
        
        if not words:
            await ctx.send("❌ Es sind keine Wörter im Filter!")
            return
            
        # Sortiere Wörter alphabetisch
        words.sort()
        
        # Erstelle Embed mit Seitennavigation, falls nötig
        embeds = []
        words_per_page = 15
        
        for i in range(0, len(words), words_per_page):
            page_words = words[i:i+words_per_page]
            
            embed = discord.Embed(
                title="📋 Gefilterte Wörter",
                description=f"Seite {len(embeds)+1}/{(len(words)-1)//words_per_page+1}",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name=f"Wörter ({len(words)} insgesamt)",
                value="```\n" + "\n".join(page_words) + "```",
                inline=False
            )
            
            embeds.append(embed)
        
        # Sende erste Seite
        if embeds:
            await ctx.send(embed=embeds[0])
        
        # TODO: Implementiere Seitennavigation mit Reaktionen, falls gewünscht
    
    @automod.command(name="addlink")
    @is_admin()
    async def automod_addlink(self, ctx, *, link: str):
        """Fügt einen Link zum Filter hinzu"""
        # Entferne Anführungszeichen und Leerzeichen, falls vorhanden
        link = link.strip('"\'').strip()
        
        if not link:
            await ctx.send("❌ Bitte gib einen Link an!")
            return
            
        # Entferne http/https Präfix für bessere Filterung
        link = re.sub(r'^https?://', '', link)
        
        await self.automod.add_banned_link(ctx.guild.id, link)
        
        embed = discord.Embed(
            title="✅ Link hinzugefügt",
            description=f"Der Link `{link}` wurde zum Filter hinzugefügt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @automod.command(name="dellink")
    @is_admin()
    async def automod_dellink(self, ctx, *, link: str):
        """Entfernt einen Link vom Filter"""
        # Entferne Anführungszeichen und Leerzeichen, falls vorhanden
        link = link.strip('"\'').strip()
        
        if not link:
            await ctx.send("❌ Bitte gib einen Link an!")
            return
            
        # Entferne http/https Präfix für bessere Filterung
        link = re.sub(r'^https?://', '', link)
        
        await self.automod.remove_banned_link(ctx.guild.id, link)
        
        embed = discord.Embed(
            title="✅ Link entfernt",
            description=f"Der Link `{link}` wurde vom Filter entfernt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @automod.command(name="links")
    @is_admin()
    async def automod_links(self, ctx):
        """Zeigt alle gefilterten Links"""
        guild_id = ctx.guild.id
        links = list(self.automod.banned_links[guild_id])
        
        if not links:
            await ctx.send("❌ Es sind keine Links im Filter!")
            return
            
        # Sortiere Links alphabetisch
        links.sort()
        
        # Erstelle Embed mit Seitennavigation, falls nötig
        embeds = []
        links_per_page = 10
        
        for i in range(0, len(links), links_per_page):
            page_links = links[i:i+links_per_page]
            
            embed = discord.Embed(
                title="📋 Gefilterte Links",
                description=f"Seite {len(embeds)+1}/{(len(links)-1)//links_per_page+1}",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name=f"Links ({len(links)} insgesamt)",
                value="```\n" + "\n".join(page_links) + "```",
                inline=False
            )
            
            embeds.append(embed)
        
        # Sende erste Seite
        if embeds:
            await ctx.send(embed=embeds[0])
    
    @automod.group(name="whitelist", invoke_without_command=True)
    @is_admin()
    async def automod_whitelist(self, ctx):
        """Verwaltet die Whitelist für AutoMod"""
        await ctx.send("❌ Bitte gib einen Unterbefehl an: `role`, `channel` oder `list`")
    
    @automod_whitelist.command(name="role")
    @is_admin()
    async def automod_whitelist_role(self, ctx, role: discord.Role):
        """Fügt eine Rolle zur Whitelist hinzu"""
        await self.automod.add_whitelist_role(ctx.guild.id, role.id)
        
        embed = discord.Embed(
            title="✅ Rolle zur Whitelist hinzugefügt",
            description=f"Die Rolle {role.mention} wurde zur Whitelist hinzugefügt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @automod_whitelist.command(name="channel")
    @is_admin()
    async def automod_whitelist_channel(self, ctx, channel: discord.TextChannel):
        """Fügt einen Kanal zur Whitelist hinzu"""
        await self.automod.add_whitelist_channel(ctx.guild.id, channel.id)
        
        embed = discord.Embed(
            title="✅ Kanal zur Whitelist hinzugefügt",
            description=f"Der Kanal {channel.mention} wurde zur Whitelist hinzugefügt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @automod_whitelist.command(name="list")
    @is_admin()
    async def automod_whitelist_list(self, ctx):
        """Zeigt alle Whitelist-Einträge"""
        guild_id = ctx.guild.id
        
        # Hole Whitelist-Einträge
        whitelisted_roles = [ctx.guild.get_role(role_id) for role_id in self.automod.whitelisted_roles[guild_id]]
        whitelisted_roles = [role for role in whitelisted_roles if role]
        
        whitelisted_channels = [ctx.guild.get_channel(channel_id) for channel_id in self.automod.whitelisted_channels[guild_id]]
        whitelisted_channels = [channel for channel in whitelisted_channels if channel]
        
        if not whitelisted_roles and not whitelisted_channels:
            await ctx.send("❌ Es sind keine Einträge in der Whitelist!")
            return
            
        embed = discord.Embed(
            title="📋 AutoMod-Whitelist",
            color=discord.Color.blue()
        )
        
        if whitelisted_roles:
            embed.add_field(
                name=f"Rollen ({len(whitelisted_roles)})",
                value="\n".join([role.mention for role in whitelisted_roles]),
                inline=False
            )
        
        if whitelisted_channels:
            embed.add_field(
                name=f"Kanäle ({len(whitelisted_channels)})",
                value="\n".join([channel.mention for channel in whitelisted_channels]),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @automod_whitelist.command(name="removerole")
    @is_admin()
    async def automod_whitelist_removerole(self, ctx, role: discord.Role):
        """Entfernt eine Rolle von der Whitelist"""
        await self.automod.remove_whitelist_role(ctx.guild.id, role.id)
        
        embed = discord.Embed(
            title="✅ Rolle von Whitelist entfernt",
            description=f"Die Rolle {role.mention} wurde von der Whitelist entfernt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @automod_whitelist.command(name="removechannel")
    @is_admin()
    async def automod_whitelist_removechannel(self, ctx, channel: discord.TextChannel):
        """Entfernt einen Kanal von der Whitelist"""
        await self.automod.remove_whitelist_channel(ctx.guild.id, channel.id)
        
        embed = discord.Embed(
            title="✅ Kanal von Whitelist entfernt",
            description=f"Der Kanal {channel.mention} wurde von der Whitelist entfernt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    # Füge die Tabellen zur Datenbank hinzu
    from utils.db import Database
    db = Database()
    
    # AutoMod-Konfigurationstabelle
    await db.execute('''
        CREATE TABLE IF NOT EXISTS automod_config (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            log_channel_id INTEGER
        )
    ''')
    
    # AutoMod-Whitelist-Tabelle
    await db.execute('''
        CREATE TABLE IF NOT EXISTS automod_whitelist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            role_id INTEGER,
            channel_id INTEGER,
            type TEXT NOT NULL,
            UNIQUE(guild_id, role_id, type),
            UNIQUE(guild_id, channel_id, type)
        )
    ''')
    
    # AutoMod-Filter-Tabelle
    await db.execute('''
        CREATE TABLE IF NOT EXISTS automod_filter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            type TEXT NOT NULL,
            UNIQUE(guild_id, word, type)
        )
    ''')
    
    # AutoMod-Einstellungen-Tabelle
    await db.execute('''
        CREATE TABLE IF NOT EXISTS automod_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            setting_type TEXT NOT NULL,
            value TEXT NOT NULL,
            UNIQUE(guild_id, setting_type)
        )
    ''')
    
    # Registriere die Cog
    await bot.add_cog(AutoModCommands(bot)) 