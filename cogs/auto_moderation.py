import discord
from discord.ext import commands
import aiosqlite
from utils.db import DB_PATH
import re
import json
import datetime
import asyncio
from collections import defaultdict

class AutoModerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_tracker = defaultdict(lambda: defaultdict(list))
        self.flood_tracker = defaultdict(lambda: defaultdict(list))
        self.configs = {}
        self.word_filters = defaultdict(set)
        
    async def cog_load(self):
        """Lädt die Konfigurationen aus der Datenbank"""
        async with aiosqlite.connect(DB_PATH) as db:
            # Lade Auto-Mod Konfigurationen für alle Server
            async with db.execute('''
                SELECT * FROM automod_config
            ''') as cursor:
                async for row in cursor:
                    self.configs[row[0]] = {
                        'enabled': row[13],  # enabled status
                        'spam_detection': row[1],
                        'spam_threshold': row[2],
                        'spam_interval': row[3],
                        'link_filter': row[4],
                        'allowed_links': json.loads(row[5]) if row[5] else [],
                        'caps_filter': row[6],
                        'caps_threshold': row[7],
                        'emoji_filter': row[8],
                        'emoji_threshold': row[9],
                        'flood_filter': row[10],
                        'flood_threshold': row[11],
                        'flood_interval': row[12],
                        'log_channel_id': row[14],
                        'whitelist_roles': json.loads(row[15]) if row[15] else [],
                        'whitelist_channels': json.loads(row[16]) if row[16] else []
                    }
                    print(f"Loaded config for guild {row[0]}: {self.configs[row[0]]}")  # Debug-Ausgabe

            # Lade Wort-Filter
            async with db.execute('SELECT guild_id, word FROM word_filter') as cursor:
                async for row in cursor:
                    self.word_filters[row[0]].add(row[1].lower())

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx):
        """Auto-Moderations Befehle"""
        embed = discord.Embed(
            title="🛡️ Auto-Moderation Befehle",
            description="Verwalte die automatische Moderation",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Grundeinstellungen",
            value="`!automod enable` - Aktiviert Auto-Moderation\n"
                  "`!automod disable` - Deaktiviert Auto-Moderation\n"
                  "`!automod status` - Zeigt aktuelle Einstellungen\n"
                  "`!automod log #kanal` - Setzt den Log-Kanal",
            inline=False
        )
        embed.add_field(
            name="Filter",
            value="`!automod spam <an/aus> [schwelle] [interval]` - Spam-Schutz\n"
                  "`!automod links <an/aus>` - Link-Filter\n"
                  "`!automod caps <an/aus> [schwelle]` - CAPS-Filter\n"
                  "`!automod emoji <an/aus> [schwelle]` - Emoji-Spam-Filter\n"
                  "`!automod flood <an/aus> [nachrichten] [sekunden]` - Flood-Schutz",
            inline=False
        )
        embed.add_field(
            name="Wort-Filter",
            value="`!automod addword <wort>` - Fügt Wort zur Blacklist hinzu\n"
                  "`!automod delword <wort>` - Entfernt Wort von der Blacklist\n"
                  "`!automod words` - Zeigt alle gefilterten Wörter",
            inline=False
        )
        embed.add_field(
            name="Whitelist",
            value="`!automod whitelist role <@rolle>` - Rolle von Filtern ausnehmen\n"
                  "`!automod whitelist channel <#kanal>` - Kanal von Filtern ausnehmen",
            inline=False
        )
        await ctx.send(embed=embed)

    @automod.command(name="status")
    @commands.has_permissions(administrator=True)
    async def show_status(self, ctx):
        """Zeigt die aktuellen Auto-Mod Einstellungen"""
        config = self.configs.get(ctx.guild.id, {})
        
        embed = discord.Embed(
            title="🛡️ Auto-Mod Status",
            description=f"**System Status:** {'✅ Aktiviert' if config.get('enabled', False) else '❌ Deaktiviert'}",
            color=discord.Color.blue()
        )

        # Spam-Schutz Status
        spam_status = (
            f"**Status:** {'✅ An' if config.get('spam_detection', False) else '❌ Aus'}\n"
            f"**Schwelle:** {config.get('spam_threshold', 5)} Nachrichten\n"
            f"**Intervall:** {config.get('spam_interval', 5)} Sekunden"
        )
        embed.add_field(name="🚫 Spam-Schutz", value=spam_status, inline=False)

        # Link-Filter Status
        link_status = (
            f"**Status:** {'✅ An' if config.get('link_filter', False) else '❌ Aus'}\n"
            f"**Erlaubte Links:** {', '.join(config.get('allowed_links', [])) or 'Keine'}"
        )
        embed.add_field(name="🔗 Link-Filter", value=link_status, inline=False)

        # CAPS-Filter Status
        caps_status = (
            f"**Status:** {'✅ An' if config.get('caps_filter', False) else '❌ Aus'}\n"
            f"**Schwelle:** {config.get('caps_threshold', 70)}%"
        )
        embed.add_field(name="🔠 CAPS-Filter", value=caps_status, inline=False)

        # Emoji-Filter Status
        emoji_status = (
            f"**Status:** {'✅ An' if config.get('emoji_filter', False) else '❌ Aus'}\n"
            f"**Maximum:** {config.get('emoji_threshold', 5)} Emojis"
        )
        embed.add_field(name="😀 Emoji-Filter", value=emoji_status, inline=False)

        # Flood-Schutz Status
        flood_status = (
            f"**Status:** {'✅ An' if config.get('flood_filter', False) else '❌ Aus'}\n"
            f"**Schwelle:** {config.get('flood_threshold', 5)} Nachrichten\n"
            f"**Intervall:** {config.get('flood_interval', 3)} Sekunden"
        )
        embed.add_field(name="📊 Flood-Schutz", value=flood_status, inline=False)

        # Log-Kanal
        log_channel_id = config.get('log_channel_id')
        log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None
        log_status = f"**Kanal:** {log_channel.mention if log_channel else '❌ Nicht gesetzt'}"
        embed.add_field(name="📝 Logging", value=log_status, inline=False)

        # Whitelist Info
        whitelist_roles = config.get('whitelist_roles', [])
        whitelist_channels = config.get('whitelist_channels', [])
        
        whitelist_info = []
        if whitelist_roles:
            roles = [ctx.guild.get_role(role_id).mention for role_id in whitelist_roles if ctx.guild.get_role(role_id)]
            whitelist_info.append(f"**Rollen:** {', '.join(roles)}")
        if whitelist_channels:
            channels = [ctx.guild.get_channel(channel_id).mention for channel_id in whitelist_channels if ctx.guild.get_channel(channel_id)]
            whitelist_info.append(f"**Kanäle:** {', '.join(channels)}")
        
        if whitelist_info:
            embed.add_field(name="⭐ Whitelist", value="\n".join(whitelist_info), inline=False)
        else:
            embed.add_field(name="⭐ Whitelist", value="Keine Einträge", inline=False)

        await ctx.send(embed=embed)

    @automod.command(name="enable")
    @commands.has_permissions(administrator=True)
    async def enable_automod(self, ctx):
        """Aktiviert die Auto-Moderation"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO automod_config 
                (guild_id, enabled) 
                VALUES (?, 1)
            ''', (ctx.guild.id,))
            await db.commit()

        self.configs.setdefault(ctx.guild.id, {})['enabled'] = True
        
        embed = discord.Embed(
            title="✅ Auto-Moderation aktiviert",
            description="Nutze `!automod status` um die aktuellen Einstellungen zu sehen.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @automod.command(name="disable")
    @commands.has_permissions(administrator=True)
    async def disable_automod(self, ctx):
        """Deaktiviert die Auto-Moderation"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO automod_config 
                (guild_id, enabled) 
                VALUES (?, 0)
            ''', (ctx.guild.id,))
            await db.commit()

        self.configs.setdefault(ctx.guild.id, {})['enabled'] = False
        
        embed = discord.Embed(
            title="❌ Auto-Moderation deaktiviert",
            description="Alle Filter wurden deaktiviert.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @automod.command(name="spam")
    @commands.has_permissions(administrator=True)
    async def set_spam_filter(self, ctx, state: str, threshold: int = 5, interval: int = 5):
        """Konfiguriert den Spam-Filter"""
        if state.lower() not in ['an', 'aus']:
            await ctx.send("❌ Bitte gib 'an' oder 'aus' an!")
            return

        if threshold < 3:
            await ctx.send("❌ Die Schwelle muss mindestens 3 Nachrichten betragen!")
            return

        if interval < 3:
            await ctx.send("❌ Das Intervall muss mindestens 3 Sekunden betragen!")
            return

        enabled = state.lower() == 'an'
        
        # Aktualisiere Datenbank
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO automod_config 
                (guild_id, spam_detection, spam_threshold, spam_interval, enabled)
                VALUES (?, ?, ?, ?, COALESCE((SELECT enabled FROM automod_config WHERE guild_id = ?), 0))
            ''', (ctx.guild.id, enabled, threshold, interval, ctx.guild.id))
            await db.commit()

        # Aktualisiere lokale Konfiguration
        if ctx.guild.id not in self.configs:
            self.configs[ctx.guild.id] = {}
        
        self.configs[ctx.guild.id].update({
            'spam_detection': enabled,
            'spam_threshold': threshold,
            'spam_interval': interval
        })

        # Debug-Ausgabe
        print(f"Updated spam config for guild {ctx.guild.id}: {self.configs[ctx.guild.id]}")

        embed = discord.Embed(
            title="🛡️ Spam-Filter Konfiguration",
            description=(
                f"**Status:** {'✅ Aktiviert' if enabled else '❌ Deaktiviert'}\n"
                f"**Schwelle:** {threshold} Nachrichten\n"
                f"**Intervall:** {interval} Sekunden\n\n"
                "**Hinweis:** Der Bot wird bei Spam:\n"
                "• Die Spam-Nachrichten löschen\n"
                "• Einen 5-Minuten Timeout vergeben\n"
                "• Den User per DM benachrichtigen"
            ),
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        await ctx.send(embed=embed)

        # Zeige aktuelle Konfiguration
        await self.show_status(ctx)

    async def check_spam(self, message, config):
        """Überprüft Nachrichten auf Spam"""
        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Prüfe Bot-Berechtigungen
        if not message.guild.me.guild_permissions.moderate_members:
            if config.get('log_channel_id'):
                log_channel = message.guild.get_channel(config['log_channel_id'])
                if log_channel:
                    await log_channel.send("⚠️ **Fehler:** Bot hat keine 'Mitglieder moderieren' Berechtigung!")
            return False
        
        # Initialisiere Tracking
        if guild_id not in self.spam_tracker:
            self.spam_tracker[guild_id] = {}
        if user_id not in self.spam_tracker[guild_id]:
            self.spam_tracker[guild_id][user_id] = []
        
        user_messages = self.spam_tracker[guild_id][user_id]
        interval = config.get('spam_interval', 5)
        cutoff = now - datetime.timedelta(seconds=interval)
        
        # Entferne alte Nachrichten
        user_messages = [msg for msg in user_messages if msg['time'] > cutoff]
        
        # Füge aktuelle Nachricht hinzu
        user_messages.append({
            'content': message.content.lower(),
            'time': now,
            'length': len(message.content)
        })
        
        self.spam_tracker[guild_id][user_id] = user_messages
        threshold = config.get('spam_threshold', 5)
        
        # Spam-Erkennung Logik
        is_spam = False
        total_messages = len(user_messages)
        
        # 1. Prüfe Nachrichtenfrequenz
        if total_messages >= threshold:
            is_spam = True
        
        # 2. Prüfe Ein-Buchstaben-Spam
        single_char_messages = sum(1 for msg in user_messages if len(msg['content']) <= 2)
        if single_char_messages >= threshold - 1:
            is_spam = True
        
        # 3. Prüfe schnelle Sätze
        if total_messages >= 3:  # Mindestens 3 Nachrichten für diese Prüfung
            # Berechne durchschnittliche Zeit zwischen Nachrichten
            time_diffs = []
            for i in range(1, len(user_messages)):
                diff = (user_messages[i]['time'] - user_messages[i-1]['time']).total_seconds()
                time_diffs.append(diff)
            
            avg_time_between = sum(time_diffs) / len(time_diffs)
            
            # Wenn durchschnittliche Zeit unter 1.5 Sekunden
            if avg_time_between < 1.5 and total_messages >= threshold - 1:
                is_spam = True
        
        # 4. Prüfe auf wiederholte Nachrichten
        unique_messages = set(msg['content'] for msg in user_messages)
        if len(unique_messages) <= 2 and total_messages >= threshold - 1:
            is_spam = True
        
        # 5. Prüfe auf ähnliche Nachrichten
        if len(user_messages) >= 3:
            similar_count = 1
            for i in range(len(user_messages)-1):
                current = user_messages[i]['content']
                for j in range(i+1, len(user_messages)):
                    other = user_messages[j]['content']
                    # Prüfe auf Teilstrings
                    if current in other or other in current:
                        similar_count += 1
                        break
            
            if similar_count >= threshold - 1:
                is_spam = True
        
        if is_spam:
            try:
                # Lösche die letzten Nachrichten
                deleted = 0
                async for msg in message.channel.history(limit=threshold * 2):
                    if msg.author.id == user_id and (msg.created_at.replace(tzinfo=datetime.timezone.utc) > cutoff):
                        try:
                            await msg.delete()
                            deleted += 1
                        except (discord.NotFound, discord.Forbidden):
                            pass
                
                # Timeout für den Spammer
                try:
                    # Prüfe ob User bereits im Timeout ist
                    if message.author.timed_out_until:
                        current_timeout = message.author.timed_out_until.replace(tzinfo=datetime.timezone.utc)
                        if current_timeout > now:
                            # User ist bereits im Timeout, verlängere es
                            new_duration = datetime.timedelta(minutes=10)  # Doppelte Zeit
                            await message.author.timeout(now + new_duration, reason="Wiederholter Spam")
                            timeout_msg = "Timeout wurde auf 10 Minuten verlängert"
                        else:
                            # Normaler Timeout
                            duration = datetime.timedelta(minutes=5)
                            await message.author.timeout(now + duration, reason="Spam Detection")
                            timeout_msg = "5 Minuten Timeout"
                    else:
                        # Normaler Timeout
                        duration = datetime.timedelta(minutes=5)
                        await message.author.timeout(now + duration, reason="Spam Detection")
                        timeout_msg = "5 Minuten Timeout"
                    
                    # Benachrichtige den User
                    warning = (
                        "⚠️ **Anti-Spam Warnung**\n\n"
                        f"Du wurdest für Spam bestraft:\n"
                        f"• {timeout_msg}\n"
                        f"• {deleted} Nachrichten gelöscht\n"
                        f"• {similar_count} ähnliche Nachrichten in {interval} Sekunden\n\n"
                        "**Hinweise:**\n"
                        "• Warte zwischen deinen Nachrichten\n"
                        "• Vermeide Ein-Buchstaben-Nachrichten\n"
                        "• Nutze keine sich wiederholenden Nachrichten\n\n"
                        "**Bei weiteren Verstößen wird die Strafe erhöht!**"
                    )
                    try:
                        await message.author.send(warning)
                    except discord.Forbidden:
                        # Wenn DMs deaktiviert sind, sende die Warnung in den Kanal
                        warning_msg = await message.channel.send(
                            f"{message.author.mention} {warning}",
                            delete_after=30
                        )
                    
                except discord.Forbidden:
                    if config.get('log_channel_id'):
                        log_channel = message.guild.get_channel(config['log_channel_id'])
                        if log_channel:
                            await log_channel.send(
                                f"⚠️ **Fehler:** Konnte {message.author.mention} nicht timeouten. "
                                "Überprüfe die Bot-Berechtigungen!"
                            )
                
                # Log-Nachricht
                if config.get('log_channel_id'):
                    log_channel = message.guild.get_channel(config['log_channel_id'])
                    if log_channel:
                        embed = discord.Embed(
                            title="🛡️ Auto-Mod: Spam Detection",
                            description=(
                                f"**User:** {message.author.mention} ({message.author.id})\n"
                                f"**Aktion:** {timeout_msg}\n"
                                f"**Gelöschte Nachrichten:** {deleted}\n"
                                f"**Ähnliche Nachrichten:** {similar_count}\n"
                                f"**Zeitraum:** {interval} Sekunden"
                            ),
                            color=discord.Color.red(),
                            timestamp=now
                        )
                        embed.add_field(
                            name="Kanal",
                            value=message.channel.mention
                        )
                        if len(message.content) <= 100:
                            embed.add_field(
                                name="Letzte Nachricht",
                                value=f"```{message.content}```",
                                inline=False
                            )
                        await log_channel.send(embed=embed)
                
                # Tracker zurücksetzen
                self.spam_tracker[guild_id][user_id] = []
                return True
                
            except Exception as e:
                print(f"Fehler bei der Spam-Behandlung: {str(e)}")
                if config.get('log_channel_id'):
                    log_channel = message.guild.get_channel(config['log_channel_id'])
                    if log_channel:
                        await log_channel.send(f"⚠️ **Fehler bei der Spam-Behandlung:** {str(e)}")
                return False
        
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        """Überprüft Nachrichten auf Verstöße"""
        if message.author.bot or not message.guild:
            return

        config = self.configs.get(message.guild.id, {})
        if not config.get('enabled', False):
            return

        # Whitelist-Prüfungen
        whitelist_roles = config.get('whitelist_roles', [])
        whitelist_channels = config.get('whitelist_channels', [])
        
        if message.channel.id in whitelist_channels:
            return
        
        if any(role.id in whitelist_roles for role in message.author.roles):
            return

        violations = []

        # Spam-Erkennung
        if config.get('spam_detection', False):
            if await self.check_spam(message, config):
                return  # Wenn Spam erkannt wurde, weitere Checks überspringen

        # CAPS-Filter
        if config.get('caps_filter', False) and len(message.content) > 8:
            caps_count = sum(1 for c in message.content if c.isupper())
            if caps_count / len(message.content) * 100 > config['caps_threshold']:
                violations.append('CAPS')

        # Emoji-Filter
        if config.get('emoji_filter', False):
            emoji_count = len(re.findall(r'<a?:\w+:\d+>|[\U0001F300-\U0001F9FF]', message.content))
            if emoji_count > config['emoji_threshold']:
                violations.append('Emoji-Spam')

        # Link-Filter
        if config.get('link_filter', False):
            allowed_links = config.get('allowed_links', [])
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
            
            for url in urls:
                if not any(allowed in url for allowed in allowed_links):
                    violations.append('Nicht erlaubter Link')
                    break

        # Wort-Filter
        filtered_words = self.word_filters.get(message.guild.id, set())
        if filtered_words:
            content_lower = message.content.lower()
            if any(word in content_lower for word in filtered_words):
                violations.append('Verbotenes Wort')

        # Flood-Schutz
        if config.get('flood_filter', False):
            user_floods = self.flood_tracker[message.guild.id][message.author.id]
            now = datetime.datetime.now()
            
            # Alte Nachrichten entfernen
            threshold_time = now - datetime.timedelta(seconds=config['flood_interval'])
            user_floods = [time for time in user_floods if time > threshold_time]
            
            # Neue Nachricht hinzufügen
            user_floods.append(now)
            
            self.flood_tracker[message.guild.id][message.author.id] = user_floods
            
            if len(user_floods) >= config['flood_threshold']:
                violations.append('Flood')
                self.flood_tracker[message.guild.id][message.author.id] = []

        # Wenn Verstöße gefunden wurden
        if violations:
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            # Log-Nachricht senden
            if config.get('log_channel_id'):
                log_channel = message.guild.get_channel(config['log_channel_id'])
                if log_channel:
                    embed = discord.Embed(
                        title="🛡️ Auto-Mod Verstoß",
                        description=f"Nachricht von {message.author.mention} wurde entfernt.",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Verstöße", value="\n".join(violations))
                    embed.add_field(name="Kanal", value=message.channel.mention)
                    embed.add_field(name="Nachricht", value=message.content[:1024], inline=False)
                    await log_channel.send(embed=embed)

            # User benachrichtigen
            try:
                await message.author.send(
                    f"⚠️ Deine Nachricht wurde wegen folgenden Verstößen entfernt: {', '.join(violations)}"
                )
            except discord.Forbidden:
                pass

async def setup(bot):
    await bot.add_cog(AutoModerator(bot)) 